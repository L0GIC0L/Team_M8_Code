import os
import re

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

        self.start_time_slider.valueChanged.connect(self.update_plot)
        self.end_time_slider.valueChanged.connect(self.update_plot)
        self.tolerance_slider.valueChanged.connect(self.update_plot)

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

        # Create a QGridLayout for the sliders and their labels
        slider_grid = QGridLayout()

        # Add labels and sliders next to each other in rows
        slider_grid.addWidget(self.start_time_label, 0, 0)  # Row 0, Column 0
        slider_grid.addWidget(self.start_time_slider, 0, 1)  # Row 0, Column 1

        slider_grid.addWidget(self.end_time_label, 1, 0)  # Row 1, Column 0
        slider_grid.addWidget(self.end_time_slider, 1, 1)  # Row 1, Column 1

        slider_grid.addWidget(self.tolerance_label, 2, 0)  # Row 2, Column 0
        slider_grid.addWidget(self.tolerance_slider, 2, 1)  # Row 2, Column 1

        # Add the slider grid to the left layout
        left_layout.addLayout(slider_grid)

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
        self.freq_list_widget = QListWidget()
        self.freq_list_widget.setSelectionMode(QListWidget.MultiSelection)  # Allow multiple selections
        self.freq_list_widget.addItem("Awaiting Data...")
        self.freq_list_widget.setMinimumWidth(125)  # Set your desired minimum width here (in pixels)

        # Add the QListWidget to the right layout
        right_layout.addWidget(self.freq_list_widget)

        # Add the left and right layouts to the main layout
        main_layout.addLayout(left_layout, 3)  # Left layout takes 3 parts of the space
        main_layout.addLayout(right_layout, 1)  # Right layout takes 1 part of the space

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

    def plot_frequency_domain(self, data, start_time, end_time, tolerance, padding_factor):
        # Extract data and compute FFT or PSD based on plot_mode
        selected_axis = self.axis_selection.currentText()
        selected_accel = self.accel_id_selection.currentText()
        accel_data = 9.8124 * data[selected_axis].to_numpy()
        time = data['Time [microseconds]'].to_numpy()
        self.padding_factor = padding_factor

        N = len(accel_data)
        if N < 2:
            print("Not enough data points for FFT.")
            return

        dt = np.mean(np.diff(time)) * 1e-6  # Time difference in seconds
        if dt <= 0:
            print("Invalid time difference; cannot compute FFT.")
            return

        hamming_window = np.blackman(N)
        accel_data_windowed = accel_data * hamming_window

        # Zero-padding: Calculate the padded length based on the padding factor
        padded_length = int(N * self.padding_factor)
        accel_data_padded = np.pad(accel_data_windowed, (0, padded_length - N), mode='constant')

        if self.plot_mode == "FFT":
            # Compute FFT with zero-padded data
            freq = np.fft.fftfreq(padded_length, d=dt)
            fft_accel = np.fft.fft(accel_data_padded)
            magnitudes = np.abs(fft_accel)[:padded_length // 2]  # Use raw magnitudes

            self.positive_freqs = freq[:padded_length // 2]
            self.positive_magnitudes = magnitudes  # Store raw magnitudes

        elif self.plot_mode == "PSD":
            freq, psd = welch(accel_data_padded, fs=1/dt, nperseg=padded_length, noverlap=padded_length//2)
            self.positive_freqs = freq
            self.positive_magnitudes = (1e9)*psd

        # Filter out frequencies below 0.5 Hz
        min_frequency = 2
        valid_indices = self.positive_freqs >= min_frequency
        self.positive_freqs = self.positive_freqs[valid_indices]
        self.positive_magnitudes = self.positive_magnitudes[valid_indices]

        # Update peaks after filtering
        peaks, _ = find_peaks(self.positive_magnitudes, height=tolerance)
        self.natural_frequencies = self.positive_freqs[peaks]
        self.peak_magnitudes = self.positive_magnitudes[peaks]

        # Update the QListWidget with natural frequencies
        self.freq_list_widget.clear()  # Clear the list
        for freq in self.natural_frequencies:
            self.freq_list_widget.addItem(f"{freq:.2f} Hz")

        # Plot data
        if not hasattr(self, 'fft_plot_data_item'):
            fft_pen = pg.mkPen(color='#F7F5FB', width=1)
            self.fft_plot_data_item = self.plot_widget_fft.plot(pen=fft_pen)

        self.fft_plot_data_item.setData(self.positive_freqs, self.positive_magnitudes)

        # Plot peaks (natural frequencies)
        if not hasattr(self, 'fft_peak_item'):
            symbol_pen = pg.mkPen('#D8973C')
            symbol_brush = pg.mkBrush('#D8973C')
            self.fft_peak_item = self.plot_widget_fft.plot(pen=None, symbol='o', symbolPen=symbol_pen,
                                                           symbolBrush=symbol_brush)

        self.fft_peak_item.setData(self.natural_frequencies, self.peak_magnitudes)

        # Update plot labels and title
        self.plot_widget_fft.setLabel('left', 'Magnitude')
        self.plot_widget_fft.setLabel('bottom', 'Frequency (Hz)')
        mode_title = "FFT" if self.plot_mode == "FFT" else "PSD"
        self.plot_widget_fft.setTitle(
            f"Accelerometer {selected_accel}: {selected_axis} {mode_title} (Frequency Domain)")

    def update_selected_frequencies(self):
        selected_items = self.freq_list_widget.selectedItems()

        # Get the selected frequencies
        selected_freqs = [float(item.text().split()[0]) for item in selected_items]

        # Find the indices of the selected frequencies in the positive frequencies
        selected_indices = []
        for freq in selected_freqs:
            # Find the closest index to the selected frequency
            idx = np.abs(self.positive_freqs - freq).argmin()
            selected_indices.append(idx)

        # Create an array of the selected frequencies and magnitudes
        selected_natural_freqs = self.positive_freqs[selected_indices]

        # Get corresponding magnitudes from the raw FFT magnitudes
        selected_magnitudes = self.positive_magnitudes[selected_indices]

        # Ensure both arrays have the same length for proper plotting
        if len(selected_natural_freqs) > 0 and len(selected_magnitudes) > 0:
            # Update the plot: set the selected frequencies and their magnitudes as the new data for the peaks
            self.fft_peak_item.setData(selected_natural_freqs, selected_magnitudes)
        else:
            # Clear the plot if no frequencies are selected
            self.fft_peak_item.setData([], [])

    def update_padding_factor(self, padding_factor):
        """ Update the padding factor when changed in settings """
        self.padding_factor = padding_factor
        print(f"Padding Factor updated to: {self.padding_factor}")
        self.update_plot()

    def open_last_sample(self):
        directory, pattern = "../Cached_Samples/", r"samples_\d{8}_\d{6}\.csv"
        files = [f for f in os.listdir(directory) if re.match(pattern, f)]
        if not files:
            print("No matching files found.")
            return

        newest_file = max([os.path.join(directory, f) for f in files], key=os.path.getmtime)
        print(f"Opening newest file: {newest_file}")
        self.data = self.load_data(newest_file)
        self.data_filtered = self.filter_data(self.data)

        if not self.data_filtered.empty:
            self.setup_sliders()
            self.plot_time_domain(self.data_filtered)
            self.plot_frequency_domain(self.data_filtered, self.start_time_slider.value(),
                                       self.end_time_slider.value(), self.tolerance_slider.value(), self.padding_factor)
        else:
            print("No data available after filtering.")

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

    def load_data(self, file_path):
        try:
            data = pd.read_csv(file_path)

            # Check if the time data is monotonic
            if not data['Time [microseconds]'].is_monotonic_increasing:
                print("Warning: Time data is not monotonic. Sorting the data might be affecting the interpretation.")

            data = data.sort_values(by='Time [microseconds]')

            # Update accelerometer ID combo box
            if 'Accelerometer ID' in data.columns:
                unique_ids = sorted(data['Accelerometer ID'].unique())
                self.accel_id_selection.clear()
                self.accel_id_selection.addItems([str(id) for id in unique_ids])

            return data

        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()

    def plot_time_domain(self, data):
        # Extract time and acceleration data
        time = data['Time [microseconds]'].to_numpy() / 1e6  # Convert to seconds
        selected_axis = self.axis_selection.currentText()  # Selected axis (e.g., X, Y, Z)
        selected_accel = self.accel_id_selection.currentText()  # Selected accelerometer ID
        accel_data = 9.8124*data[selected_axis].to_numpy()  # Get selected axis data

        # Create the PlotDataItem if it doesn't already exist
        if not hasattr(self, 'time_plot_data_item'):
            pen = pg.mkPen(color='#2541B2', width=1)
            self.time_plot_data_item = self.plot_widget_time.plot(pen=pen, name=selected_axis)

        # Update the PlotDataItem's data
        self.time_plot_data_item.setData(time, accel_data)

        # Update plot labels and title
        self.plot_widget_time.setLabel('left', 'Acceleration (m/s²)')
        self.plot_widget_time.setLabel('bottom', 'Time (s)')
        self.plot_widget_time.setTitle(f"Accelerometer {selected_accel}: {selected_axis} (Time Domain)")


    def filter_data(self, data):
        if data.empty:
            return data

        # Filter by selected accelerometer ID first
        selected_id = self.accel_id_selection.currentText()
        if selected_id and 'Accelerometer ID' in data.columns:
            newdata = data[data['Accelerometer ID'].astype(str) == selected_id]
        else:
            # If no accelerometer ID is selected or the column is missing, return the data unfiltered
            newdata = data

        # Check if newdata is empty after accelerometer ID filtering
        if newdata.empty:
            print("No data found for the selected Accelerometer ID.")
            return newdata  # Return the empty dataframe

        # Calculate percentiles for each column
        percentiles = {
            'time': newdata['Time [microseconds]'].quantile([0.005, 0.995]),
            'x_accel': newdata['X Acceleration'].quantile([0.005, 0.995]),
            'y_accel': newdata['Y Acceleration'].quantile([0.005, 0.995]),
            'z_accel': newdata['Z Acceleration'].quantile([0.005, 0.995]),
        }

        # Apply filtering conditions based on the calculated percentiles
        data_filtered = newdata[
            (newdata['Time [microseconds]'] >= percentiles['time'].iloc[0]) &
            (newdata['Time [microseconds]'] <= percentiles['time'].iloc[1]) &
            (newdata['X Acceleration'] >= percentiles['x_accel'].iloc[0]) &
            (newdata['X Acceleration'] <= percentiles['x_accel'].iloc[1]) &
            (newdata['Y Acceleration'] >= percentiles['y_accel'].iloc[0]) &
            (newdata['Y Acceleration'] <= percentiles['y_accel'].iloc[1]) &
            (newdata['Z Acceleration'] >= percentiles['z_accel'].iloc[0]) &
            (newdata['Z Acceleration'] <= percentiles['z_accel'].iloc[1])
            ]

        return data_filtered

    def setup_sliders(self):
        # Setup the sliders based on the filtered data.
        # This ugly fix is necessary to prevent slider values over extending thier limits.

        if self.data_filtered.empty:
            return  # Do not set up sliders if there's no data

        time_values = (self.data_filtered['Time [microseconds]'].to_numpy())/100000
        min_time = (int(time_values[0]))
        max_time = (int(time_values[-1]))

        # Set the range based on actual time values
        self.start_time_slider.setRange(min_time, max_time)
        self.end_time_slider.setRange(min_time, max_time)

        # Set default values
        self.start_time_slider.setValue(min_time)
        self.end_time_slider.setValue(max_time)

        # Update labels with initial values
        self.update_labels()

    def update_labels(self):
        # Update the labels to show actual time values and tolerance.
        start_time = (self.start_time_slider.value() )*100000 # Get actual time values from sliders
        end_time = (self.end_time_slider.value() )*100000
        tolerance_value = self.tolerance_slider.value()

        # Update the labels with the actual time values
        self.start_time_label.setText(f"Start Time: {start_time} µs")
        self.end_time_label.setText(f"End Time: {end_time} µs")
        self.tolerance_label.setText(f"Tolerance: {tolerance_value} dB")

    def update_plot(self):
        # Update the plots based on the current slider values.
        if self.data.empty:
            print("No data to plot.")
            return

        # Refilter the data based on current accelerometer ID
        self.data_filtered = self.filter_data(self.data)

        if self.data_filtered.empty:
            print("No data available for selected accelerometer ID.")
            return

        # Get current time values from sliders
        start_time = (self.start_time_slider.value())*100000
        end_time = (self.end_time_slider.value())*100000

        # Update labels to reflect current slider values
        self.update_labels()

        # Filter data based on time range
        time_filtered_data = self.data_filtered[
            (self.data_filtered['Time [microseconds]'] >= start_time) &
            (self.data_filtered['Time [microseconds]'] <= end_time)
            ]

        if time_filtered_data.empty:
            print("No data in selected time range.")
            return

        self.plot_time_domain(time_filtered_data)

        default_tolerance = self.tolerance_slider.value()
        self.plot_frequency_domain(time_filtered_data, start_time, end_time, default_tolerance, self.padding_factor)

    def export_data(self):
        # Export trimmed data, frequency and magnitude data, and natural frequencies to CSV files if available.
        if self.data_filtered.empty:
            print("No data to export.")
            return

        # Get the current slider time range
        start_time = self.start_time_slider.value()
        end_time = self.end_time_slider.value()

        # Print out the time range for debugging
        print(f"Start time: {start_time*100000}, End time: {end_time*100000}")

        # Filter the data within the selected time range
        trimmed_data = self.data_filtered[
            (self.data_filtered['Time [microseconds]'] >= start_time*100000) &
            (self.data_filtered['Time [microseconds]'] <= end_time*100000)
            ]

        # If the trimmed data is empty, print a message and exit
        if trimmed_data.empty:
            print("No data found within the selected time range.")
            return

        # Show file dialog to select where to save the CSV files
        file_dialog = QFileDialog()
        file_base_path, _ = file_dialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")

        if file_base_path:
            # Export trimmed time-range data
            trimmed_data_path = f"{file_base_path}_trimmed_data.csv"
            trimmed_data.to_csv(trimmed_data_path, index=False)
            print(f"Trimmed acceleration data exported to {trimmed_data_path}.")

            # Export frequency and magnitude data
            if hasattr(self, 'positive_freqs') and hasattr(self, 'positive_magnitudes_dB'):
                # Ensure both frequency and magnitude arrays are of the same length
                if len(self.positive_freqs) == len(self.positive_magnitudes_dB):
                    freq_magnitude_data = pd.DataFrame({
                        "Frequency (Hz)": self.positive_freqs,
                        "Magnitude (dB)": self.positive_magnitudes_dB
                    })
                    freq_magnitude_path = f"{file_base_path}_frequency_magnitude.csv"
                    freq_magnitude_data.to_csv(freq_magnitude_path, index=False)
                    print(f"Frequency and magnitude data exported to {freq_magnitude_path}.")
                else:
                    print("Warning: Frequency and magnitude data arrays have mismatched lengths.")
            else:
                print("Frequency and magnitude data are not available for export.")

            # Export only selected natural frequencies if available
            if hasattr(self, 'natural_frequencies') and self.natural_frequencies.size > 0:
                # Get the selected natural frequencies from the QListWidget
                selected_items = self.freq_list_widget.selectedItems()
                selected_freqs = [float(item.text().split()[0]) for item in selected_items]

                if selected_freqs:
                    # Filter the natural frequencies and corresponding magnitudes based on selected frequencies
                    selected_indices = [np.abs(self.natural_frequencies - freq).argmin() for freq in selected_freqs]
                    selected_magnitudes = self.peak_magnitudes[selected_indices]
                    selected_natural_freqs = self.natural_frequencies[selected_indices]

                    # Ensure both arrays have matching lengths
                    if len(selected_natural_freqs) == len(selected_magnitudes):
                        natural_freq_data = pd.DataFrame({
                            "Natural Frequency (Hz)": selected_natural_freqs,
                            "Magnitude (dB)": selected_magnitudes
                        })
                        natural_freq_path = f"{file_base_path}_selected_natural_frequencies.csv"
                        natural_freq_data.to_csv(natural_freq_path, index=False)
                        print(f"Selected natural frequencies exported to {natural_freq_path}.")
                    else:
                        print("Warning: Mismatched lengths between selected frequencies and magnitudes.")
                else:
                    print("No natural frequencies selected for export.")
            else:
                print("Natural frequency data is not available for export.")

    def open_csv(self):
        # Open a file dialog to select and load a CSV file.
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")

        if file_path:
            self.data = self.load_data(file_path)
            self.data_filtered = self.filter_data(self.data)

            if not self.data_filtered.empty:
                self.setup_sliders()
                self.plot_time_domain(self.data_filtered)

                default_tolerance = self.tolerance_slider.value()
                self.plot_frequency_domain(self.data_filtered,
                                           self.start_time_slider.value(),
                                           self.end_time_slider.value(),
                                           default_tolerance)
            else:
                print("No data available after filtering.")