import csv
import os
import re
import sys
from datetime import datetime  # Add this import statement

import numpy as np
import pandas as pd
import pyqtgraph as pg

from scipy.signal import find_peaks

from PySide6.QtCore import QIODevice, Qt, QTimer, QThread, Signal
from PySide6.QtSerialPort import QSerialPort
from PySide6.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, \
    QFileDialog, QComboBox, QHBoxLayout, QTabWidget, QLabel, QScrollArea, QCheckBox, \
    QSlider

from pglive.sources.data_connector import DataConnector
from pglive.sources.live_axis_range import LiveAxisRange
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

class SerialReader(QThread):
    # Define a generic data_received signal with sensor_id
    data_received = Signal(str, float, float, float, float)

    def __init__(self, port_name="/dev/ttyACM0", baud_rate=1000000):
        super().__init__()
        self.serial = QSerialPort()
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud_rate)
        self.serial.readyRead.connect(self.read_data)

    def set_port(self, port_name):
        # If the serial port is open, close it first
        if self.serial.isOpen():
            self.serial.close()
        # Set the new port name
        self.serial.setPortName(port_name)
        print(f"Port set to {port_name}")
        # Try to open the serial port with the new settings
        self.start_serial()

    def set_speed(self, speed = "400"):
        if self.serial.write((str(speed) + '\n').encode()) & self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
            print(f"Successfully changed speed to {speed}.")
        else:
            print(f"Failed to set speed to {speed}.")

    def start_serial(self):
        if not self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
            print(f"Failed to open port {self.serial.portName()}")
        else:
            print(f"Connected to {self.serial.portName()}!")

    def read_data(self):
        while self.serial.canReadLine():
            line = self.serial.readLine().data().decode().strip()
            parts = line.split()
            #print(parts)  # Debugging: Print incoming data

            if len(parts) == 5:
                sensor_id, timeus, accel_x, accel_y, accel_z = parts
                try:
                    timeus = float(timeus)
                    accel_x = float(accel_x)
                    accel_y = float(accel_y)
                    accel_z = float(accel_z)
                    # Emit data with sensor_id
                    self.data_received.emit(sensor_id, timeus, accel_x, accel_y, accel_z)
                except ValueError:
                    print("Error parsing data.")

    def stop_serial(self):
        if self.serial.isOpen():
            self.serial.close()

class DataRecorder:
    def __init__(self):
        super().__init__()
        self.data_records = []  # Store all recorded data
        self.recording = False   # State to check if recording is active

    def start_recording(self):
        self.recording = True
        self.data_records.clear()  # Clear previous data
        print("Recording started...")  # Debugging line

    def stop_recording(self):
        self.recording = False
        print("Recording stopped.")  # Debugging line

    def record_data(self, timeus, sensor_id, accel_x, accel_y, accel_z):
        if self.recording:
            # Append the new data to the records
            self.data_records.append([int(timeus), sensor_id, accel_x, accel_y, accel_z])

    def export_data(self):
        if len(self.data_records) > 0:
            filename, _ = QFileDialog.getSaveFileName(
                None, "Export Data", "", "CSV Files (*.csv)")
            if filename:
                try:
                    with open(filename, "w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration", "Z Acceleration"])
                        writer.writerows(self.data_records)
                    QMessageBox.information(None, "Export Success", "Data exported successfully.")
                except Exception:
                    QMessageBox.warning(None, "Export Error", "Failed to export data.")
            else:
                QMessageBox.warning(None, "Export Error", "Invalid filename.")
        else:
            QMessageBox.warning(None, "Export Error", "No data to export.")

    def export_default(self):
        # Create the directory if it does not exist
        directory = os.path.expanduser("Cached_Samples/")  # Use expanduser to handle home directory
        os.makedirs(directory, exist_ok=True)  # Create the directory if it doesn't exist

        if len(self.data_records) > 0:
            # Generate a default filename based on the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(directory, f"samples_{timestamp}.csv")
            self.last_saved_file = filename

            try:
                with open(filename, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration",
                                     "Z Acceleration"])
                    writer.writerows(self.data_records)
            except Exception:
                QMessageBox.warning(None, "Export Error", "Failed to export data.")
        else:
            QMessageBox.warning(None, "Export Error", "No data to export.")

class Settings(QWidget):
    def __init__(self, plot_fft_instance):
        super().__init__()
        self.plot_fft = plot_fft_instance  # Reference to PlotFFT instance
        self.init_ui()

    def init_ui(self):
        # Main layout for the settings widget
        main_layout = QHBoxLayout()

        # Left side for padding factor controls
        left_layout = QVBoxLayout()

        # Label for the Padding Slider
        self.padding_label = QLabel("PF=1")
        self.padding_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.padding_label)

        # Slider for Padding Factor (1 to 10) - Vertical Slider
        self.padding_slider = QSlider(Qt.Orientation.Vertical)
        self.padding_slider.setMinimum(1)
        self.padding_slider.setMaximum(10)
        self.padding_slider.setValue(1)  # Default value
        self.padding_slider.valueChanged.connect(self.update_padding)
        left_layout.addWidget(self.padding_slider)

        # Right side for stylesheet selection
        right_layout = QVBoxLayout()

        # Label for the Stylesheet Dropdown
        label = QLabel("Select Stylesheet:")
        label.setAlignment(Qt.AlignBottom)
        right_layout.addWidget(label)

        # Dropdown (ComboBox) for selecting stylesheet
        self.stylesheet_dropdown = QComboBox()
        self.stylesheet_dropdown.addItems(["Default", "Dark Mode", "Light Mode"])
        self.stylesheet_dropdown.currentIndexChanged.connect(self.change_stylesheet)
        right_layout.addWidget(self.stylesheet_dropdown)

        # Add both left and right layouts to the main layout
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)

        # Set the layout for the widget
        self.setLayout(main_layout)

    def update_padding(self):
        padding_factor = self.padding_slider.value()
        self.padding_label.setText(f"PF={padding_factor}")
        self.plot_fft.update_padding_factor(padding_factor)

    def change_stylesheet(self):
        selected_style = self.stylesheet_dropdown.currentText()
        if selected_style == "Default":
            load_stylesheet(QApplication.instance(), "style_blank")  # Directly calling the function
        elif selected_style == "Dark Mode":
            load_stylesheet(QApplication.instance(), "style_dark")  # Directly calling the function
        elif selected_style == "Light Mode":
            load_stylesheet(QApplication.instance(), "style_light")

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
        layout = QVBoxLayout()

        # Create the toggle button for PSD/FFT
        self.toggle_button = QPushButton("Show PSD")
        self.toggle_button.clicked.connect(self.toggle_plot)

        # Create a container widget
        container_widget = QWidget()
        container_widget.setObjectName("graphy")  # Set object name
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)  # Margin to space the PlotWidget from the edges

        # Create two PlotWidgets: one for time domain and one for frequency domain
        self.plot_widget_time = pg.PlotWidget()  # Time domain plot
        self.plot_widget_time.setBackground("#2b2b2b")
        self.plot_widget_fft = pg.PlotWidget()  # Frequency domain plot
        self.plot_widget_fft.setBackground("#2b2b2b")

        container_layout.addWidget(self.plot_widget_time)
        container_layout.addWidget(self.plot_widget_fft)

        # Create sliders for setting the FFT time interval and tolerance
        self.start_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)

        # Set ranges for sliders based on data length and tolerance
        self.start_time_slider.setRange(0, 100)
        self.end_time_slider.setRange(0, 100)
        self.tolerance_slider.setRange(10, 10000)  # Example range for tolerance

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
        self.tolerance_label = QLabel("Tolerance: 10 dB")

        # Create the export button
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_data)

        # Create the open CSV button
        self.open_button = QPushButton("Open CSV")
        self.open_button.clicked.connect(self.open_csv)

        # Create the open CSV button
        self.open_recent = QPushButton("Open Latest Sample")
        self.open_recent.clicked.connect(self.open_last_sample)

        # Add widgets to the layout
        layout.addWidget(container_widget)
        layout.addWidget(QLabel("Accelerometer ID:"))  # Add label for accelerometer selection
        layout.addWidget(self.accel_id_selection)  # Add the accelerometer ID selection
        layout.addWidget(self.axis_selection)  # Add the axis selection combo box to the layout
        layout.addWidget(self.start_time_label)
        layout.addWidget(self.start_time_slider)
        layout.addWidget(self.end_time_label)
        layout.addWidget(self.end_time_slider)
        layout.addWidget(self.tolerance_label)
        layout.addWidget(self.tolerance_slider)
        layout.addWidget(self.export_button)  # Add the export button to the layout
        layout.addWidget(self.open_button)  # Add the open CSV button to the layout
        layout.addWidget(self.open_recent)  # Add the open CSV button to the layout
        layout.addWidget(self.toggle_button)  # Add the toggle button to the layout

        # Set the layout to the main widget
        self.setLayout(layout)

        # Load, filter, and plot the data
        self.data = pd.DataFrame()  # Empty DataFrame initially
        self.data_filtered = pd.DataFrame()

        self.positive_freqs = np.array([])  # Placeholder for frequency data
        self.positive_magnitudes_dB = np.array([])  # Placeholder for magnitudes

        self.plot_mode = "FFT"  # Default mode

    def plot_frequency_domain(self, data, start_time, end_time, tolerance, padding_factor):
        # Extract data and compute FFT
        selected_axis = self.axis_selection.currentText()
        selected_accel = self.accel_id_selection.currentText()
        accel_data = data[selected_axis].to_numpy()
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

        # Zero-padding: Calculate the padded length based on the padding factor
        padded_length = int(N * self.padding_factor)
        accel_data_padded = np.pad(accel_data, (0, padded_length - N), mode='constant')

        # Compute FFT with zero-padded data
        freq = np.fft.fftfreq(padded_length, d=dt)
        fft_accel = np.fft.fft(accel_data_padded)
        psd = (np.abs(fft_accel) ** 2) / (padded_length * dt)
        psd_dB = 10 * np.log10(psd[:padded_length // 2])
        magnitudes = np.abs(fft_accel)[:padded_length // 2]

        self.positive_freqs = freq[:padded_length // 2]
        self.positive_magnitudes_dB = psd_dB if self.plot_mode == "PSD" else magnitudes

        peaks, _ = find_peaks(self.positive_magnitudes_dB, height=tolerance)
        self.natural_frequencies = self.positive_freqs[peaks]
        peak_magnitudes = self.positive_magnitudes_dB[peaks]

        # Plot data
        if not hasattr(self, 'fft_plot_data_item'):
            fft_pen = pg.mkPen(color='#F7F5FB', width=1)
            self.fft_plot_data_item = self.plot_widget_fft.plot(pen=fft_pen)

        self.fft_plot_data_item.setData(self.positive_freqs, self.positive_magnitudes_dB)

        # Plot peaks
        if not hasattr(self, 'fft_peak_item'):
            symbol_pen = pg.mkPen('#D8973C')
            symbol_brush = pg.mkBrush('#D8973C')
            self.fft_peak_item = self.plot_widget_fft.plot(pen=None, symbol='o', symbolPen=symbol_pen,
                                                           symbolBrush=symbol_brush)

        self.fft_peak_item.setData(self.natural_frequencies, peak_magnitudes)

        # Update plot labels and title
        self.plot_widget_fft.setLabel('left', 'PSD (dB/Hz)' if self.plot_mode == "PSD" else 'Magnitude')
        self.plot_widget_fft.setLabel('bottom', 'Frequency (Hz)')
        mode_title = "PSD" if self.plot_mode == "PSD" else "FFT"
        self.plot_widget_fft.setTitle(
            f"Accelerometer {selected_accel}: {selected_axis} {mode_title} (Frequency Domain)")

    def update_padding_factor(self, padding_factor):
        """ Update the padding factor when changed in settings """
        self.padding_factor = padding_factor
        print(f"Padding Factor updated to: {self.padding_factor}")
        self.update_plot()

    def open_last_sample(self):
        directory, pattern = "Cached_Samples/", r"samples_\d{8}_\d{6}\.csv"
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
        accel_data = data[selected_axis].to_numpy()  # Get selected axis data

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

        # Filter the data within the selected time range
        trimmed_data = self.data_filtered[
            (self.data_filtered['Time [microseconds]'] >= start_time) &
            (self.data_filtered['Time [microseconds]'] <= end_time)
            ]

        file_dialog = QFileDialog()
        file_base_path, _ = file_dialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")

        if file_base_path:
            # Export trimmed time-range data
            trimmed_data_path = f"{file_base_path}_trimmed_data.csv"
            trimmed_data.to_csv(trimmed_data_path, index=False)
            print(f"Trimmed acceleration data exported to {trimmed_data_path}.")

            # Export frequency and magnitude data
            if hasattr(self, 'positive_freqs') and hasattr(self, 'positive_magnitudes_dB'):
                freq_magnitude_data = pd.DataFrame({
                    "Frequency (Hz)": self.positive_freqs,
                    "Magnitude": self.positive_magnitudes_dB
                })
                freq_magnitude_path = f"{file_base_path}_frequency_magnitude.csv"
                freq_magnitude_data.to_csv(freq_magnitude_path, index=False)
                print(f"Frequency and magnitude data exported to {freq_magnitude_path}.")
            else:
                print("Frequency and magnitude data are not available for export.")

            # Export natural frequencies
            if hasattr(self, 'natural_frequencies') and self.natural_frequencies.size > 0:
                natural_freq_data = pd.DataFrame({"Natural Frequency (Hz)": self.natural_frequencies})
                natural_freq_path = f"{file_base_path}_natural_frequencies.csv"
                natural_freq_data.to_csv(natural_freq_path, index=False)
                print(f"Natural frequencies exported to {natural_freq_path}.")
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

class SerialPlotterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real-Time Accelerometer Viewer")
        self.setGeometry(100, 100, 600, 600)

        self.tab_widget = QTabWidget()
        self.plot_tab = QWidget()
        self.plot_layout = QGridLayout()
        self.data_connectors = {}

        # Initialize SerialReader
        self.serial_reader = SerialReader()
        self.serial_reader.data_received.connect(self.update_data_buffers)
        self.serial_reader.start_serial()  # Start reading from the default port

        # Options Menu
        self.setup_options_menu()

        # Setup the plotting tab's layout and add to tab widget
        self.plot_tab.setLayout(self.plot_layout)
        self.tab_widget.addTab(self.plot_tab, "Plot Data")

        # Add SensorPlot tab
        self.plot_fft = PlotFFT()  # Assuming PlotFFT is defined elsewhere
        self.tab_widget.addTab(self.plot_fft, "Sensor Data Plot")

        # Add SensorPlot tab
        self.settings = Settings(self.plot_fft)  # Assuming PlotFFT is defined elsewhere
        self.tab_widget.addTab(self.settings, "Settings")

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

        # Initialize sensor data storage
        self.init_sensor_data()

    def setup_options_menu(self):
        self.serial_ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1", "COM0", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"]
        self.current_port_index = 0  # Default to the second port in the list

        self.communication_speeds = [400, 500, 600, 1000, 2000, 4000, 8000, 10000, 100000]
        self.selected_speed_index = 0

        self.data_recorder = DataRecorder()  # Create an instance of DataRecorder

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(230, 250)
        scroll_area.setMaximumWidth(210)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_widget.setObjectName("scroll")
        content_layout = QGridLayout(content_widget)

        # Set vertical and horizontal spacing between items
        content_layout.setVerticalSpacing(15)
        content_layout.setHorizontalSpacing(10)

        # Set margins around the layout
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Options title centered at the top
        options_label = QLabel("Options")
        options_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_label.setStyleSheet("font-size: 14pt;")
        content_layout.addWidget(options_label, 0, 0, 1, 2)  # Spans across two columns

        # Checkbox for enabling/disabling plotting
        self.plot_enabled_checkbox = QCheckBox("Enable Plotting")
        self.plot_enabled_checkbox.setChecked(True)
        self.plot_enabled_checkbox.stateChanged.connect(self.toggle_plotting)
        self.plot_enabled_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        content_layout.addWidget(self.plot_enabled_checkbox, 1, 0, 1, 2)

        # Communication speed combo
        communication_speed_label = QLabel("Speed:")
        communication_speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(communication_speed_label, 2, 0)
        self.communication_speed_combo = QComboBox()
        self.communication_speed_combo.addItems([str(size) for size in self.communication_speeds])
        self.communication_speed_combo.setCurrentIndex(self.selected_speed_index)
        self.communication_speed_combo.currentIndexChanged.connect(self.speed_button)
        content_layout.addWidget(self.communication_speed_combo, 2, 1)

        # Serial port combo
        serial_port_label = QLabel("COM Port:")
        serial_port_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(serial_port_label, 4, 0)
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.addItems(self.serial_ports)
        self.serial_port_combo.setCurrentIndex(self.current_port_index)
        self.serial_port_combo.currentIndexChanged.connect(self.change_serial_port)
        content_layout.addWidget(self.serial_port_combo, 4, 1)

        # Max Points Selection ComboBox
        max_points_label = QLabel("Max Points:")
        max_points_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(max_points_label, 5, 0)  # Adjust row index as needed

        self.max_points_combo = QComboBox()
        # Populate the dropdown with potential max point sizes (e.g., 100, 200, 400, 600, 800)
        self.max_points_combo.addItems([str(size) for size in [100, 200, 400, 600, 800]])
        self.max_points_combo.setCurrentIndex(3)  # Default to 600 if it's the initial size
        self.max_points_combo.currentIndexChanged.connect(self.update_plot_settings)
        content_layout.addWidget(self.max_points_combo, 5, 1)  # Adjust row index as needed

        # Communication speed combo
        update_speed_label = QLabel("Update Speed:")
        update_speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(update_speed_label, 6, 0)

        self.update_speed_combo = QComboBox()
        self.update_speed_combo.addItems([str(i) for i in [10, 20, 30, 40, 50, 60,120,240,480,960]])  # Example FPS options
        self.update_speed_combo.setCurrentIndex(2)  # Default to 30 FPS (index 2)
        self.update_speed_combo.currentIndexChanged.connect(self.update_plot_settings)
        content_layout.addWidget(self.update_speed_combo, 6, 1)

        # Start Recording button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #2C6E49; color: white;")
        content_layout.addWidget(self.record_button, 7, 0, 1, 2)

        # Export Data button
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        content_layout.addWidget(self.export_button, 8, 0, 1, 2)

        # Finalize the scroll area
        scroll_area.setWidget(content_widget)
        self.plot_layout.addWidget(scroll_area, 0, 3, 3, 1)

    def init_sensor_data(self):
        # Initialize data connectors for multiple sensors
        self.sensor_count = 3  # Adjust based on the number of sensors you expect
        for sensor_id in range(1, self.sensor_count + 1):
            self.add_sensor_plot(sensor_id,sensor_id-1)

    def add_sensor_plot(self, sensor_id, row, max_points=600,update_rate=30):
        container_widget = QWidget()
        container_widget.setObjectName("graphy")  # Set object name
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)  # Margin to space the PlotWidget from the edges

        sensor_plot_widget = LivePlotWidget(title=f'Sensor ID: {sensor_id}',
                                            x_range_controller=LiveAxisRange(),
                                            y_range_controller=LiveAxisRange())
        sensor_plot_widget.setBackground("#2b2b2b")

        colors = ["red", "orange", "cyan"]  # Colors for X, Y, Z respectively

        for i, axis in enumerate(['X', 'Y', 'Z']):
            plot = LiveLinePlot(pen=colors[i])
            sensor_plot_widget.addItem(plot)
            connector = DataConnector(plot, max_points=max_points, update_rate=update_rate)
            self.data_connectors[(sensor_id, axis)] = connector

        # Add the PlotWidget to the container's layout
        container_layout.addWidget(sensor_plot_widget)

        # Add the container to the main layout
        self.plot_layout.addWidget(container_widget, row, 0)

    def update_plot_settings(self):
        # Get the selected max points value from the max points dropdown
        selected_max_points = int(self.max_points_combo.currentText())

        # Get the selected update speed (in FPS) from the update speed dropdown
        selected_update_rate = int(self.update_speed_combo.currentText())

        # Remove existing sensor plots and their connectors
        for sensor_id in list(self.data_connectors.keys()):
            # Remove the sensor's plot (if needed)
            self.remove_sensor_plot(sensor_id)

        # Re-add all sensor plots with the new max_points and update_rate values
        for sensor_id in range(1, self.sensor_count + 1):
            self.add_sensor_plot(sensor_id, sensor_id - 1, max_points=selected_max_points, update_rate=selected_update_rate)

    def remove_sensor_plot(self, sensor_id):
        # Helper method to remove a plot and its connector
        # Iterate over all children in the layout and find the container for this sensor
        for widget in self.plot_layout.findChildren(QWidget):
            if widget.findChild(LivePlotWidget):
                plot_widget = widget.findChild(LivePlotWidget)
                if plot_widget.title() == f'Sensor ID: {sensor_id}':
                    # Remove the widget from the layout and clean up the data connector
                    self.plot_layout.removeWidget(widget)
                    widget.deleteLater()
                    # Remove the corresponding data connectors
                    for axis in ['X', 'Y', 'Z']:
                        self.data_connectors[(sensor_id, axis)] = None
                    return  # Stop once the correct plot is found and removed

    def speed_button(self):
        selected_speed = int(self.communication_speed_combo.currentText())
        print(f"Attempting to set speed to {selected_speed}...")
        self.serial_reader.set_speed(selected_speed)

    def change_serial_port(self):
        selected_port = self.serial_port_combo.currentText()
        print(f"Attempting to change port to {selected_port}...")
        self.serial_reader.set_port(selected_port)

    def update_data_buffers(self, sensor_id, timeus, accel_x, accel_y, accel_z):
        sensor_id = int(sensor_id)  # Convert sensor_id to int
        self.data_recorder.record_data(timeus, sensor_id, accel_x, accel_y, accel_z)  # Record the data

        # Append data to the corresponding live plot connectors
        self.data_connectors[(sensor_id, 'X')].cb_append_data_point(accel_x, x=timeus)
        self.data_connectors[(sensor_id, 'Y')].cb_append_data_point(accel_y, x=timeus)
        self.data_connectors[(sensor_id, 'Z')].cb_append_data_point(accel_z, x=timeus)

    def toggle_plotting(self, state):
        if state == 0:  # 0 means unchecked
            print("Stopping plot updates...")  # Debugging line
            for connector in self.data_connectors.values():
                connector.clear()  # Clear the data if needed
                connector.pause()
        elif state == 2:  # 2 means checked
            print("Starting plot updates...")  # Debugging line
            for connector in self.data_connectors.values():
                connector.resume()

    def toggle_recording(self):
        if self.record_button.text() == "Start Recording":
            # Start recording
            self.data_recorder.start_recording()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: #A4243B; color: white;")
        else:
            # Stop recording
            self.data_recorder.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #2C6E49; color: white;")
            self.data_recorder.export_default()

    def export_data(self):
        self.data_recorder.export_data()

def load_stylesheet(app, style_name="style_dark"):
    # Map stylesheet names to file paths
    stylesheet_path = os.path.join(os.path.dirname(__file__), f"Preferences/{style_name}.qss")

    # Check if the file exists
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Error: Stylesheet file '{stylesheet_path}' not found.")
        app.setStyleSheet("")  # Reset to default if file is missing

def main():
    app = QApplication(sys.argv)
    try:
        load_stylesheet(app)
    except FileNotFoundError as e:
        print(f"Failed to load stylesheet: File not found. {e}")
    except Exception as e:
        print(f"An unexpected error occurred while loading the stylesheet: {e}")
    finally:
        try:
            main_window = SerialPlotterWindow()
            main_window.show()
            sys.exit(app.exec())
        except Exception as e:
            print(f"An unexpected error occurred while starting the application: {e}")

if __name__ == "__main__":
    main()