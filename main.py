import csv
import os
import signal
import sys

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QIODevice, Qt
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, \
    QFileDialog, QComboBox, QTextEdit, QTabWidget, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPalette, QColor


class CircularBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = np.zeros(capacity)
        self.index = 0
        self.full = False

    def push(self, value):
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.capacity
        if self.index == 0:
            self.full = True

    def get_data(self):
        if self.full:
            return np.concatenate((self.buffer[self.index:], self.buffer[:self.index]))
        else:
            return self.buffer[:self.index]

class SerialPlotterWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real-Time Accelerometer Viewer")
        self.setGeometry(100, 100, 1200, 600)

        self.tab_widget = QTabWidget()  # Create a tab widget

        self.plot_tab = QWidget()
        self.plot_layout = QGridLayout()

        self.graph_widgets = []
        self.data_buffers = []
        self.plot_data_items = []
        self.data_records = []

        self.buffer_sizes = [1000, 3000, 5000, 7000, 10000]
        self.buffer_capacity = self.buffer_sizes[0]

        self.serial_port = QSerialPort()
        self.serial_port.setPortName("/dev/ttyACM0")  # Adjust to your serial port
        self.serial_port.setBaudRate(1000000)
        self.serial_port.readyRead.connect(self.receive_serial_data)

        # Create text edit for live serial data
        self.serial_text_edit = QTextEdit()
        self.serial_text_edit.setReadOnly(True)
        self.plot_layout.addWidget(self.serial_text_edit, 0, 3, 3, 1)  # Add it to the right side of the layout

        # Add the buffer size combo and export button to the layout
        buffer_size_combo = QComboBox()
        buffer_size_combo.addItems([str(size) for size in self.buffer_sizes])
        buffer_size_combo.setCurrentIndex(0)
        buffer_size_combo.currentIndexChanged.connect(self.change_buffer_size)
        self.plot_layout.addWidget(buffer_size_combo, 2, 0, 1, 1)

        export_button = QPushButton("Export Data")
        export_button.clicked.connect(self.export_data)
        self.plot_layout.addWidget(export_button, 2, 1, 1, 1)

        # Set up the plotting tab's layout and add to tab widget
        self.plot_tab.setLayout(self.plot_layout)
        self.tab_widget.addTab(self.plot_tab, "Plot Data")  # Add Plot tab

        # Create another tab for additional settings or information
        self.settings_tab = QWidget()
        self.settings_layout = QVBoxLayout()
        self.settings_text = QTextEdit("Settings or additional information can go here.")
        self.settings_layout.addWidget(self.settings_text)
        self.settings_tab.setLayout(self.settings_layout)

        # Add the settings tab to the tab widget
        self.tab_widget.addTab(self.settings_tab, "Settings")

        # Set the tab widget as the central widget of the main window
        self.setCentralWidget(self.tab_widget)

    def add_graph(self, name, x_label, y_label, row, col, color, is_live=False):
        # Create the graph widget
        graph_widget = pg.PlotWidget()
        graph_widget.setBackground("#2b2b2b")
        graph_widget.showGrid(True, True)
        graph_widget.setLabel("left", y_label)
        graph_widget.setLabel("bottom", x_label)
        graph_widget.setMouseEnabled(x=True, y=False)
        graph_widget.setClipToView(True)

        # Create a container widget for the graph with a layout
        graph_widget_container = QWidget()
        graph_widget_layout = QVBoxLayout()
        graph_widget_layout.addWidget(graph_widget)
        graph_widget_container.setLayout(graph_widget_layout)

        # Apply rounded corners to the graph container using a stylesheet
        graph_widget_container.setStyleSheet("""
            QWidget {
                border-radius: 10px;  /* Rounded corners */
                background-color: #2b2b2b;
            }
        """)

        # Add the container to the main layout
        self.plot_layout.addWidget(graph_widget_container, row, col)

        # Data buffer and plot item setup
        data_buffer = CircularBuffer(self.buffer_capacity)
        plot_data_item = graph_widget.plot(data_buffer.get_data(), pen=pg.mkPen(color, width=1))

        self.data_buffers.append(data_buffer)
        self.plot_data_items.append(plot_data_item)

    def receive_serial_data(self):
        while self.serial_port.canReadLine():
            try:
                data = self.serial_port.readLine().data().decode("utf-8").strip()
                values = data.split()

                # Update text edit with new serial data
                self.serial_text_edit.append(data)

                scaling_factor = 256
                gravity = 9.8067

                if len(values) == 5:
                    accel_id = int(values[0])
                    x_accel = (float(values[2]) / scaling_factor) * gravity
                    y_accel = (float(values[3]) / scaling_factor) * gravity
                    z_accel = (float(values[4]) / scaling_factor) * gravity

                    if accel_id == 1:
                        self.update_plot(0, x_accel, 0, 0)  # Plot X for Sensor 1
                        self.update_plot(1, 0, y_accel, 0, is_y_data=True)  # Plot Y for Sensor 1 on bottom graph
                        self.update_plot(2, 0, 0, z_accel, is_y_data=False,
                                         is_z_data=True)  # Plot Z for Sensor 2 on bottom graph

                    elif accel_id == 2:
                        self.update_plot(3, x_accel, 0, 0)  # Plot X for Sensor 2
                        self.update_plot(4, 0, y_accel, 0, is_y_data=True)
                        self.update_plot(5, 0, 0, z_accel, is_y_data=False,
                                         is_z_data=True)  # Plot Z for Sensor 2 on bottom graph
                    elif accel_id == 3:
                        self.update_plot(2, x_accel, y_accel, z_accel)  # Plot X for Sensor 3
                    elif accel_id == 4:
                        self.update_plot(3, x_accel, y_accel, z_accel)  # Plot X for Sensor 4

                    self.data_records.append([accel_id, x_accel, y_accel, z_accel])

            except (UnicodeDecodeError, IndexError, ValueError) as e:
                print(f"Error processing data: {e}")

    def update_plot(self, index, x, y, z, is_y_data=False, is_z_data=False):
        if index < len(self.data_buffers):
            if is_y_data:
                # Use Y acceleration data for specific plots
                self.data_buffers[index].push(y)
            elif is_z_data:
                # Use Z acceleration data for specific plots
                self.data_buffers[index].push(z)
            else:
                # Use X acceleration data for default plots
                self.data_buffers[index].push(x)
            self.plot_data_items[index].setData(self.data_buffers[index].get_data())

    def export_data(self):
        if len(self.data_records) > 0:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Data", "", "CSV Files (*.csv)")
            if filename:
                try:
                    with open(filename, "w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Accelerometer ID", "X Acceleration", "Y Acceleration", "Z Acceleration"])
                        writer.writerows(self.data_records)
                    QMessageBox.information(
                        self, "Export Success", "Data exported successfully.")
                except Exception:
                    QMessageBox.warning(
                        self, "Export Error", "Failed to export data.")
            else:
                QMessageBox.warning(self, "Export Error", "Invalid filename.")
        else:
            QMessageBox.warning(self, "Export Error", "No data to export.")

    def change_buffer_size(self, index):
        self.buffer_capacity = self.buffer_sizes[index]
        self.data_buffers = [CircularBuffer(self.buffer_capacity) for _ in range(len(self.data_buffers))]

    def closeEvent(self, event):
        self.serial_port.close()
        event.accept()


def keyboard_interrupt_handler(signal, frame):
    sys.exit(0)


def load_stylesheet(app):
    # Get the absolute path of the stylesheet file
    style_file = os.path.join(os.path.dirname(__file__), "style.qss")

    # Read the content of the stylesheet
    with open(style_file, "r") as f:
        app.setStyleSheet(f.read())

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load stylesheet from external file
    load_stylesheet(app)

    signal.signal(signal.SIGINT, keyboard_interrupt_handler)

    plotter_window = SerialPlotterWindow()
    plotter_window.add_graph("Accel 1 X", "Time", "X Acceleration", 0, 0, "r")
    plotter_window.add_graph("Accel 1 Y", "Time", "Y Acceleration", 0, 1, "g")
    plotter_window.add_graph("Accel 1 Z", "Time", "Z Acceleration", 0, 2, "y")

    plotter_window.add_graph("Accel 2 X", "Time", "X Acceleration", 1, 0, "r")
    plotter_window.add_graph("Accel 2 Y", "Time", "Y Acceleration", 1, 1, "g")
    plotter_window.add_graph("Accel 2 Z", "Time", "Z Acceleration", 1, 2, "y")

    if not plotter_window.serial_port.open(QIODevice.OpenModeFlag.ReadWrite):
        print("Failed to open serial port.")
        # sys.exit(1)

    plotter_window.show()
    sys.exit(app.exec())