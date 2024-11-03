import csv
import os
import signal
import sys
import time
from datetime import datetime  # Add this import statement

import numpy as np
import pandas as pd
import pyqtgraph as pg

from scipy.signal import find_peaks

from PyQt6.QtCore import QIODevice, Qt,QTimer, QThread, pyqtSignal
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, \
    QFileDialog, QComboBox, QTextEdit, QTabWidget, QGraphicsDropShadowEffect, QLabel, QScrollArea, QCheckBox, \
    QSlider
from PyQt6.QtGui import QPalette, QColor

class SerialReader(QThread):
    # Define a generic data_received signal with sensor_id
    data_received = pyqtSignal(str, float, float, float, float)

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
        if self.serial.write((str(speed) + '\n').encode()) & self.serial.open(QIODevice.OpenModeFlag.ReadOnly):
            print(f"Successfully changed speed to {speed}.")
        else:
            print(f"Failed to set speed to {speed}.")

    def start_serial(self):
        if not self.serial.open(QIODevice.OpenModeFlag.ReadOnly):
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

class CircularBuffer:
    def __init__(self, capacity):
        """Initialize the circular buffer with a fixed capacity."""
        self.capacity = capacity
        self.buffer = []
        self.start = 0  # Points to the oldest element
        self.count = 0  # Number of elements in the buffer

    def append(self, item):
        """Append a new item to the buffer, overwriting the oldest data if full."""
        if self.count < self.capacity:
            # Buffer not full, simply append
            self.buffer.append(item)
            self.count += 1
        else:
            # Buffer full, overwrite the oldest element
            self.buffer[self.start] = item
            self.start = (self.start + 1) % self.capacity  # Move start pointer

    def get_all(self):
        """Retrieve all elements in the buffer in the correct order."""
        if self.count < self.capacity:
            return self.buffer[:]
        else:
            # Return items in the correct order from oldest to newest
            return self.buffer[self.start:] + self.buffer[:self.start]

    def get_latest(self):
        """Retrieve the latest items in the buffer."""
        return self.get_all()

    def is_full(self):
        """Check if the buffer is full."""
        return self.count == self.capacity

    def clear(self):
        """Reset the buffer to empty state."""
        self.buffer = []
        self.start = 0
        self.count = 0

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
            self.data_records.append([timeus, sensor_id, accel_x, accel_y, accel_z])

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

class PlotFFT(QWidget):
    def __init__(self):
        super().__init__()

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
        layout.addWidget(self.toggle_button)  # Add the toggle button to the layout

        # Set the layout to the main widget
        self.setLayout(layout)

        # Load, filter, and plot the data
        self.data = pd.DataFrame()  # Empty DataFrame initially
        self.data_filtered = pd.DataFrame()

        self.positive_freqs = np.array([])  # Placeholder for frequency data
        self.positive_magnitudes_dB = np.array([])  # Placeholder for magnitudes

        self.plot_mode = "FFT"  # Default mode

    def toggle_plot(self):
        """Toggle between PSD and FFT plotting."""
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
        time = data['Time [microseconds]'].to_numpy()
        selected_axis = self.axis_selection.currentText()  # Get the selected axis
        selected_accel = self.accel_id_selection.currentText()  # Get selected accelerometer ID
        accel_data = data[selected_axis].to_numpy()  # Select data based on the chosen axis

        self.plot_widget_time.clear()

        pen1 = pg.mkPen(color='#2541B2')
        pen2 = pg.mkPen(color='#1768AC')
        pen3 = pg.mkPen(color='#06BEE1')

        # Plot the selected acceleration axis
        self.plot_widget_time.plot(time, accel_data, pen=pen1, name=selected_axis)

        self.plot_widget_time.addLegend()
        self.plot_widget_time.setLabel('left', 'Acceleration (m/s²)')
        self.plot_widget_time.setLabel('bottom', 'Time (microseconds)')
        self.plot_widget_time.setTitle(f"Accelerometer {selected_accel}: {selected_axis} (Time Domain)")

    def filter_data(self, data):
        if data.empty:
            return data

        # Filter by selected accelerometer ID first
        selected_id = self.accel_id_selection.currentText()
        if selected_id and 'Accelerometer ID' in data.columns:
            data = data[data['Accelerometer ID'].astype(str) == selected_id]

        percentiles = {
            'time': data['Time [microseconds]'].quantile([0.005, 0.995]),
            'z_accel': data['X Acceleration'].quantile([0.005, 0.995]),
            'y_accel': data['Y Acceleration'].quantile([0.005, 0.995]),
            'z_accel': data['Z Acceleration'].quantile([0.005, 0.995]),
        }

        data_filtered = data[
            (data['Time [microseconds]'] >= percentiles['time'].iloc[0]) &
            (data['Time [microseconds]'] <= percentiles['time'].iloc[1]) &
            (data['X Acceleration'] >= percentiles['z_accel'].iloc[0]) &
            (data['X Acceleration'] <= percentiles['z_accel'].iloc[1]) &
            (data['Y Acceleration'] >= percentiles['y_accel'].iloc[0]) &
            (data['Y Acceleration'] <= percentiles['y_accel'].iloc[1]) &
            (data['Z Acceleration'] >= percentiles['z_accel'].iloc[0]) &
            (data['Z Acceleration'] <= percentiles['z_accel'].iloc[1])
            ]

        return data_filtered

    def setup_sliders(self):
        """Setup the sliders based on the filtered data."""
        if self.data_filtered.empty:
            return  # Do not set up sliders if there's no data

        time_values = self.data_filtered['Time [microseconds]'].to_numpy()
        min_time = int(time_values[0])
        max_time = int(time_values[-1])

        # Set the range based on actual time values
        self.start_time_slider.setRange(min_time, max_time)
        self.end_time_slider.setRange(min_time, max_time)

        # Set default values
        self.start_time_slider.setValue(min_time)
        self.end_time_slider.setValue(max_time)

        # Update labels with initial values
        self.update_labels()

    def update_labels(self):
        """Update the labels to show actual time values and tolerance."""
        start_time = self.start_time_slider.value()  # Get actual time values from sliders
        end_time = self.end_time_slider.value()
        tolerance_value = self.tolerance_slider.value()

        # Update the labels with the actual time values
        self.start_time_label.setText(f"Start Time: {start_time} µs")
        self.end_time_label.setText(f"End Time: {end_time} µs")
        self.tolerance_label.setText(f"Tolerance: {tolerance_value} dB")

    def update_plot(self):
        """Update the plots based on the current slider values."""
        if self.data.empty:
            print("No data to plot.")
            return

        # Refilter the data based on current accelerometer ID
        self.data_filtered = self.filter_data(self.data)

        if self.data_filtered.empty:
            print("No data available for selected accelerometer ID.")
            return

        # Get current time values from sliders
        start_time = self.start_time_slider.value()
        end_time = self.end_time_slider.value()

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
        self.plot_frequency_domain(time_filtered_data, start_time, end_time, default_tolerance)

    def plot_frequency_domain(self, data, start_time, end_time, tolerance):
        selected_axis = self.axis_selection.currentText()
        selected_accel = self.accel_id_selection.currentText()

        # Extract relevant data
        accel_data = data[selected_axis].to_numpy()
        time = data['Time [microseconds]'].to_numpy()

        N = len(accel_data)
        if N < 2:
            print("Not enough data points for FFT.")
            return

        dt = np.mean(np.diff(time)) * 1e-6  # Convert µs to seconds
        if dt <= 0:
            print("Invalid time difference; cannot compute FFT.")
            return

        # Perform FFT
        freq = np.fft.fftfreq(N, d=dt)
        fft_accel = np.fft.fft(accel_data)

        # PSD and FFT magnitudes
        psd = (np.abs(fft_accel) ** 2) / (N * dt)
        psd_dB = 10 * np.log10(psd[:N // 2])
        magnitudes = np.abs(fft_accel)[:N // 2]

        self.positive_freqs = freq[:N // 2]
        self.positive_magnitudes_dB = psd_dB if self.plot_mode == "PSD" else magnitudes

        # Find peaks in the selected mode
        peaks, _ = find_peaks(self.positive_magnitudes_dB, height=tolerance)
        self.natural_frequencies = self.positive_freqs[peaks]
        peak_magnitudes = self.positive_magnitudes_dB[peaks]

        # Plot
        self.plot_widget_fft.clear()

        fftPen = pg.mkPen(color='#F7F5FB')
        symbolPen = pg.mkPen('#D8973C')
        symbolBrush = pg.mkBrush('#D8973C')

        self.plot_widget_fft.plot(self.positive_freqs, self.positive_magnitudes_dB, pen=fftPen)

        # Add peak markers
        self.plot_widget_fft.plot(
            self.natural_frequencies, peak_magnitudes, pen=None, symbol='o', symbolPen=symbolPen, symbolBrush=symbolBrush
        )
        self.plot_widget_fft.setLabel('left', 'PSD (dB/Hz)' if self.plot_mode == "PSD" else 'Magnitude')
        self.plot_widget_fft.setLabel('bottom', 'Frequency (Hz)')

        # Set title based on the selected mode
        mode_title = "PSD" if self.plot_mode == "PSD" else "FFT"
        self.plot_widget_fft.setTitle(
            f"Accelerometer {selected_accel}: {selected_axis} {mode_title} (Frequency Domain)")

    def export_data(self):
        """Export trimmed data, frequency and magnitude data, and natural frequencies to CSV files if available."""
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
        """Open a file dialog to select and load a CSV file."""
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
        self.data_buffers = {}
        self.plot_data_items = {}

        # Initialize SerialReader
        self.serial_reader = SerialReader()
        self.serial_reader.data_received.connect(self.update_data_buffers)
        self.serial_reader.start_serial()  # Start reading from the default port

        # Create a QTimer for controlled plot updates
        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(1)  # Refresh approximately every 30ms
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start()

        # Options Menu
        self.setup_options_menu()

        # Setup the plotting tab's layout and add to tab widget
        self.plot_tab.setLayout(self.plot_layout)
        self.tab_widget.addTab(self.plot_tab, "Plot Data")

        # Add SensorPlot tab
        self.plot_fft = PlotFFT()
        self.tab_widget.addTab(self.plot_fft, "Sensor Data Plot")

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

        # Initialize sensor data storage
        self.init_sensor_data()

    def setup_options_menu(self):
        self.serial_ports = ["/dev/ttyACM0","/dev/ttyACM1","/dev/ttyUSB0", "/dev/ttyUSB1", "COM0", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"]
        self.current_port_index = 0  # Default to the second port in the list

        self.communication_speeds = [400, 500, 600, 1000, 2000, 4000, 8000, 10000,100000]
        self.selected_speed_index = 0

        self.buffer_sizes = [1000, 3000, 5000, 7000, 10000, 17500, 30000]
        self.buffer_capacity = self.buffer_sizes[0]

        self.data_recorder = DataRecorder()  # Create an instance of DataRecorder

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(210, 250)
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

        # Buffer size combo
        buffer_size_label = QLabel("Buffer Size:")
        buffer_size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(buffer_size_label, 3, 0)
        buffer_size_combo = QComboBox()
        buffer_size_combo.addItems([str(size) for size in self.buffer_sizes])
        buffer_size_combo.setCurrentIndex(0)
        buffer_size_combo.currentIndexChanged.connect(self.change_buffer_size)
        content_layout.addWidget(buffer_size_combo, 3, 1)

        # Serial port combo
        serial_port_label = QLabel("COM Port:")
        serial_port_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(serial_port_label, 4, 0)
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.addItems(self.serial_ports)
        self.serial_port_combo.setCurrentIndex(self.current_port_index)
        self.serial_port_combo.currentIndexChanged.connect(self.change_serial_port)
        content_layout.addWidget(self.serial_port_combo, 4, 1)

        # Start Recording button
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet("background-color: #2C6E49; color: white;")
        content_layout.addWidget(self.record_button, 5, 0, 1, 2)

        # Export Data button
        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        content_layout.addWidget(self.export_button, 6, 0, 1, 2)

        # Finalize the scroll area
        scroll_area.setWidget(content_widget)
        self.plot_layout.addWidget(scroll_area, 0, 3, 3, 1)

    def init_sensor_data(self):
        # Initialize data buffers and plot items for multiple sensors
        self.sensor_count = 3  # Adjust based on the number of sensors you expect
        self.data_buffers = {1: {'x': CircularBuffer(self.buffer_capacity),
                                  'y': CircularBuffer(self.buffer_capacity),
                                  'z': CircularBuffer(self.buffer_capacity)},
                             2: {'x': CircularBuffer(self.buffer_capacity),
                                  'y': CircularBuffer(self.buffer_capacity),
                                  'z': CircularBuffer(self.buffer_capacity)},
                             3: {'x': CircularBuffer(self.buffer_capacity),
                                 'y': CircularBuffer(self.buffer_capacity),
                                 'z': CircularBuffer(self.buffer_capacity)}}

        # Create a single plot widget for each sensor
        for sensor_id in self.data_buffers.keys():
            self.plot_data_items[sensor_id] = self.add_graph(f"Sensor {sensor_id}", "Time (samples)", "Acceleration", sensor_id - 1)

    def speed_button(self):
        selected_speed = int(self.communication_speed_combo.currentText())
        print(f"Attempting to set speed to {selected_speed}...")
        self.serial_reader.set_speed(selected_speed)

    def change_serial_port(self):
        selected_port = self.serial_port_combo.currentText()
        print(f"Attempting to change port to {selected_port}...")
        self.serial_reader.set_port(selected_port)

    def add_graph(self, name, x_label, y_label, row):
        # Outer widget to hold the PlotWidget with rounded corners
        container_widget = QWidget()
        container_widget.setObjectName("graphy")  # Set object name
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)  # Margin to space the PlotWidget from the edges

        # Graph widget (PlotWidget) with the actual plot
        graph_widget = pg.PlotWidget()
        graph_widget.setBackground("#2b2b2b")
        graph_widget.showGrid(False, True)
        graph_widget.setLabel("left", y_label)
        graph_widget.setLabel("bottom", x_label)
        graph_widget.setMouseEnabled(x=True, y=False)
        graph_widget.setClipToView(True)
        graph_widget.setMinimumSize(200, 150)
        graph_widget.setYRange(-10, 10)

        # Add the PlotWidget to the container's layout
        container_layout.addWidget(graph_widget)

        # Add the container to the main layout
        self.plot_layout.addWidget(container_widget, row, 0)

        # Create a curve for each axis with a different color
        curve_x = graph_widget.plot([], pen='r', name='X Acceleration')
        curve_y = graph_widget.plot([], pen='g', name='Y Acceleration')
        curve_z = graph_widget.plot([], pen='b', name='Z Acceleration')

        return (curve_x, curve_y, curve_z)

    def update_data_buffers(self, sensor_id, timeus, accel_x, accel_y, accel_z):
        sensor_id = int(sensor_id)  # Convert sensor_id to int
        self.data_recorder.record_data(timeus, sensor_id, accel_x, accel_y, accel_z)  # Record the data
        if sensor_id in self.data_buffers:
            self.data_buffers[sensor_id]['x'].append(accel_x)
            self.data_buffers[sensor_id]['y'].append(accel_y)
            self.data_buffers[sensor_id]['z'].append(accel_z)

    def update_plots(self):
        for sensor_id in self.data_buffers.keys():
            x_data = self.data_buffers[sensor_id]['x'].get_all()
            y_data = self.data_buffers[sensor_id]['y'].get_all()
            z_data = self.data_buffers[sensor_id]['z'].get_all()

            # Update each curve for the current sensor
            curve_x, curve_y, curve_z = self.plot_data_items[sensor_id]
            curve_x.setData(range(len(x_data)), x_data)
            curve_y.setData(range(len(y_data)), y_data)
            curve_z.setData(range(len(z_data)), z_data)

    def change_buffer_size(self, index):
        self.buffer_capacity = self.buffer_sizes[index]
        for sensor_id in self.data_buffers.keys():
            # Reset the circular buffers with the new size
            self.data_buffers[sensor_id]['x'] = CircularBuffer(self.buffer_capacity)
            self.data_buffers[sensor_id]['y'] = CircularBuffer(self.buffer_capacity)
            self.data_buffers[sensor_id]['z'] = CircularBuffer(self.buffer_capacity)

    def toggle_plotting(self, state):
        if state == 0:  # 0 means unchecked
            print("Stopping plot updates...")  # Debugging line
            self.plot_timer.stop()  # Stop the timer when unchecked
        elif state == 2:  # 2 means checked
            print("Starting plot updates...")  # Debugging line
            self.plot_timer.start()  # Start the timer when checked

    def toggle_recording(self):
        if self.record_button.text() == "Start Recording":
            # Start recording
            self.data_recorder.start_recording()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: #A4243B; color: white;")
            # Enable other UI elements if needed, or disable them for recording

        else:
            # Stop recording
            self.data_recorder.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #2C6E49; color: white;")
            self.data_recorder.export_default()
            # Re-enable or reset other UI elements if needed

    def export_data(self):
        self.data_recorder.export_data()

def load_stylesheet(app):
    # Get the absolute path of the stylesheet file
    style_file = os.path.join(os.path.dirname(__file__), "Preferences/style_dark.qss")

    # Read the content of the stylesheet
    with open(style_file, "r") as f:
        app.setStyleSheet(f.read())

def main():
    app = QApplication(sys.argv)
    load_stylesheet(app)
    main = SerialPlotterWindow()
    main.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()