import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QGridLayout, QWidget, QPushButton, QVBoxLayout, \
    QFileDialog, QComboBox, QHBoxLayout, QLabel, \
    QSlider, QListWidget, QListWidgetItem
from scipy.signal import find_peaks, welch

class PlotFFT(QWidget):
    def __init__(self):
        super().__init__()

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

        # Load data with dataset_index
        data = self.load_data(newest_file, dataset_index=0)

        if not data.empty:
            # Filter the data
            data_filtered = self.filter_data(data)

            if not data_filtered.empty:
                # Initialize self.datasets
                self.datasets = [data_filtered]

                # Initialize dataset colors
                self.dataset_colors = [pg.intColor(i) for i in range(len(self.datasets))]

                # Proceed with setup and plotting
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

    def open_csv(self):
        # Open a file dialog to select and load multiple CSV files.
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, "Open CSV Files", "", "CSV Files (*.csv)")

        if file_paths:
            self.datasets = []  # Initialize datasets list to store multiple DataFrames
            all_unique_ids = set()  # To store unique accelerometer IDs across all files
            self.dataset_colors = {}  # Dictionary to store color for each dataset, keyed by index
            colors = ['#2541B2', '#D8973C', '#34A5DA', '#F7F5FB', '#A14A44', '#44A1A0']  # Color palette

            for i, file_path in enumerate(file_paths):
                data = self.load_data(file_path, i)  # Pass index to load_data
                if not data.empty:
                    self.datasets.append(data)  # Append each loaded DataFrame to the datasets list
                    self.dataset_colors[i] = colors[i % len(colors)]  # Assign color from palette, cycling if needed
                    if 'Accelerometer ID' in data.columns:
                        unique_ids = set(
                            map(str, data['Accelerometer ID'].unique()))  # Convert IDs to string to be consistent
                        all_unique_ids.update(unique_ids)  # Add unique IDs to the set

            if self.datasets:
                # Update accelerometer ID combo box with unique IDs from all loaded datasets
                sorted_ids = sorted(list(all_unique_ids))
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems(sorted_ids)

                self.filter_and_plot_all()
            else:
                print("No valid data loaded from the selected files.")

    def load_data(self, file_path, dataset_index):  # Modified load_data to accept dataset_index
        try:
            data = pd.read_csv(file_path)

            # Check if the time data is monotonic
            if not data['Time [microseconds]'].is_monotonic_increasing:
                print("Warning: Time data is not monotonic. Sorting the data might be affecting the interpretation.")

            data = data.sort_values(by='Time [microseconds]')

            # Reset time to start from 0 for each dataset
            min_time = data['Time [microseconds]'].min()
            data['Time [microseconds]'] = data['Time [microseconds]'] - min_time

            # Add a Dataset Index column to identify each dataset later if needed
            data['Dataset Index'] = dataset_index

            # Update accelerometer ID combo box will now be handled in open_csv after loading all datasets

            return data

        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()

    def filter_and_plot_all(self):
        """Filters all loaded datasets, sets up sliders, and plots time and frequency domains."""
        if not self.datasets:
            print("No datasets loaded to filter and plot.")
            return

        # Refilter all datasets based on current accelerometer ID selection
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]
        self.datasets_filtered = [df for df in datasets_filtered if not df.empty]  # Update self.datasets_filtered

        if not self.datasets_filtered:
            print("No data available after filtering for the selected Accelerometer ID.")
            self.plot_time_domain([])  # Clear time domain plot
            self.plot_frequency_domain([])  # Clear frequency domain plot
            self.freq_list_widget.clear()  # Clear frequency list
            return

        self.setup_sliders()  # Setup sliders based on the filtered datasets
        self.update_plot()  # Use update_plot to handle plotting based on current slider and other settings

    def filter_data(self, dataset):
        if dataset.empty:
            return pd.DataFrame()

        # Filter by selected accelerometer ID first
        selected_id = self.accel_id_selection.currentText()
        if selected_id and 'Accelerometer ID' in dataset.columns:
            newdata = dataset[dataset['Accelerometer ID'].astype(str) == selected_id]
        else:
            # If no accelerometer ID is selected or the column is missing, return the dataset unfiltered
            newdata = dataset

        # Check if newdata is empty after accelerometer ID filtering
        if newdata.empty:
            return pd.DataFrame()

        return newdata

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

    def plot_frequency_domain(self, datasets_filtered):
        self.plot_widget_fft.clear()
        self.freq_list_widget.clear()
        self.datasets_freq_data = []  # List to store frequency data for each dataset

        selected_axis = self.axis_selection.currentText()
        selected_accel = self.accel_id_selection.currentText()
        tolerance = self.tolerance_slider.value()
        padding_factor = self.padding_factor

        # Add a legend if it doesn't already exist
        if not hasattr(self, 'fft_legend'):
            self.fft_legend = self.plot_widget_fft.addLegend()

        # Initialize list to accumulate all natural frequencies
        all_natural_frequencies = []

        for i, data in enumerate(datasets_filtered):
            if data.empty:
                continue

            # Extract data and compute FFT or PSD based on plot_mode
            accel_data = 9.8124 * data[selected_axis].to_numpy()
            time = data['Time [microseconds]'].to_numpy()

            N = len(accel_data)
            if N < 2:
                print("Not enough data points for FFT.")
                continue

            dt = np.mean(np.diff(time)) * 1e-6  # Time difference in microseconds

            if dt <= 0:
                print("Invalid time difference; cannot compute FFT.")
                continue

            # Apply a window function to reduce spectral leakage
            window = np.blackman(N)
            accel_data_windowed = accel_data * window

            # Zero-padding for higher frequency resolution
            padded_length = int(N * padding_factor)
            accel_data_padded = np.pad(accel_data_windowed, (0, padded_length - N), mode='constant')

            if self.plot_mode == "FFT":
                # Compute FFT with zero-padded data
                fft_accel = np.fft.fft(accel_data_padded)
                freq = np.fft.fftfreq(len(accel_data_padded), d=dt)
                magnitudes = np.abs(fft_accel)

                # Keep only the positive half of the spectrum
                positive_freqs = freq[:len(freq) // 2]
                positive_magnitudes = magnitudes[:len(magnitudes) // 2]

            elif self.plot_mode == "PSD":
                # Use padded data as required
                padded_length = len(accel_data_padded)

                # Dynamically compute segment length: use a fraction of padded_length.
                dynamic_factor = 2  # Adjust this factor as needed.

                nperseg = int(padded_length / dynamic_factor) if padded_length >= dynamic_factor else padded_length
                noverlap = int(nperseg / 2)  # Typically, 50% overlap works well.

                # Compute PSD using Welch's method with a standard window (Hann is common)
                freq, psd = welch(accel_data_padded, fs=1 / dt, window='blackman', nperseg=nperseg, noverlap=noverlap)
                positive_freqs = freq

                # Convert to dB without extra scaling; adjust if you need a specific offset.
                positive_magnitudes = psd*10**(padding_factor)


            # Filter out frequencies below a certain threshold
            min_frequency = 2  # Hz
            valid_indices = positive_freqs >= min_frequency
            positive_freqs = positive_freqs[valid_indices]
            positive_magnitudes = positive_magnitudes[valid_indices]

            # Store frequency data for this dataset
            self.datasets_freq_data.append({
                'positive_freqs': positive_freqs,
                'positive_magnitudes': positive_magnitudes
            })

            # Peak detection for this dataset
            peaks, properties = find_peaks(positive_magnitudes, height=tolerance)
            natural_frequencies = positive_freqs[peaks]
            peak_magnitudes = positive_magnitudes[peaks]

            # Accumulate frequencies for the frequency list
            all_natural_frequencies.extend(natural_frequencies)

            # Plot the FFT/PSD data for this dataset and add to legend
            pen = pg.mkPen(color=self.dataset_colors[i], width=1)
            plot_item = self.plot_widget_fft.plot(positive_freqs, positive_magnitudes, pen=pen,
                                                  name=f"{selected_axis} - Accel {selected_accel} (Dataset {i + 1})")

            # Plot the peaks (natural frequencies) as dots for this dataset
            symbol_pen = pg.mkPen(color=self.dataset_colors[i])
            symbol_brush = pg.mkBrush(color=self.dataset_colors[i])
            fft_peak_item = pg.ScatterPlotItem(
                x=natural_frequencies,
                y=peak_magnitudes,
                pen=symbol_pen,
                brush=symbol_brush,
                size=10,  # Adjust size as needed
                symbol='o'
            )
            self.plot_widget_fft.addItem(fft_peak_item)
            fft_peak_item.setZValue(10)  # Ensure the peaks appear on top

        # Update the QListWidget with combined natural frequencies from all datasets
        unique_natural_frequencies = np.unique(np.round(all_natural_frequencies, decimals=2))
        for freq in unique_natural_frequencies:
            self.freq_list_widget.addItem(f"{freq:.2f} Hz")

        # Adjust the plot ranges to include all data
        self.plot_widget_fft.enableAutoRange(axis='xy', enable=True)

        # Update plot labels and title
        if datasets_filtered:
            mode_title = "FFT" if self.plot_mode == "FFT" else "PSD"
            self.plot_widget_fft.setLabel('left', 'Magnitude')
            self.plot_widget_fft.setLabel('bottom', 'Frequency (Hz)')
            self.plot_widget_fft.setTitle(
                f"Accelerometer {selected_accel}: {selected_axis} {mode_title} (Frequency Domain)"
            )

            # Inside plot_frequency_domain, after computing dt and freq:
            sampling_freq = 1 / dt  # Compute the sampling frequency
            self.freq_info_label.setText(f"Freq: {dt:.10f} Hz\n1/dt: {sampling_freq:.4f} Hz")

        else:
            self.plot_widget_fft.clear()
            self.plot_widget_fft.setTitle("No Data Loaded")
            self.freq_list_widget.clear()

    def setup_sliders(self):
        min_time_global = float('inf')
        max_time_global = float('-inf')

        if not self.datasets:  # Handle case where datasets is empty
            self.start_time_slider.setRange(0, 100)
            self.end_time_slider.setRange(0, 100)
            self.start_time_slider.setValue(0)
            self.end_time_slider.setValue(100)
            self.update_labels()
            print("No datasets loaded to setup sliders.")
            return

        for dataset in self.datasets:  # Iterate through all loaded datasets to find global min/max time
            if not dataset.empty:
                time_values = (dataset['Time [microseconds]'].to_numpy()) / 100000
                min_time_dataset = (int(time_values[0]))
                max_time_dataset = (int(time_values[-1]))

                min_time_global = min(min_time_global, min_time_dataset)
                max_time_global = max(max_time_global, max_time_dataset)

        if min_time_global != float('inf'):  # Check if any data was loaded to set slider ranges
            # Set the range based on global min/max time values
            self.start_time_slider.setRange(min_time_global, max_time_global)
            self.end_time_slider.setRange(min_time_global, max_time_global)

            # Set default values to the global range
            self.start_time_slider.setValue(min_time_global)
            self.end_time_slider.setValue(max_time_global)
        else:
            self.start_time_slider.setRange(0, 100)  # Reset to default ranges if no data
            self.end_time_slider.setRange(0, 100)
            self.start_time_slider.setValue(0)
            self.end_time_slider.setValue(100)
            print("No valid time data found in datasets to setup sliders.")

        # Update labels in either case to ensure they reflect slider values
        self.update_labels()

    def on_slider_value_changed(self, value):
        sender = self.sender()  # Get the slider that triggered the event

        # Update labels to reflect current slider values
        self.update_labels()

        # Check if the slider is currently being dragged
        if sender.isSliderDown():
            # Slider is being dragged; do not update yet
            pass
        else:
            # Slider is not being dragged (value changed via scroll wheel or keyboard)
            self.slider_timer.start()

    def on_slider_released(self):
        # Stop any ongoing timer
        self.slider_timer.stop()

        # Update the plot immediately when the slider is released
        self.update_plot()

    def update_plot(self):
        if not self.datasets:  # Check if datasets list is empty
            print("No data to plot.")
            return

        # Refilter the data based on current accelerometer ID
        datasets_filtered = [self.filter_data(dataset) for dataset in self.datasets]

        valid_datasets_filtered = [df for df in datasets_filtered if not df.empty]  # Remove empty DataFrames from the list

        if not valid_datasets_filtered:  # Check if any valid data after filtering
            print("No data available for selected accelerometer ID across datasets.")
            self.plot_time_domain([])  # Clear time domain plot
            self.plot_frequency_domain([])  # Clear freq domain - pass empty list
            self.freq_list_widget.clear()  # Clear freq list
            return

        # Get current time values from sliders (global time range)
        start_time = (self.start_time_slider.value()) * 100000
        end_time = (self.end_time_slider.value()) * 100000

        # Update labels to reflect current slider values
        self.update_labels()

        # Filter data based on time range for each dataset, using the GLOBAL time range
        time_filtered_datasets = []
        for data_filtered in valid_datasets_filtered:
            time_filtered_data = data_filtered[
                (data_filtered['Time [microseconds]'] >= start_time) &
                (data_filtered['Time [microseconds]'] <= end_time)
            ]
            time_filtered_datasets.append(time_filtered_data)

        valid_time_filtered_datasets = [df for df in time_filtered_datasets if not df.empty]  # Remove empty datasets after time filter

        if not valid_time_filtered_datasets:  # Check if any data remains after time filtering
            print("No data in selected time range across datasets.")
            self.plot_time_domain([])  # Clear time domain plot
            self.plot_frequency_domain([])  # Clear freq domain - pass empty list
            self.freq_list_widget.clear()  # Clear freq list
            return

        self.plot_time_domain(valid_time_filtered_datasets)  # Pass the list of datasets
        self.plot_frequency_domain(valid_time_filtered_datasets)  # Pass the list to freq domain as well, no time range needed here as it uses full data for FFT/PSD