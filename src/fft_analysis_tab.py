import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QWidget, QPushButton, QVBoxLayout, \
    QFileDialog, QComboBox, QHBoxLayout, QLabel, \
    QSlider, QListWidget, QListWidgetItem
from scipy.signal import find_peaks, welch


def process_frequency_data(datasets, selected_axis, padding_factor, plot_mode):
    results = []
    # Define gravity offsets for each axis (adjust these values based on calibration)
    gravity_offsets = {'X': -9.8124, 'Y': 0.0, 'Z': 0.0}

    for data in datasets:
        if data.empty:
            continue

        # Convert acceleration data to physical units and correct for gravity
        accel_data = 9.8124 * data[selected_axis].to_numpy()
        accel_data -= gravity_offsets.get(selected_axis, 0.0)

        # Optional: Commented out mean subtraction if not needed
        # accel_data -= np.mean(accel_data)

        time_data = data['Time [microseconds]'].to_numpy()
        if np.max(time_data) < 1000:
            time = time_data
            print("Time data detected in seconds.")
        else:
            time = time_data * 1e-6  # Convert microseconds to seconds

        N_fixed = 5096  # Fixed FFT length

        if len(accel_data) < N_fixed:
            print("Not enough data points.")
            continue

        dt = np.mean(np.diff(time))
        if dt <= 0:
            continue  # Prevent invalid time steps

        # Use only the first N_fixed samples
        accel_data = accel_data[:N_fixed]

        # Apply a Hann window for balanced spectral response
        window = np.hanning(N_fixed)
        accel_data_windowed = accel_data * window

        # Zero-pad to next power of 2 using the given padding_factor
        padded_length = int(2 ** np.ceil(np.log2(N_fixed * padding_factor)))
        accel_data_padded = np.pad(
            accel_data_windowed, (0, padded_length - N_fixed), mode="constant"
        )

        if plot_mode == "FFT":
            fft_accel = np.fft.fft(accel_data_padded)
            freq = np.fft.fftfreq(len(accel_data_padded), d=dt)
            # Keep only positive frequencies
            positive_freqs = freq[:len(freq) // 2]
            positive_magnitudes = np.abs(fft_accel)[:len(freq) // 2]

        elif plot_mode == "PSD":
            padded_len = len(accel_data_padded)
            dynamic_factor = 2
            nperseg = max(256, int(padded_len / dynamic_factor))
            noverlap = int(nperseg * 0.5)
            freq, psd = welch(
                accel_data_padded,
                fs=1 / dt,
                window="hann",
                nperseg=nperseg,
                noverlap=noverlap,
                scaling="density"
            )
            # Convert PSD (power/Hz) to amplitude spectral density (ASD)
            positive_freqs = freq
            positive_magnitudes = np.sqrt(psd)
        else:
            print(f"Unknown plot mode: {plot_mode}")
            continue

        # Optionally, remove frequencies below a given minimum (e.g., below 2 Hz)
        min_frequency = 4  # Hz
        valid_indices = positive_freqs >= min_frequency
        positive_freqs = positive_freqs[valid_indices]
        positive_magnitudes = positive_magnitudes[valid_indices]

        # Normalize magnitudes to 0-1
        positive_magnitudes -= positive_magnitudes.min()
        if positive_magnitudes.max() > 0:
            positive_magnitudes /= positive_magnitudes.max()

        # Scale magnitudes to 0-1000
        positive_magnitudes *= 1000

        results.append({
            'positive_freqs': positive_freqs,
            'positive_magnitudes': positive_magnitudes,
            'dt': dt
        })

    return results

def detect_peaks(positive_freqs, positive_magnitudes, tolerance):
    peaks, properties = find_peaks(positive_magnitudes, height=tolerance)
    natural_frequencies = positive_freqs[peaks]
    peak_magnitudes = positive_magnitudes[peaks]
    return natural_frequencies, peak_magnitudes

def plot_frequency_data(processed_data, plot_widget, freq_list_widget, tolerance, dataset_colors, selected_axis, selected_accel, plot_mode, freq_info_label):
    plot_widget.clear()
    freq_list_widget.clear()
    all_natural_frequencies = []

    if not hasattr(plot_widget, 'fft_legend'):
        plot_widget.fft_legend = plot_widget.addLegend()

    for i, freq_data in enumerate(processed_data):
        positive_freqs = freq_data['positive_freqs']
        positive_magnitudes = freq_data['positive_magnitudes']
        dt = freq_data['dt']

        natural_frequencies, peak_magnitudes = detect_peaks(positive_freqs, positive_magnitudes, tolerance)
        all_natural_frequencies.extend(natural_frequencies)

        pen = pg.mkPen(color=dataset_colors[i % len(dataset_colors)], width=1)
        plot_widget.plot(positive_freqs, positive_magnitudes, pen=pen,
                         name="{} - Accel {} (Dataset {})".format(selected_axis, selected_accel, i + 1))

        symbol_pen = pg.mkPen(color=dataset_colors[i % len(dataset_colors)])
        symbol_brush = pg.mkBrush(color=dataset_colors[i % len(dataset_colors)])
        fft_peak_item = pg.ScatterPlotItem(x=natural_frequencies, y=peak_magnitudes,
                                           pen=symbol_pen, brush=symbol_brush, size=10, symbol='o')
        plot_widget.addItem(fft_peak_item)
        fft_peak_item.setZValue(10)

    unique_natural_frequencies = np.unique(np.round(all_natural_frequencies, decimals=2))
    for freq in unique_natural_frequencies:
        freq_list_widget.addItem("{:.2f} Hz".format(freq))

    plot_widget.enableAutoRange(axis='xy', enable=True)
    if processed_data:
        dt = processed_data[0]['dt']
        sampling_freq = 1 / dt
        freq_info_label.setText("dt: {:.10f} s\n1/dt: {:.4f} Hz".format(dt, sampling_freq))
        mode_title = "FFT" if plot_mode == "FFT" else "PSD"
        plot_widget.setLabel('left', 'Magnitude')
        plot_widget.setLabel('bottom', 'Frequency (Hz)')
        plot_widget.setTitle("Accelerometer {}: {} {} (Frequency Domain)".format(selected_accel, selected_axis, mode_title))
    else:
        plot_widget.setTitle("No Data Loaded")

class PlotFFT(QWidget):
    SLIDER_CONVERSION = 100000  # Conversion factor for slider values (each step equals 100,000 µs)

    def __init__(self):
        super().__init__()

        # Data and configuration
        self.dataset_colors = ["r", "g", "b", "y", "m", "c", "k"]
        self.datasets_freq_data = []  # This will store processed frequency data
        self.datasets = []  # initialize datasets as an empty list
        self.padding_factor = 5
        self.plot_mode = "FFT"  # Default mode

        # Timers for debouncing
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_plot)
        self.slider_timer = QTimer()
        self.slider_timer.setSingleShot(True)
        self.slider_timer.setInterval(200)
        self.slider_timer.timeout.connect(self.update_plot)

        # Main layout (Left: plots and controls; Right: frequency info)
        main_layout = QHBoxLayout()

        # --------------------
        # Left Layout
        # --------------------
        left_layout = QVBoxLayout()

        # Toggle button for switching between FFT and PSD modes
        self.toggle_button = QPushButton("Show PSD")
        self.toggle_button.clicked.connect(self.toggle_plot)

        # Container widget for plots with a margin
        self.container_widget = QWidget()
        self.container_widget.setObjectName("graphy")
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)

        # Plot widgets for time domain and frequency domain
        self.plot_widget_time = pg.PlotWidget()
        self.plot_widget_time.setBackground("#2b2b2b")
        self.plot_widget_fft = pg.PlotWidget()
        self.plot_widget_fft.setBackground("#2b2b2b")

        container_layout.addWidget(self.plot_widget_time)
        container_layout.addWidget(self.plot_widget_fft)
        left_layout.addWidget(self.container_widget)

        # Sliders and their labels
        self.start_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.start_time_slider.setRange(0, 100)
        self.end_time_slider.setRange(0, 100)
        self.tolerance_slider.setRange(1, 10000)
        self.start_time_slider.setValue(0)
        self.end_time_slider.setValue(100)
        self.tolerance_slider.setValue(1000)

        self.start_time_label = QLabel("Start Time: 0 µs")
        self.end_time_label = QLabel("End Time: 0 µs")
        self.tolerance_label = QLabel("Tolerance: 1000 dB")

        # Connect slider signals in a loop
        for slider in (self.start_time_slider, self.end_time_slider, self.tolerance_slider):
            slider.valueChanged.connect(self.on_slider_value_changed)
            slider.sliderReleased.connect(self.on_slider_released)

        slider_grid = QGridLayout()
        slider_grid.addWidget(self.start_time_label, 0, 0)
        slider_grid.addWidget(self.start_time_slider, 0, 1)
        slider_grid.addWidget(self.end_time_label, 1, 0)
        slider_grid.addWidget(self.end_time_slider, 1, 1)
        slider_grid.addWidget(self.tolerance_label, 2, 0)
        slider_grid.addWidget(self.tolerance_slider, 2, 1)
        left_layout.addLayout(slider_grid)

        # Accelerometer and axis selection
        self.axis_selection = QComboBox()
        self.axis_selection.addItems(["X Acceleration", "Y Acceleration", "Z Acceleration"])
        self.axis_selection.currentIndexChanged.connect(self.update_plot)
        self.accel_id_selection = QComboBox()
        self.accel_id_selection.currentIndexChanged.connect(self.update_plot)

        accel_row = QHBoxLayout()
        accel_row.addWidget(QLabel("Accelerometer ID and Axis:"))
        accel_row.addWidget(self.accel_id_selection)
        accel_row.addWidget(self.axis_selection)
        left_layout.addLayout(accel_row)

        # Button grid for export, open CSV, and toggle
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_data)
        self.open_button = QPushButton("Open CSV")
        self.open_button.clicked.connect(self.open_csv)
        self.open_recent = QPushButton("Open Latest Sample")
        self.open_recent.clicked.connect(self.open_last_sample)

        button_grid = QGridLayout()
        button_grid.addWidget(self.export_button, 0, 0)
        button_grid.addWidget(self.open_button, 0, 1)
        button_grid.addWidget(self.open_recent, 1, 0)
        button_grid.addWidget(self.toggle_button, 1, 1)
        left_layout.addLayout(button_grid)

        # --------------------
        # Right Layout
        # --------------------
        right_layout = QVBoxLayout()
        self.freq_list_widget = QListWidget()
        self.freq_list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.freq_list_widget.addItem("Awaiting Data...")
        self.freq_list_widget.setMinimumWidth(125)
        right_layout.addWidget(self.freq_list_widget)
        self.freq_info_label = QLabel("Freq: -- Hz\n1/dt: -- Hz")
        self.freq_info_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.freq_info_label)

        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)
        self.setLayout(main_layout)

        # Data placeholders
        self.data = pd.DataFrame()
        self.data_filtered = pd.DataFrame()
        self.positive_freqs = np.array([])
        self.positive_magnitudes_dB = np.array([])
        self.fft_peaks = []
        self.natural_frequencies = np.array([])

        self.freq_list_widget.itemSelectionChanged.connect(self.update_selected_frequencies)

    def set_background(self, hex_color):
        self.plot_widget_time.setBackground(hex_color)
        self.plot_widget_fft.setBackground(hex_color)

    def update_selected_frequencies(self):
        selected_items = self.freq_list_widget.selectedItems()
        selected_freqs = [float(item.text().split()[0]) for item in selected_items]

        if hasattr(self, 'selected_peaks_item'):
            self.plot_widget_fft.removeItem(self.selected_peaks_item)
            del self.selected_peaks_item

        selected_natural_freqs, selected_magnitudes = [], []
        for freq_data in self.datasets_freq_data:
            positive_freqs = freq_data['positive_freqs']
            positive_magnitudes = freq_data['positive_magnitudes']
            if len(positive_freqs) == 0:
                continue
            for freq in selected_freqs:
                idx = np.abs(positive_freqs - freq).argmin()
                selected_natural_freqs.append(positive_freqs[idx])
                selected_magnitudes.append(positive_magnitudes[idx])

        if selected_natural_freqs and selected_magnitudes:
            symbol_pen = pg.mkPen('w')
            symbol_brush = pg.mkBrush('w')
            self.selected_peaks_item = pg.ScatterPlotItem(
                x=selected_natural_freqs,
                y=selected_magnitudes,
                pen=symbol_pen,
                brush=symbol_brush,
                size=12,
                symbol='o'
            )
            self.plot_widget_fft.addItem(self.selected_peaks_item)
            self.selected_peaks_item.setZValue(15)
        else:
            print("No frequencies selected or no data available to plot selected frequencies.")

    def update_padding_factor(self, padding_factor):
        self.padding_factor = padding_factor
        print(f"Padding Factor updated to: {self.padding_factor}")
        self.update_plot()

    def open_last_sample(self):
        import os, re
        directory = "../Cached_Samples/"
        pattern = r"samples_\d{8}_\d{6}\.csv"
        files = [f for f in os.listdir(directory) if re.match(pattern, f)]
        if not files:
            print("No matching files found.")
            return

        newest_file = max([os.path.join(directory, f) for f in files], key=os.path.getmtime)
        print(f"Opening newest file: {newest_file}")
        data = self.load_data(newest_file, dataset_index=0)
        if not data.empty:
            if 'Accelerometer ID' in data.columns:
                unique_ids = sorted(data['Accelerometer ID'].astype(str).unique())
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems(unique_ids)
                if unique_ids:
                    self.accel_id_selection.setCurrentIndex(0)
            data_filtered = self.filter_data(data)
            if not data_filtered.empty:
                self.datasets = [data_filtered]
                self.dataset_colors = [pg.intColor(0)]
                self.setup_sliders()
                self.plot_time_domain(self.datasets)
                self.plot_frequency_domain(self.datasets)
            else:
                print("No data available after filtering.")
        else:
            print("No data loaded from file.")

    def toggle_plot(self):
        self.plot_mode = "PSD" if self.plot_mode == "FFT" else "FFT"
        self.toggle_button.setText("Show FFT" if self.plot_mode == "PSD" else "Show PSD")
        self.update_plot()

    def update_labels(self):
        start_time = self.start_time_slider.value() * self.SLIDER_CONVERSION
        end_time = self.end_time_slider.value() * self.SLIDER_CONVERSION
        tolerance_value = self.tolerance_slider.value()
        self.start_time_label.setText(f"Start Time: {start_time} µs")
        self.end_time_label.setText(f"End Time: {end_time} µs")
        self.tolerance_label.setText(f"Tolerance: {tolerance_value} dB")

    def export_data(self):
        if not hasattr(self, 'datasets_filtered') or all(df.empty for df in self.datasets_filtered):
            print("No data to export.")
            return

        file_dialog = QFileDialog()
        file_base_path, _ = file_dialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_base_path:
            for i, trimmed_data in enumerate(self.datasets_filtered):
                if trimmed_data.empty:
                    continue
                start_time = self.start_time_slider.value()
                end_time = self.end_time_slider.value()
                trimmed_data_in_range = trimmed_data[
                    (trimmed_data['Time [microseconds]'] >= start_time * self.SLIDER_CONVERSION) &
                    (trimmed_data['Time [microseconds]'] <= end_time * self.SLIDER_CONVERSION)
                ]
                if trimmed_data_in_range.empty:
                    print(f"No data in range for Dataset {i + 1}.")
                    continue
                trimmed_data_path = f"{file_base_path}_Dataset_{i + 1}_trimmed_data.csv"
                trimmed_data_in_range.to_csv(trimmed_data_path, index=False)
                print(f"Dataset {i + 1} trimmed data exported to {trimmed_data_path}.")

            if self.datasets_freq_data:
                for i, freq_data in enumerate(self.datasets_freq_data):
                    positive_freqs = freq_data['positive_freqs']
                    positive_magnitudes = freq_data['positive_magnitudes']
                    positive_magnitudes_dB = 20 * np.log10(positive_magnitudes)
                    freq_magnitude_data = pd.DataFrame({
                        "Frequency (Hz)": positive_freqs,
                        "Magnitude (dB)": positive_magnitudes_dB
                    })
                    freq_magnitude_path = f"{file_base_path}_Dataset_{i + 1}_frequency_magnitude.csv"
                    freq_magnitude_data.to_csv(freq_magnitude_path, index=False)
                    print(f"Dataset {i + 1} frequency data exported to {freq_magnitude_path}.")
            else:
                print("Frequency data unavailable for export.")

            if hasattr(self, 'freq_list_widget'):
                selected_items = self.freq_list_widget.selectedItems()
                if selected_items:
                    selected_freqs = [float(item.text().split()[0]) for item in selected_items]
                    selected_natural_freqs, selected_magnitudes = [], []
                    for freq in selected_freqs:
                        for freq_data in self.datasets_freq_data:
                            positive_freqs = freq_data['positive_freqs']
                            positive_magnitudes = freq_data['positive_magnitudes']
                            if len(positive_freqs) == 0:
                                continue
                            idx = np.abs(positive_freqs - freq).argmin()
                            selected_natural_freqs.append(positive_freqs[idx])
                            selected_magnitudes.append(positive_magnitudes[idx])
                    if selected_natural_freqs and selected_magnitudes:
                        selected_magnitudes_dB = 20 * np.log10(selected_magnitudes)
                        natural_freq_data = pd.DataFrame({
                            "Natural Frequency (Hz)": selected_natural_freqs,
                            "Magnitude (dB)": selected_magnitudes_dB
                        })
                        natural_freq_path = f"{file_base_path}_selected_natural_frequencies.csv"
                        natural_freq_data.to_csv(natural_freq_path, index=False)
                        print(f"Selected frequencies exported to {natural_freq_path}.")
                    else:
                        print("No matching natural frequencies found for export.")
                else:
                    print("No natural frequencies selected for export.")
            else:
                print("Natural frequency data unavailable for export.")

    def plot_time_domain(self, datasets_filtered):
        self.plot_widget_time.clear()
        if hasattr(self, 'time_legend'):
            self.plot_widget_time.removeItem(self.time_legend)
            del self.time_legend
        self.time_legend = self.plot_widget_time.addLegend()

        for i, data_filtered in enumerate(datasets_filtered):
            if not data_filtered.empty:
                time = data_filtered['Time [microseconds]'].to_numpy() / 1e6  # Convert µs to s
                selected_axis = self.axis_selection.currentText()
                selected_accel = self.accel_id_selection.currentText()
                accel_data = 9.8124 * data_filtered[selected_axis].to_numpy()
                pen = pg.mkPen(color=self.dataset_colors[i], width=1)
                self.plot_widget_time.plot(time, accel_data, pen=pen,
                                           name=f"{selected_axis} - Accel {selected_accel} (Dataset {i + 1})")
        if datasets_filtered:
            selected_axis = self.axis_selection.currentText()
            selected_accel = self.accel_id_selection.currentText()
            self.plot_widget_time.setLabel('left', 'Acceleration (m/s²)')
            self.plot_widget_time.setLabel('bottom', 'Time (s)')
            self.plot_widget_time.setTitle(f"Accelerometer {selected_accel}: {selected_axis} (Time Domain)")
        else:
            self.plot_widget_time.clear()
            self.plot_widget_time.setTitle("No Data Loaded")

    def plot_frequency_domain(self, datasets):
        # Process frequency data and also store it in self.datasets_freq_data for later use.
        processed = process_frequency_data(
            datasets,
            self.axis_selection.currentText(),
            self.padding_factor,
            self.plot_mode
        )
        self.datasets_freq_data = processed  # Ensure this is available for update_selected_frequencies
        plot_frequency_data(
            processed,
            self.plot_widget_fft,
            self.freq_list_widget,
            self.tolerance_slider.value(),
            self.dataset_colors,
            self.axis_selection.currentText(),
            self.accel_id_selection.currentText(),
            self.plot_mode,
            self.freq_info_label
        )

    def open_csv(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Open CSV Files", "", "CSV Files (*.csv)")
        if file_paths:
            self.datasets = []
            self.dataset_colors = []  # Reinitialize to avoid index errors
            all_unique_ids = set()
            colors = ['#2541B2', '#D8973C', '#34A5DA', '#F7F5FB', '#A14A44', '#44A1A0']
            for i, file_path in enumerate(file_paths):
                data = self.load_data(file_path, i)
                if not data.empty:
                    self.datasets.append(data)
                    self.dataset_colors.append(colors[i % len(colors)])
                    if 'Accelerometer ID' in data.columns:
                        all_unique_ids.update(map(str, data['Accelerometer ID'].unique()))
            if self.datasets:
                sorted_ids = sorted(all_unique_ids)
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems(sorted_ids)
                self.filter_and_plot_all()
            else:
                print("No valid data loaded from selected files.")

    def load_data(self, file_path, dataset_index):
        try:
            data = pd.read_csv(file_path)
            if not data['Time [microseconds]'].is_monotonic_increasing:
                print("Warning: Time data is not monotonic. Sorting may affect interpretation.")
            data = data.sort_values(by='Time [microseconds]')
            min_time = data['Time [microseconds]'].min()
            data['Time [microseconds]'] -= min_time
            data['Dataset Index'] = dataset_index
            return data
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()

    def filter_and_plot_all(self):
        if not self.datasets:
            print("No datasets loaded to filter and plot.")
            return
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]
        self.datasets_filtered = [df for df in datasets_filtered if not df.empty]
        if not self.datasets_filtered:
            print("No data available after filtering for selected Accelerometer ID.")
            self.plot_time_domain([])
            self.plot_frequency_domain([])
            self.freq_list_widget.clear()
            return
        self.setup_sliders()
        self.update_plot()

    def filter_data(self, dataset):
        if dataset.empty:
            return pd.DataFrame()
        selected_id = self.accel_id_selection.currentText()
        if selected_id and 'Accelerometer ID' in dataset.columns:
            newdata = dataset[dataset['Accelerometer ID'].astype(str) == selected_id]
            return newdata if not newdata.empty else pd.DataFrame()
        return dataset

    def setup_sliders(self):
        min_time_global = float('inf')
        max_time_global = float('-inf')
        if not self.datasets:
            self.start_time_slider.setRange(0, 100)
            self.end_time_slider.setRange(0, 100)
            self.start_time_slider.setValue(0)
            self.end_time_slider.setValue(100)
            self.update_labels()
            print("No datasets loaded to setup sliders.")
            return
        for dataset in self.datasets:
            if not dataset.empty:
                time_values = dataset['Time [microseconds]'].to_numpy() / self.SLIDER_CONVERSION
                min_time_dataset = int(time_values[0])
                max_time_dataset = int(time_values[-1])
                min_time_global = min(min_time_global, min_time_dataset)
                max_time_global = max(max_time_global, max_time_dataset)
        if min_time_global != float('inf'):
            self.start_time_slider.setRange(min_time_global, max_time_global)
            self.end_time_slider.setRange(min_time_global, max_time_global)
            self.start_time_slider.setValue(min_time_global)
            self.end_time_slider.setValue(max_time_global)
        else:
            self.start_time_slider.setRange(0, 100)
            self.end_time_slider.setRange(0, 100)
            self.start_time_slider.setValue(0)
            self.end_time_slider.setValue(100)
            print("No valid time data found in datasets for sliders.")
        self.update_labels()

    def on_slider_value_changed(self, value):
        self.update_labels()
        sender = self.sender()
        if not sender.isSliderDown():
            self.slider_timer.start()

    def on_slider_released(self):
        self.slider_timer.stop()
        self.update_plot()

    def _filter_datasets_by_time(self, datasets, start_time, end_time):
        filtered = [df[(df['Time [microseconds]'] >= start_time) &
                       (df['Time [microseconds]'] <= end_time)]
                    for df in datasets]
        return [df for df in filtered if not df.empty]

    def update_plot(self):
        if not self.datasets:
            print("No data to plot.")
            return
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]
        valid_datasets = [df for df in datasets_filtered if not df.empty]
        if not valid_datasets:
            print("No data available for selected accelerometer ID.")
            self.plot_time_domain([])
            self.plot_frequency_domain([])
            self.freq_list_widget.clear()
            return
        start_time = self.start_time_slider.value() * self.SLIDER_CONVERSION
        end_time = self.end_time_slider.value() * self.SLIDER_CONVERSION
        self.update_labels()
        time_filtered = self._filter_datasets_by_time(valid_datasets, start_time, end_time)
        if not time_filtered:
            print("No data in selected time range.")
            self.plot_time_domain([])
            self.plot_frequency_domain([])
            self.freq_list_widget.clear()
            return
        self.plot_time_domain(time_filtered)
        self.plot_frequency_domain(time_filtered)
