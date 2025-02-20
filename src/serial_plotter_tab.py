from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QCheckBox, QComboBox, QPushButton, QScrollArea
from pglive.sources.data_connector import DataConnector
from pglive.sources.live_axis_range import LiveAxisRange
from pglive.sources.live_plot import LiveLinePlot
from pglive.sources.live_plot_widget import LivePlotWidget

from data_recorder import DataRecorder
from serial_reader import SerialReader

class SerialPlotterTab(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Real-Time Accelerometer Viewer")
        self.setGeometry(100, 100, 600, 600)

        self.plot_layout = QGridLayout(self)
        self.setLayout(self.plot_layout)
        self.data_connectors = {}

        # Initialize SerialReader
        self.serial_reader = SerialReader()
        self.serial_reader.data_received.connect(self.update_data_buffers)
        self.serial_reader.start()
        self.serial_reader.start_serial()  # Start reading from the default port

        # Options Menu
        self.setup_options_menu()

        # Initialize sensor data storage
        self.init_sensor_data()

    def setup_options_menu(self):
        self.serial_ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1", "COM0", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9"]
        self.current_port_index = 0  # Default to the second port in the list

        self.communication_speeds = [0, 100, 200, 300, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 2000, 4000, 8000, 10000, 100000]
        self.selected_speed_index = 0

        self.data_recorder = DataRecorder()  # Create an instance of DataRecorder
        self.data_recorder.start()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(300, 250)
        scroll_area.setMaximumWidth(300)
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
        self.max_points_combo.addItems([str(size) for size in [100, 200, 400, 600, 800]])
        self.max_points_combo.setCurrentIndex(3)  # Default to 600 if it's the initial size
        self.max_points_combo.currentIndexChanged.connect(self.update_plot_settings)
        content_layout.addWidget(self.max_points_combo, 5, 1)  # Adjust row index as needed

        # Update speed combo
        update_speed_label = QLabel("Update Speed:")
        update_speed_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(update_speed_label, 6, 0)

        self.update_speed_combo = QComboBox()
        self.update_speed_combo.addItems([str(i) for i in [10, 20, 30, 40, 50, 60, 120, 240, 480, 960]])  # Example FPS options
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
        self.plot_layout.addWidget(scroll_area, 0, 3, 4, 1)

    def init_sensor_data(self):
        # Initialize data connectors for multiple sensors
        self.sensor_count = 4  # Adjust based on the number of sensors you expect
        for sensor_id in range(1, self.sensor_count + 1):
            self.add_sensor_plot(sensor_id-1, sensor_id-1)

    def get_axis_colors(self,sensor_id):
        if sensor_id == 0:
            # Sensor ID 0 - Variations of yellow
            return ["#FFFF00", "#FFD700", "#FFEC8B"]  # Yellow, Golden Yellow, Light Yellow
        elif sensor_id == 1:
            # Sensor ID 1 - Variations of blue
            return ["#0000FF", "#1E90FF", "#ADD8E6"]  # Blue, Dodger Blue, Light Blue
        elif sensor_id == 2:
            # Sensor ID 2 - Variations of red
            return ["#FF0000", "#FF6347", "#FF7F50"]  # Red, Tomato, Coral
        elif sensor_id == 3:
            # Sensor ID 3 - Variations of grey
            return ["#808080", "#A9A9A9", "#D3D3D3"]  # Gray shades
        elif sensor_id == 4:
            # Sensor ID 4 - Variations of cyan
            return ["#00FFFF", "#00CED1", "#E0FFFF"]  # Cyan, Dark Cyan, Light Cyan
        elif sensor_id == 5:
            # Sensor ID 5 - Variations of pink
            return ["#FFC0CB", "#FFB6C1", "#FF69B4"]  # Pink, Light Pink, Hot Pink
        else:
            # Default case for unrecognized sensor_id (green variations)
            return ["#008000", "#32CD32", "#90EE90"]  # Green, Lime Green, Pale Green

    def add_sensor_plot(self, sensor_id, row, max_points=300,update_rate=30, hex_color="#2b2b2b"):
        self.container_widget = QWidget()
        self.container_widget.setObjectName("graphy")  # Set object name
        container_layout = QVBoxLayout(self.container_widget)
        container_layout.setContentsMargins(5, 5, 5, 5)  # Margin to space the PlotWidget from the edges

        self.sensor_plot_widget = LivePlotWidget(title=f'Sensor ID: {sensor_id}',
                                            x_range_controller=LiveAxisRange(),
                                            y_range_controller=LiveAxisRange())
        self.sensor_plot_widget.setBackground(hex_color)

        colors = self.get_axis_colors(sensor_id)
        #colors = ["red", "orange", "cyan"]  # Colors for X, Y, Z respectively

        for i, axis in enumerate(['X', 'Y', 'Z']):
            plot = LiveLinePlot(pen=colors[i])
            self.sensor_plot_widget.addItem(plot)
            connector = DataConnector(plot, max_points=max_points, update_rate=update_rate)
            self.data_connectors[(sensor_id, axis)] = connector

        # Add the PlotWidget to the container's layout
        container_layout.addWidget(self.sensor_plot_widget)

        # Add the container to the main layout
        self.plot_layout.addWidget(self.container_widget, row, 0)

    def update_plot_settings(self):
        print(f"Starting update_plot_settings")
        selected_max_points = int(self.max_points_combo.currentText())
        selected_update_rate = int(self.update_speed_combo.currentText())
        source_color = self.container_widget.palette().color(self.container_widget.backgroundRole())
        hex_color = source_color.name()

        # Get valid sensor IDs (ensure positive)
        existing_sensors = {abs(s_id) for (s_id, axis) in self.data_connectors.keys()}
        print(f"Existing sensors: {existing_sensors}")

        # Remove existing plots from the specified column
        self.remove_widgets_in_column(0)  # Assuming you want to clear column 0

        # Re-add plots in proper grid positions
        row = 0
        for sensor_id in sorted(existing_sensors):
            print(f"Adding sensor {sensor_id} at row {row}")
            self.add_sensor_plot(
                row,  # Use row as grid position
                sensor_id,
                max_points=selected_max_points,
                update_rate=selected_update_rate,
                hex_color=hex_color
            )
            row += 1

    def remove_widgets_in_column(self, column_index):
        print(f"Removing all widgets in column {column_index}")

        # Iterate through all items in the layout
        for i in reversed(range(self.plot_layout.count())):
            item = self.plot_layout.itemAt(i)
            widget = item.widget()

            if widget is not None:
                # Check if the widget is in the specified column
                pos = self.plot_layout.getItemPosition(i)
                if pos[1] == column_index:  # pos[1] is the column position
                    print(f"Removing widget at position {pos}")
                    self.plot_layout.removeWidget(widget)
                    widget.setParent(None)
                    widget.deleteLater()

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
            self.toggle_plotting(0)

            # Start recording
            self.data_recorder.start_recording()
            self.record_button.setText("Stop Recording")
            self.record_button.setStyleSheet("background-color: #A4243B; color: white;")
        else:
            # Stop recording
            self.toggle_plotting(2)
            self.data_recorder.stop_recording()
            self.record_button.setText("Start Recording")
            self.record_button.setStyleSheet("background-color: #2C6E49; color: white;")
            self.data_recorder.export_default()

    def export_data(self):
        self.data_recorder.export_data()
