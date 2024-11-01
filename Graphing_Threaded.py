import csv
import os
import signal
import sys
import time

import numpy as np
import pyqtgraph as pg

from PyQt6.QtCore import QIODevice, Qt,QTimer, QThread, pyqtSignal
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, \
    QFileDialog, QComboBox, QTextEdit, QTabWidget, QGraphicsDropShadowEffect, QLabel, QScrollArea, QCheckBox
from PyQt6.QtGui import QPalette, QColor

class SerialReader(QThread):
    # Define a generic data_received signal with sensor_id
    data_received = pyqtSignal(str, float, float, float, float)

    def __init__(self, port_name="/dev/ttyACM1", baud_rate=9600):
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

    def start_serial(self):
        if not self.serial.open(QIODevice.OpenModeFlag.ReadOnly):
            print(f"Failed to open port {self.serial.portName()}")
        else:
            print(f"Connected to {self.serial.portName()}")

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

class SerialPlotterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real-Time Accelerometer Viewer")
        self.setGeometry(100, 100, 1200, 600)

        self.tab_widget = QTabWidget()
        self.plot_tab = QWidget()
        self.plot_layout = QGridLayout()
        self.data_buffers = {}
        self.plot_data_items = {}

        self.buffer_sizes = [1000, 3000, 5000, 7000, 10000, 17500, 30000]
        self.buffer_capacity = self.buffer_sizes[0]

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

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

        # Initialize sensor data storage
        self.init_sensor_data()

    def setup_options_menu(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(200,100)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)

        options_label = QLabel("Options")
        content_layout.addWidget(options_label, 0, 0, 1, 2)
        options_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Buffer size combo
        buffer_size_label = QLabel("Buffer Size:")
        content_layout.addWidget(buffer_size_label, 3, 0, 1, 1)
        buffer_size_combo = QComboBox()
        buffer_size_combo.addItems([str(size) for size in self.buffer_sizes])
        buffer_size_combo.setCurrentIndex(0)
        buffer_size_combo.currentIndexChanged.connect(self.change_buffer_size)
        content_layout.addWidget(buffer_size_combo, 3, 1, 1, 1)

        # Checkbox for enabling/disabling plotting
        self.plot_enabled_checkbox = QCheckBox("Enable Plotting")
        self.plot_enabled_checkbox.setChecked(True)
        self.plot_enabled_checkbox.stateChanged.connect(self.toggle_plotting)
        content_layout.addWidget(self.plot_enabled_checkbox, 1, 0, 1, 2)

        self.data_recorder = DataRecorder()  # Create an instance of DataRecorder

        # Create buttons for recording control
        self.record_button = QPushButton("Start Recording")
        self.record_button.clicked.connect(self.start_recording)
        content_layout.addWidget(self.record_button, 4, 1, 1, 1)

        self.stop_record_button = QPushButton("Stop Recording")
        self.stop_record_button.clicked.connect(self.stop_recording)
        content_layout.addWidget(self.stop_record_button, 5, 1, 1, 1)

        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        content_layout.addWidget(self.export_button, 6, 1, 1, 1)

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

    def add_graph(self, name, x_label, y_label, row):
        graph_widget = pg.PlotWidget()
        graph_widget.setBackground("#2b2b2b")
        graph_widget.showGrid(False, True)
        graph_widget.setLabel("left", y_label)
        graph_widget.setLabel("bottom", x_label)
        graph_widget.setMouseEnabled(x=True, y=False)
        graph_widget.setClipToView(True)
        graph_widget.setMinimumSize(200, 150)
        graph_widget.setYRange(-10, 10)

        self.plot_layout.addWidget(graph_widget, row, 0)

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

    def start_recording(self):
        self.data_recorder.start_recording()
        self.record_button.setEnabled(False)
        self.stop_record_button.setEnabled(True)

    def stop_recording(self):
        self.data_recorder.stop_recording()
        self.record_button.setEnabled(True)
        self.stop_record_button.setEnabled(False)

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
