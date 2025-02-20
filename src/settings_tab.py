import json, os, math
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    QComboBox,
    QSlider,
)
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QPoint, QRect, QSize

CONFIG_FILE_PATH = "../Preferences/config.json"

def load_stylesheet(app, style_name):
    path = os.path.join(os.path.dirname(__file__), f"../Preferences/{style_name}.qss")
    if os.path.exists(path):
        with open(path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Error: Stylesheet file '{path}' not found.")
        app.setStyleSheet("")

def update_config_file(bolt_states, striker_config, sensor_config, file_path=CONFIG_FILE_PATH):
    config = {
        "bolt_configuration": bolt_states,
        "striker_configuration": striker_config,
        "sensor_configuration": sensor_config,
    }
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(config, f, indent=4)
    print("Updated config file with:", json.dumps(config, indent=4))

def load_config(file_path=CONFIG_FILE_PATH):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            config = json.load(f)
        print("Loaded config file:", json.dumps(config, indent=4))
        return config
    default_config = {
        "bolt_configuration": [True] * 20,
        "striker_configuration": "Front",
        "sensor_configuration": "A",
    }
    print(
        "No config file found. Using default config:",
        json.dumps(default_config, indent=4),
    )
    return default_config

class BoltWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.bolt_count = 20
        self.bolts = [True] * self.bolt_count
        self.bolt_positions = []
        self.config_update_callback = None
        self.setMinimumSize(250, 250)
        self.update_bolt_positions()

    def update_bolt_positions(self):
        self.bolt_positions.clear()
        size = min(self.width(), self.height())
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = size // 2 - 15
        for i in range(self.bolt_count):
            angle = (-2 * math.pi * (i + math.pi / 2 + 14)) / self.bolt_count
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            self.bolt_positions.append(
                QRect(QPoint(int(x - 15), int(y - 15)), QSize(30, 30))
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_bolt_positions()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        for i, rect in enumerate(self.bolt_positions):
            painter.setBrush(Qt.black if self.bolts[i] else Qt.red)
            painter.drawEllipse(rect)
            painter.setPen(Qt.white if self.bolts[i] else Qt.black)
            painter.drawText(rect, Qt.AlignCenter, str(i + 1))
            painter.setPen(Qt.NoPen)

    def mousePressEvent(self, event):
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        for i, rect in enumerate(self.bolt_positions):
            if rect.contains(pos):
                self.bolts[i] = not self.bolts[i]
                self.update()
                print(f"Bolt state: {''.join('1' if b else '0' for b in self.bolts)}")
                if self.config_update_callback:
                    self.config_update_callback()
                break

class ImageWidget(QWidget):
    def __init__(self, image_path):
        super().__init__()
        self.pixmap = QPixmap(image_path)
        self.scaled_pixmap = None
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.circle_color = Qt.white

    def resizeEvent(self, event):
        super().resizeEvent(event)
        size = min(self.width(), self.height()) - 20
        self.scaled_pixmap = (
            self.pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            if size > 0
            else QPixmap()
        )
        self.update()

    def set_image(self, image_path):
        self.pixmap = QPixmap(image_path)
        self.resizeEvent(None)

    def paintEvent(self, event):
        painter = QPainter(self)
        size = min(self.width(), self.height()) - 20
        center = QPoint(self.width() // 2, self.height() // 2)
        circle_rect = QRect(center.x() - size // 2, center.y() - size // 2, size, size)
        painter.setBrush(self.circle_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(circle_rect)
        if self.scaled_pixmap and not self.scaled_pixmap.isNull():
            pix_rect = self.scaled_pixmap.rect()
            pix_rect.moveCenter(circle_rect.center())
            painter.drawPixmap(pix_rect.topLeft(), self.scaled_pixmap)

class Settings(QWidget):
    def __init__(self, plot_fft_instance=None, serial_plotter_instance=None):
        super().__init__()
        # Store references to external instances (if any)
        self.plot_fft = plot_fft_instance
        self.plot_serial = serial_plotter_instance

        # Load configuration from file or use defaults
        config = load_config()
        self.current_striker_config = config.get("striker_configuration", "Front")
        self.current_sensor_config = config.get("sensor_configuration", "A")
        default_bolts = config.get("bolt_configuration", [True] * 20)

        # Initialize image widgets using the current configuration
        self.drum_widget = ImageWidget(
            f"../Preferences/Striker_On_{self.current_striker_config}.png"
        )
        self.config_widget = ImageWidget(
            f"../Preferences/Sensor_Config_{self.current_sensor_config}.png"
        )
        # Initialize the bolt widget and update its state from the loaded configuration
        self.bolt_widget = BoltWidget()
        self.bolt_widget.bolts = default_bolts
        self.bolt_widget.config_update_callback = self.update_configuration_file

        # Build the UI layout
        self.init_ui()

        # Write the loaded configuration to file to ensure consistency
        self.update_configuration_file()

    # Set up the user interface layout
    def init_ui(self):
        main_layout = QVBoxLayout()  # Main vertical layout

        # Top layout containing the striker image, sensor image, and bolt widget
        widgets_layout = QHBoxLayout()
        widgets_layout.addWidget(self.drum_widget)
        widgets_layout.addWidget(self.config_widget)
        widgets_layout.addWidget(self.bolt_widget)
        main_layout.addLayout(widgets_layout)

        # Layout for impact location (striker) buttons
        impact_layout = QHBoxLayout()
        for pos in ["Front", "Right", "Left"]:
            btn = QPushButton(pos)
            # When clicked, update the striker image and config setting
            btn.clicked.connect(lambda _, p=pos: self.set_image(p))
            impact_layout.addWidget(btn)
        main_layout.addLayout(impact_layout)

        # Layout for sensor configuration buttons
        config_layout = QHBoxLayout()
        for conf in ["A", "B", "C"]:
            btn = QPushButton(f"Config {conf}")
            # When clicked, update the sensor image and config setting
            btn.clicked.connect(lambda _, c=conf: self.select_config(c))
            config_layout.addWidget(btn)
        main_layout.addLayout(config_layout)

        # Layout for padding factor slider and stylesheet selection
        controls_layout = QHBoxLayout()

        # Left side: Padding factor controls
        left_layout = QVBoxLayout()
        self.padding_label = QLabel("PF=1")  # Display current padding factor
        self.padding_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.padding_label)
        self.padding_slider = QSlider(Qt.Horizontal)
        self.padding_slider.setRange(1, 10)  # Slider range from 1 to 10
        self.padding_slider.setValue(1)      # Default value is 1
        # Update padding when slider value changes
        self.padding_slider.valueChanged.connect(self.update_padding)
        left_layout.addWidget(self.padding_slider)
        controls_layout.addLayout(left_layout)

        # Right side: Stylesheet selection dropdown
        right_layout = QVBoxLayout()
        lbl = QLabel("Select Stylesheet:")
        lbl.setAlignment(Qt.AlignBottom)
        right_layout.addWidget(lbl)
        self.stylesheet_dropdown = QComboBox()
        self.stylesheet_dropdown.addItems(
            ["Default", "Dark", "Light", "AMERICA", "Abomination"]
        )
        # Change the stylesheet when a new option is selected
        self.stylesheet_dropdown.currentIndexChanged.connect(self.change_stylesheet)
        right_layout.addWidget(self.stylesheet_dropdown)
        controls_layout.addLayout(right_layout)
        main_layout.addLayout(controls_layout)

        # Layout for color legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend: Black = 1, Blue = 3, Red = 2, Yellow = 0"))
        main_layout.addLayout(legend_layout)

        # Apply the constructed layout to the Settings widget
        self.setLayout(main_layout)

    # Update the striker image based on the selected position
    def set_image(self, position):
        self.drum_widget.set_image(f"../Preferences/Striker_On_{position}.png")
        print(f"{position} button clicked")
        self.current_striker_config = position
        self.update_configuration_file()

    # Update the sensor configuration image based on the selected config
    def select_config(self, config):
        self.config_widget.set_image(f"../Preferences/Sensor_Config_{config}.png")
        print(f"Config {config} selected")
        self.current_sensor_config = config
        self.update_configuration_file()

    # Update the padding factor display and notify external plot instances if applicable
    def update_padding(self):
        pf = self.padding_slider.value()
        self.padding_label.setText(f"PF={pf}")
        if self.plot_fft:
            self.plot_fft.update_padding_factor(pf)

    # Load and apply a new stylesheet based on the given style name
    def apply_stylesheet(self, style):
        load_stylesheet(QApplication.instance(), f"style_{style.lower()}")
        if self.plot_fft and self.plot_serial:
            col = (
                self.plot_fft.container_widget.palette()
                .color(self.plot_fft.container_widget.backgroundRole())
                .name()
            )
            self.plot_fft.set_background(col)
            self.plot_serial.update_plot_settings()

    # Handle changes in the stylesheet selection dropdown
    def change_stylesheet(self):
        self.apply_stylesheet(self.stylesheet_dropdown.currentText())

    # Write the current configuration from all widgets to the config file
    def update_configuration_file(self):
        update_config_file(
            self.bolt_widget.bolts,
            self.current_striker_config,
            self.current_sensor_config,
        )