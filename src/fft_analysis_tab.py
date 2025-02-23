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
    for data in datasets:
        if data.empty:
            continue

        accel_data = 9.8124 * data[selected_axis].to_numpy()
        time_data = data['Time [microseconds]'].to_numpy()
        if np.max(time_data) < 1000:
            time = time_data
            print("Time data detected in seconds.")
        else:
            time = time_data * 1e-6
            #print("Time data detected in microseconds, converting to seconds.")

        N = len(accel_data)
        if N < 2:
            print("Not enough data points for FFT/PSD.")
            continue

        dt = np.mean(np.diff(time))
        if dt <= 0:
            #print("Invalid time difference; cannot compute frequency data.")
            continue

        window = np.blackman(N)
        accel_data_windowed = accel_data * window

        padded_length = int(N * padding_factor)
        accel_data_padded = np.pad(accel_data_windowed, (0, padded_length - N), mode='constant')

        if plot_mode == "FFT":
            fft_accel = np.fft.fft(accel_data_padded)
            freq = np.fft.fftfreq(len(accel_data_padded), d=dt)
            magnitudes = np.abs(fft_accel)
            positive_freqs = freq[:len(freq) // 2]
            positive_magnitudes = magnitudes[:len(magnitudes) // 2]
        elif plot_mode == "PSD":
            padded_len = len(accel_data_padded)
            dynamic_factor = 2  # adjust as needed
            nperseg = int(padded_len / dynamic_factor) if padded_len >= dynamic_factor else padded_len
            noverlap = int(nperseg / 2)
            freq, psd = welch(accel_data_padded, fs=1/dt, window='blackman',
                              nperseg=nperseg, noverlap=noverlap)
            positive_freqs = freq
            positive_magnitudes = psd * (10 ** padding_factor)
        else:
            print("Unknown plot mode: {}".format(plot_mode))
            continue

        min_frequency = 2  # Hz
        valid_indices = positive_freqs >= min_frequency
        positive_freqs = positive_freqs[valid_indices]
        positive_magnitudes = positive_magnitudes[valid_indices]

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
    def __init__(self):
        super().__init__()
        self.dataset_colors = ["r", "g", "b", "y", "m", "c", "k"]  # Example colors for datasets
        self.datasets_freq_data = []

        # Default padding factor
        self.padding_factor = 5

        # Initialize the QTimer for debouncing
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_plot)

        # Set up the main widget layout
        main_layout = QHBoxLayout()  # Use QHBoxLayout for left-right arrangement

        # Create the left layout (Plot and controls)
        left_layout = QVBoxLayout()

        # Create the toggle button for PSD/FFT
        self.toggle_button = QPushButton("Show PSD")
        self.toggle_button.clicked.connect(self.toggle_plot)

        # Create a container widget for the plots
        self.container_widget = QWidget()
        self.container_widget.setObjectName("graphy")  # Set object name
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)  # Margin to space the PlotWidget from the edges

        # Create two PlotWidgets: one for time domain and one for frequency domain
        self.plot_widget_time = pg.PlotWidget()  # Time domain plot
        self.plot_widget_time.setBackground("#2b2b2b")
        self.plot_widget_fft = pg.PlotWidget()  # Frequency domain plot
        self.plot_widget_fft.setBackground("#2b2b2b")

        container_layout.addWidget(self.plot_widget_time)
        container_layout.addWidget(self.plot_widget_fft)

        # Add the container widget (with the plots) to the left layout
        left_layout.addWidget(self.container_widget)

        # Create sliders for setting the FFT time interval and tolerance
        self.start_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)

        # Set ranges for sliders based on data length and tolerance
        self.start_time_slider.setRange(0, 100)
        self.end_time_slider.setRange(0, 100)
        self.tolerance_slider.setRange(1, 10000)  # Example range for tolerance

        self.start_time_slider.setValue(0)
        self.end_time_slider.setValue(100)
        self.tolerance_slider.setValue(1000)  # default tolerance

        # Create the combo box for axis selection
        self.axis_selection = QComboBox()
        self.axis_selection.addItems(["X Acceleration", "Y Acceleration", "Z Acceleration"])
        self.axis_selection.currentIndexChanged.connect(self.update_plot)  # Update plot on selection change

        # Add accelerometer ID selection combo box
        self.accel_id_selection = QComboBox()
        self.accel_id_selection.currentIndexChanged.connect(self.update_plot)

        # Add labels for the sliders
        self.start_time_label = QLabel("Start Time: 0 µs")
        self.end_time_label = QLabel("End Time: 100 µs")
        self.tolerance_label = QLabel("Tolerance: 1000 dB")

        # Create the export button
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_data)

        # Create the open CSV button
        self.open_button = QPushButton("Open CSV")
        self.open_button.clicked.connect(self.open_csv)

        # Create the open CSV button
        self.open_recent = QPushButton("Open Latest Sample")
        self.open_recent.clicked.connect(self.open_last_sample)

        # Create a QHBoxLayout for the accelerometer selection row
        accel_row = QHBoxLayout()

        # Add the widgets to the row
        accel_row.addWidget(QLabel("Accelerometer ID and Axis:"),0)  # Label for accelerometer selection
        accel_row.addWidget(self.accel_id_selection,1)  # Accelerometer ID selection combo box
        accel_row.addWidget(self.axis_selection,1)  # Axis selection combo box

        # Add the horizontal layout to the left layout
        left_layout.addLayout(accel_row)

        # Initialize your QTimer
        self.slider_timer = QTimer()
        self.slider_timer.setSingleShot(True)
        self.slider_timer.setInterval(200)  # Interval in milliseconds (adjust as needed)
        self.slider_timer.timeout.connect(self.update_plot)

        # Create a QGridLayout for the sliders and their labels
        slider_grid = QGridLayout()

        # Add labels and sliders next to each other in rows
        slider_grid.addWidget(self.start_time_label, 0, 0)
        slider_grid.addWidget(self.start_time_slider, 0, 1)
        slider_grid.addWidget(self.end_time_label, 1, 0)
        slider_grid.addWidget(self.end_time_slider, 1, 1)
        slider_grid.addWidget(self.tolerance_label, 2, 0)
        slider_grid.addWidget(self.tolerance_slider, 2, 1)

        # Add the slider grid to the left layout
        left_layout.addLayout(slider_grid)

        # *** Remove the disconnect calls since they're not necessary ***

        # Connect valueChanged signals to the custom handler
        self.start_time_slider.valueChanged.connect(self.on_slider_value_changed)
        self.end_time_slider.valueChanged.connect(self.on_slider_value_changed)
        self.tolerance_slider.valueChanged.connect(self.on_slider_value_changed)

        # Connect sliderReleased signals to the release handler
        self.start_time_slider.sliderReleased.connect(self.on_slider_released)
        self.end_time_slider.sliderReleased.connect(self.on_slider_released)
        self.tolerance_slider.sliderReleased.connect(self.on_slider_released)

        # Assuming `left_layout` is your left side layout, create a QGridLayout for the buttons
        button_grid = QGridLayout()

        # Add buttons to the grid in a 2x2 pattern
        button_grid.addWidget(self.export_button, 0, 0)  # Row 0, Column 0
        button_grid.addWidget(self.open_button, 0, 1)  # Row 0, Column 1
        button_grid.addWidget(self.open_recent, 1, 0)  # Row 1, Column 0
        button_grid.addWidget(self.toggle_button, 1, 1)  # Row 1, Column 1

        # Add the button grid to the left layout
        left_layout.addLayout(button_grid)

        # Create the right layout (QListWidget)
        right_layout = QVBoxLayout()

        # Frequency List Widget
        self.freq_list_widget = QListWidget()
        self.freq_list_widget.setSelectionMode(QListWidget.MultiSelection)  # Allow multiple selections
        self.freq_list_widget.addItem("Awaiting Data...")
        self.freq_list_widget.setMinimumWidth(125)  # Set minimum width

        right_layout.addWidget(self.freq_list_widget)

        # Create a QLabel for frequency information
        self.freq_info_label = QLabel("Freq: -- Hz\n1/dt: -- Hz")
        self.freq_info_label.setAlignment(Qt.AlignCenter)  # Align text to the right

        right_layout.addWidget(self.freq_info_label)  # Add label to the right layout

        # Add the left and right layouts to the main layout
        main_layout.addLayout(left_layout, 3)  # Left layout takes 3 parts of space
        main_layout.addLayout(right_layout, 1)  # Right layout takes 1 part of space

        # Set the layout to the main widget
        self.setLayout(main_layout)

        # Load, filter, and plot the data
        self.data = pd.DataFrame()  # Empty DataFrame initially
        self.data_filtered = pd.DataFrame()

        self.positive_freqs = np.array([])  # Placeholder for frequency data
        self.positive_magnitudes_dB = np.array([])  # Placeholder for magnitudes

        self.plot_mode = "FFT"  # Default mode

        # Store natural frequency points
        self.fft_peaks = []  # Holds the plot items for natural frequency markers
        self.natural_frequencies = np.array([])

        # Connect the selection change signal from the QListWidget
        self.freq_list_widget.itemSelectionChanged.connect(self.update_selected_frequencies)

    def set_background(self, hex_color):
        self.color_hex = hex_color
        self.plot_widget_time.setBackground(self.color_hex)
        self.plot_widget_fft.setBackground(self.color_hex)

    def update_selected_frequencies(self):
        selected_items = self.freq_list_widget.selectedItems()

        # Get the selected frequencies
        selected_freqs = [float(item.text().split()[0]) for item in selected_items]

        # Clear existing selected peaks if any
        if hasattr(self, 'selected_peaks_item'):
            self.plot_widget_fft.removeItem(self.selected_peaks_item)
            del self.selected_peaks_item

        # Collect data for the selected frequencies
        selected_natural_freqs = []
        selected_magnitudes = []

        # Loop over stored frequency data for each dataset
        for freq_data in self.datasets_freq_data:
            positive_freqs = freq_data['positive_freqs']
            positive_magnitudes = freq_data['positive_magnitudes']

            if len(positive_freqs) == 0:
                continue

            for freq in selected_freqs:
                # Find the index of the frequency closest to the selected frequency
                idx = np.abs(positive_freqs - freq).argmin()
                selected_natural_freqs.append(positive_freqs[idx])
                selected_magnitudes.append(positive_magnitudes[idx])

        # Plot the selected frequencies as peaks
        if selected_natural_freqs and selected_magnitudes:
            symbol_pen = pg.mkPen('w')  # White color for selected peaks
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
        """ Update the padding factor when changed in settings """
        self.padding_factor = padding_factor
        print(f"Padding Factor updated to: {self.padding_factor}")
        self.update_plot()

    def open_last_sample(self):
        import os
        import re

        directory = "../Cached_Samples/"
        pattern = r"samples_\d{8}_\d{6}\.csv"
        files = [f for f in os.listdir(directory) if re.match(pattern, f)]
        if not files:
            print("No matching files found.")
            return

        newest_file = max([os.path.join(directory, f) for f in files], key=os.path.getmtime)
        print(f"Opening newest file: {newest_file}")

        # Load data
        data = self.load_data(newest_file, dataset_index=0)

        if not data.empty:
            # Update accelerometer ID selection
            if 'Accelerometer ID' in data.columns:
                unique_ids = data['Accelerometer ID'].astype(str).unique()
                sorted_ids = sorted(unique_ids)
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems(sorted_ids)
                if sorted_ids:
                    self.accel_id_selection.setCurrentIndex(0)  # Select first ID

            # Filter data
            data_filtered = self.filter_data(data)

            if not data_filtered.empty:
                self.datasets = [data_filtered]
                self.dataset_colors = [pg.intColor(0)]  # Assign color for single dataset
                self.setup_sliders()
                self.plot_time_domain(self.datasets)
                self.plot_frequency_domain(self.datasets)
            else:
                print("No data available after filtering.")
        else:
            print("No data loaded from the file.")

    def toggle_plot(self):
        # Toggle between PSD and FFT plotting.
        if self.plot_mode == "FFT":
            self.plot_mode = "PSD"
            self.toggle_button.setText("Show FFT")
        else:
            self.plot_mode = "FFT"
            self.toggle_button.setText("Show PSD")

        # Update the plot with the current mode
        self.update_plot()

    def update_labels(self):
        # Update the labels to show actual time values and tolerance.
        start_time = (self.start_time_slider.value() )*100000 # Get actual time values from sliders
        end_time = (self.end_time_slider.value() )*100000
        tolerance_value = self.tolerance_slider.value()

        # Update the labels with the actual time values
        self.start_time_label.setText(f"Start Time: {start_time} µs")
        self.end_time_label.setText(f"End Time: {end_time} µs")
        self.tolerance_label.setText(f"Tolerance: {tolerance_value} dB")

    def export_data(self):
        # Check if there are any filtered datasets to export
        if not self.datasets_filtered or all(df.empty for df in self.datasets_filtered):
            print("No data to export.")
            return

        # Show file dialog to select where to save the CSV files
        file_dialog = QFileDialog()
        file_base_path, _ = file_dialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")

        if file_base_path:
            # Export trimmed time-range data for each dataset
            for i, trimmed_data in enumerate(self.datasets_filtered):
                if trimmed_data.empty:
                    continue

                # Get the current slider time range
                start_time = self.start_time_slider.value()
                end_time = self.end_time_slider.value()

                # Filter the data within the selected time range
                trimmed_data_in_range = trimmed_data[
                    (trimmed_data['Time [microseconds]'] >= start_time * 1e6) &
                    (trimmed_data['Time [microseconds]'] <= end_time * 1e6)
                    ]

                if trimmed_data_in_range.empty:
                    print(f"No data found within the selected time range for Dataset {i + 1}.")
                    continue

                # Export trimmed data to CSV
                trimmed_data_path = f"{file_base_path}_Dataset_{i + 1}_trimmed_data.csv"
                trimmed_data_in_range.to_csv(trimmed_data_path, index=False)
                print(f"Trimmed acceleration data for Dataset {i + 1} exported to {trimmed_data_path}.")

            # Export frequency and magnitude data for each dataset
            if hasattr(self, 'datasets_freq_data') and self.datasets_freq_data:
                for i, freq_data in enumerate(self.datasets_freq_data):
                    positive_freqs = freq_data['positive_freqs']
                    positive_magnitudes = freq_data['positive_magnitudes']

                    # Convert magnitudes to dB if needed (assuming you may want to)
                    positive_magnitudes_dB = 20 * np.log10(positive_magnitudes)

                    freq_magnitude_data = pd.DataFrame({
                        "Frequency (Hz)": positive_freqs,
                        "Magnitude (dB)": positive_magnitudes_dB
                    })

                    freq_magnitude_path = f"{file_base_path}_Dataset_{i + 1}_frequency_magnitude.csv"
                    freq_magnitude_data.to_csv(freq_magnitude_path, index=False)
                    print(f"Frequency and magnitude data for Dataset {i + 1} exported to {freq_magnitude_path}.")
            else:
                print("Frequency and magnitude data are not available for export.")

            # Export selected natural frequencies
            if hasattr(self, 'freq_list_widget'):
                selected_items = self.freq_list_widget.selectedItems()
                if selected_items:
                    selected_freqs = [float(item.text().split()[0]) for item in selected_items]

                    # Collect natural frequencies and magnitudes from all datasets
                    selected_natural_freqs = []
                    selected_magnitudes = []

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
                        # Convert magnitudes to dB if needed
                        selected_magnitudes_dB = 20 * np.log10(selected_magnitudes)

                        natural_freq_data = pd.DataFrame({
                            "Natural Frequency (Hz)": selected_natural_freqs,
                            "Magnitude (dB)": selected_magnitudes_dB
                        })

                        natural_freq_path = f"{file_base_path}_selected_natural_frequencies.csv"
                        natural_freq_data.to_csv(natural_freq_path, index=False)
                        print(f"Selected natural frequencies exported to {natural_freq_path}.")
                    else:
                        print("No matching natural frequencies found in datasets for export.")
                else:
                    print("No natural frequencies selected for export.")
            else:
                print("Natural frequency data is not available for export.")

    def plot_time_domain(self, datasets_filtered):
        self.plot_widget_time.clear()  # Clear plot before plotting new data

        # Remove existing legend if it exists
        if hasattr(self, 'time_legend'):
            self.plot_widget_time.removeItem(self.time_legend)
            del self.time_legend

        # Add a new legend
        self.time_legend = self.plot_widget_time.addLegend()

        for i, data_filtered in enumerate(datasets_filtered):
            if not data_filtered.empty:
                # Extract time and acceleration data
                time = data_filtered['Time [microseconds]'].to_numpy() / 1e6  # Convert to seconds
                selected_axis = self.axis_selection.currentText()  # Selected axis (e.g., X, Y, Z)
                selected_accel = self.accel_id_selection.currentText()  # Selected accelerometer ID
                accel_data = 9.8124 * data_filtered[selected_axis].to_numpy()  # Get selected axis data

                pen = pg.mkPen(color=self.dataset_colors[i], width=1)  # Get color for dataset

                # Plot each dataset and add to legend
                plot_item = self.plot_widget_time.plot(time, accel_data, pen=pen,
                                                       name=f"{selected_axis} - Accel {selected_accel} (Dataset {i + 1})")

        # Update plot labels and title
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
        # Use the global functions defined above.
        processed = process_frequency_data(datasets, self.axis_selection.currentText(),
                                           self.padding_factor, self.plot_mode)
        plot_frequency_data(processed, self.plot_widget_fft, self.freq_list_widget,
                            self.tolerance_slider.value(), self.dataset_colors,
                            self.axis_selection.currentText(), self.accel_id_selection.currentText(),
                            self.plot_mode, self.freq_info_label)

    def open_csv(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Open CSV Files", "", "CSV Files (*.csv)")
        if file_paths:
            self.datasets = []
            all_unique_ids = set()
            self.dataset_colors = {}
            colors = ['#2541B2', '#D8973C', '#34A5DA', '#F7F5FB', '#A14A44', '#44A1A0']
            for i, file_path in enumerate(file_paths):
                data = self.load_data(file_path, i)
                if not data.empty:
                    self.datasets.append(data)
                    self.dataset_colors[i] = colors[i % len(colors)]
                    if 'Accelerometer ID' in data.columns:
                        unique_ids = set(map(str, data['Accelerometer ID'].unique()))
                        all_unique_ids.update(unique_ids)
            if self.datasets:
                sorted_ids = sorted(list(all_unique_ids))
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems(sorted_ids)
                self.filter_and_plot_all()
            else:
                print("No valid data loaded from the selected files.")

    def load_data(self, file_path, dataset_index):
        try:
            data = pd.read_csv(file_path)
            if not data['Time [microseconds]'].is_monotonic_increasing:
                print("Warning: Time data is not monotonic. Sorting may affect interpretation.")
            data = data.sort_values(by='Time [microseconds]')
            min_time = data['Time [microseconds]'].min()
            data['Time [microseconds]'] = data['Time [microseconds]'] - min_time
            data['Dataset Index'] = dataset_index
            return data
        except Exception as e:
            print("Error loading data: {}".format(e))
            return pd.DataFrame()

    def filter_and_plot_all(self):
        if not hasattr(self, 'datasets') or not self.datasets:
            print("No datasets loaded to filter and plot.")
            return
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]
        self.datasets_filtered = [df for df in datasets_filtered if not df.empty]
        if not self.datasets_filtered:
            print("No data available after filtering for the selected Accelerometer ID.")
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
        else:
            newdata = dataset
        return newdata if not newdata.empty else pd.DataFrame()

    def setup_sliders(self):
        min_time_global = float('inf')
        max_time_global = float('-inf')
        if not hasattr(self, 'datasets') or not self.datasets:
            self.start_time_slider.setRange(0, 100)
            self.end_time_slider.setRange(0, 100)
            self.start_time_slider.setValue(0)
            self.end_time_slider.setValue(100)
            self.update_labels()
            print("No datasets loaded to setup sliders.")
            return
        for dataset in self.datasets:
            if not dataset.empty:
                time_values = dataset['Time [microseconds]'].to_numpy() / 100000
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
            print("No valid time data found in datasets to setup sliders.")
        self.update_labels()

    def on_slider_value_changed(self, value):
        sender = self.sender()
        self.update_labels()
        if not sender.isSliderDown():
            self.slider_timer.start()

    def on_slider_released(self):
        self.slider_timer.stop()
        self.update_plot()

    def update_plot(self):
        if not hasattr(self, 'datasets') or not self.datasets:
            print("No data to plot.")
            return
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]
        valid_datasets_filtered = [df for df in datasets_filtered if not df.empty]
        if not valid_datasets_filtered:
            print("No data available for selected accelerometer ID across datasets.")
            self.plot_time_domain([])
            self.plot_frequency_domain([])
            self.freq_list_widget.clear()
            return
        start_time = self.start_time_slider.value() * 100000
        end_time = self.end_time_slider.value() * 100000
        self.update_labels()
        time_filtered_datasets = []
        for data_filtered in valid_datasets_filtered:
            tf_data = data_filtered[
                (data_filtered['Time [microseconds]'] >= start_time) &
                (data_filtered['Time [microseconds]'] <= end_time)
            ]
            time_filtered_datasets.append(tf_data)
        valid_time_filtered_datasets = [df for df in time_filtered_datasets if not df.empty]
        if not valid_time_filtered_datasets:
            print("No data in selected time range across datasets.")
            self.plot_time_domain([])
            self.plot_frequency_domain([])
            self.freq_list_widget.clear()
            return
        self.plot_time_domain(valid_time_filtered_datasets)
        self.plot_frequency_domain(valid_time_filtered_datasets)