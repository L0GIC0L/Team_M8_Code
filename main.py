import csv
import os
import signal
import sys

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QIODevice, Qt
from PyQt6.QtSerialPort import QSerialPort
from PyQt6.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, \
    QFileDialog, QComboBox, QTextEdit, QTabWidget, QGraphicsDropShadowEffect, QLabel, QScrollArea
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


        
    # ---------------------------------------- Initialization ---------------------------------------- #
        super().__init__()

        self.setWindowTitle("Real-Time Accelerometer Viewer")
        self.setGeometry(100, 100, 1200, 600)

        self.tab_widget = QTabWidget()  # Create a tab widget



    # ----------------------------------------- Plot Tab ------------------------------------------ #
        self.plot_tab = QWidget()
        self.plot_layout = QGridLayout()

        self.graph_widgets = []
        self.data_buffers = []
        self.plot_data_items = []
        self.data_records = []

        self.buffer_sizes = [1000, 3000, 5000, 7000, 10000,17500,30000]
        self.buffer_capacity = self.buffer_sizes[0]

        self.serial_ports = ["/dev/ttyACM0","/dev/ttyUSB0", "/dev/ttyUSB1", "COM0", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"]
        self.current_port_index = 1  # Default to the second port in the list

        self.serial_port = QSerialPort()
        self.serial_port.setPortName(self.serial_ports[self.current_port_index])
        self.serial_port.setBaudRate(460800)
        self.serial_port.readyRead.connect(self.receive_serial_data)

        

        # ------------------------------------ Raw Data ------------------------------------ #
        self.serial_text_edit = QTextEdit()
        self.serial_text_edit.setReadOnly(True)
        self.plot_layout.addWidget(self.serial_text_edit, 2, 0, 1, 4)  # Add it to the right side of the layout



        # ---------------------------------- Options Menu ---------------------------------- #
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)  # Allows the scroll area to resize with the window
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar

        content_widget = QWidget()
        content_layout = QGridLayout(content_widget)
        content_widget.setObjectName("scroll")  # Set object name
        scroll_area.setMinimumSize(200, 150)

        options_label = QLabel("Options")
        content_layout.addWidget(options_label, 0, 0, 1, 2)
        options_label.setObjectName("heading_label")  # Set object name
        options_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        options_label.setFixedHeight(50)

        # Add the buffer size combo and export button to the layout
        buffer_size_label = QLabel("Buffer Size:")
        content_layout.addWidget(buffer_size_label, 1, 0, 1, 1)
        buffer_size_label.setObjectName("combo_label")  # Set object name
        buffer_size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        buffer_size_combo = QComboBox()
        buffer_size_combo.addItems([str(size) for size in self.buffer_sizes])
        buffer_size_combo.setCurrentIndex(0)
        buffer_size_combo.currentIndexChanged.connect(self.change_buffer_size)
        content_layout.addWidget(buffer_size_combo, 1, 1, 1, 1)

        # Add the buffer size combo and export button to the layout
        serial_port_label = QLabel("COM Port:")
        content_layout.addWidget(serial_port_label, 2, 0, 1, 1)
        serial_port_label.setObjectName("combo_label")  # Set object name
        serial_port_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.serial_port_combo = QComboBox()
        self.serial_port_combo.addItems(self.serial_ports)
        self.serial_port_combo.setCurrentIndex(self.current_port_index)
        self.serial_port_combo.currentIndexChanged.connect(self.change_serial_port)
        content_layout.addWidget(self.serial_port_combo, 2, 1, 1, 1)

        self.reconnect_button = QPushButton("Reconnect")
        self.reconnect_button.clicked.connect(self.reconnect_serial_port)
        content_layout.addWidget(self.reconnect_button, 3, 0, 1, 2)

        export_button = QPushButton("Export Data")
        export_button.clicked.connect(self.export_data)
        content_layout.addWidget(export_button, 4, 0, 1, 2)

        spacer = QWidget()
        content_layout.addWidget(spacer, 5, 0, 1, 2)

        scroll_area.setWidget(content_widget)
        self.plot_layout.addWidget(scroll_area, 0, 3, 2, 1)

        # Set up the plotting tab's layout and add to tab widget
        self.plot_tab.setLayout(self.plot_layout)
        self.tab_widget.addTab(self.plot_tab, "Plot Data")  # Add Plot tab



    # ----------------------------------------- Settings Tab ------------------------------------------ #
        # Create another tab for additional settings or information
        self.settings_tab = QWidget()
        self.settings_layout = QGridLayout()

        s_scroll_area = QScrollArea()
        s_scroll_area.setWidgetResizable(True)  # Allows the scroll area to resize with the window
        s_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar
        s_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar

        s_content_widget = QWidget()
        s_content_layout = QGridLayout(s_content_widget)
        s_content_widget.setObjectName("scroll")  # Set object name
        s_scroll_area.setMinimumSize(200, 150)

        settings_label = QLabel("Settings")
        s_content_layout.addWidget(settings_label, 0, 0, 1, 2)
        settings_label.setObjectName("heading_label")  # Set object name
        settings_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        s_scroll_area.setWidget(s_content_widget)
        self.settings_layout.addWidget(s_scroll_area, 0, 3, 2, 1)

        # Set up the plotting tab's layout and add to tab widget
        self.settings_tab.setLayout(self.settings_layout)
        self.tab_widget.addTab(self.settings_tab, "Settings")  # Add Plot tab



    # ----------------------------------------- Frequency Graph Tab ------------------------------------------ #
        # Create another tab for additional settings or information
        self.frequency_tab = QWidget()
        self.frequency_layout = QGridLayout()

        f_scroll_area = QScrollArea()
        f_scroll_area.setWidgetResizable(True)  # Allows the scroll area to resize with the window
        f_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar
        f_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar

        f_content_widget = QWidget()
        f_content_layout = QGridLayout(f_content_widget)
        f_content_widget.setObjectName("scroll")  # Set object name
        f_scroll_area.setMinimumSize(200, 150)

        frequency_label = QLabel("Frequency Graph")
        f_content_layout.addWidget(frequency_label, 0, 0, 1, 2)
        frequency_label.setObjectName("heading_label")  # Set object name
        frequency_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        f_scroll_area.setWidget(f_content_widget)
        self.frequency_layout.addWidget(f_scroll_area, 0, 3, 2, 1)

        # Set up the plotting tab's layout and add to tab widget
        self.frequency_tab.setLayout(self.frequency_layout)
        self.tab_widget.addTab(self.frequency_tab, "Frequency Graph")  # Add Plot tab



    # ----------------------------------------- Analysis Tab ------------------------------------------ #
        # Create another tab for additional settings or information
        self.analysis_tab = QWidget()
        self.analysis_layout = QGridLayout()

        a_scroll_area = QScrollArea()
        a_scroll_area.setWidgetResizable(True)  # Allows the scroll area to resize with the window
        a_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar
        a_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Never show the horizontal scrollbar

        a_content_widget = QWidget()
        a_content_layout = QGridLayout(a_content_widget)
        a_content_widget.setObjectName("scroll")  # Set object name
        a_scroll_area.setMinimumSize(200, 150)

        analysis_label = QLabel("Analysis")
        a_content_layout.addWidget(analysis_label, 0, 0, 1, 2)
        analysis_label.setObjectName("heading_label")  # Set object name
        analysis_label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        a_scroll_area.setWidget(a_content_widget)
        self.analysis_layout.addWidget(a_scroll_area, 0, 3, 2, 1)

        # Set up the plotting tab's layout and add to tab widget
        self.analysis_tab.setLayout(self.analysis_layout)
        self.tab_widget.addTab(self.analysis_tab, "Analysis")  # Add Plot tab

        

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
        graph_widget.setMinimumSize(200, 150)

        # Create a container widget for the graph with a layout
        graph_widget_container = QWidget()
        graph_widget_container.setObjectName("graphy")  # Set object name
        graph_widget_layout = QVBoxLayout()
        graph_widget_layout.addWidget(graph_widget)
        graph_widget_container.setLayout(graph_widget_layout)

        # Add the container to the main layout
        self.plot_layout.addWidget(graph_widget_container, row, col, 1, 1)

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

                scaling_factor = 1
                gravity = 9.8067

                if len(values) == 5:
                    accel_id = int(values[0])
                    utime = (int(values[1]))
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

                    self.data_records.append([utime, accel_id, x_accel, y_accel, z_accel])

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
                        writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration", "Z Acceleration"])
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

    def change_serial_port(self, index):
        self.current_port_index = index
        self.reconnect_serial_port()

    def reconnect_serial_port(self):
        if self.serial_port.isOpen():
            self.serial_port.close()

        self.serial_port.setPortName(self.serial_ports[self.current_port_index])

        if self.serial_port.open(QSerialPort.OpenModeFlag.ReadWrite):
            print(f"Successfully connected to {self.serial_ports[self.current_port_index]}")
        else:
            print(f"Failed to connect to {self.serial_ports[self.current_port_index]}")
            QMessageBox.warning(self, "Connection Error",
                                f"Failed to connect to {self.serial_ports[self.current_port_index]}")

    def closeEvent(self, event):
        if self.serial_port.isOpen():
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

    # Try to open the serial port
    if not plotter_window.serial_port.open(QSerialPort.OpenModeFlag.ReadWrite):
        print(f"Failed to open serial port: {plotter_window.serial_port.errorString()}")
        QMessageBox.critical(plotter_window, "Serial Port Error",
                             f"Failed to open serial port: {plotter_window.serial_port.errorString()}\n"
                             "The application will continue running, but you may need to reconnect manually.")
        # Note: We're not exiting the application here, allowing for manual reconnection

    plotter_window.show()
    sys.exit(app.exec())
