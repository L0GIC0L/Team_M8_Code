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
    QLineEdit, QFormLayout, QFrame, QScrollArea, QGridLayout
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

def update_config_file(
    bolt_states,
    striker_config,
    sensor_config,
    detection_tolerance=200,
    hit_threshold=3,
    recording_delay=3000,
    recording_duration=10000,
    file_path=CONFIG_FILE_PATH
):
    config = {
        "bolt_configuration": bolt_states,
        "striker_configuration": striker_config,
        "sensor_configuration": sensor_config,
        "detection_tolerance": detection_tolerance,
        "hit_threshold": hit_threshold,
        "recording_delay": recording_delay,
        "recording_duration": recording_duration,
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
        "detection_tolerance": 200,
        "hit_threshold": 3,
        "recording_delay": 3000,
        "recording_duration": 10000,
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
        # Load new settings or use defaults if not found
        self.detection_tolerance = config.get("detection_tolerance", 200)
        self.hit_threshold = config.get("hit_threshold", 3)
        self.recording_delay = config.get("recording_delay", 3000)
        self.recording_duration = config.get("recording_duration", 10000)

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
        main_layout = QGridLayout()  # Use QGridLayout for better positioning

        # ========== Left Section (Widgets) ==========
        widgets_layout = QHBoxLayout()
        widgets_layout.addWidget(self.drum_widget)
        widgets_layout.addWidget(self.config_widget)
        widgets_layout.addWidget(self.bolt_widget)
        main_layout.addLayout(widgets_layout, 0, 0, 1, 2)  # Span across two columns

        # ========== Middle Section (Impact & Config Buttons) ==========
        impact_layout = QHBoxLayout()
        for pos in ["Front", "Right", "Left"]:
            btn = QPushButton(pos)
            btn.clicked.connect(lambda _, p=pos: self.set_image(p))
            impact_layout.addWidget(btn)
        main_layout.addLayout(impact_layout, 1, 0)  # First column

        config_layout = QHBoxLayout()
        for conf in ["A", "B", "C"]:
            btn = QPushButton(f"Config {conf}")
            btn.clicked.connect(lambda _, c=conf: self.select_config(c))
            config_layout.addWidget(btn)
        main_layout.addLayout(config_layout, 2, 0)  # First column

        # ========== Middle Controls (Padding & Stylesheet) ==========
        controls_layout = QHBoxLayout()

        # Left side: Padding factor controls
        left_layout = QVBoxLayout()
        self.padding_label = QLabel("PF=1")
        self.padding_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.padding_label)
        self.padding_slider = QSlider(Qt.Horizontal)
        self.padding_slider.setRange(1, 10)
        self.padding_slider.setValue(5)
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
        self.stylesheet_dropdown.currentIndexChanged.connect(self.change_stylesheet)
        right_layout.addWidget(self.stylesheet_dropdown)
        controls_layout.addLayout(right_layout)

        main_layout.addLayout(controls_layout, 3, 0)  # Left section (column 0)

        # ========== Right Section (Options - Scrollable) ==========
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumSize(300, 250)
        scroll_area.setMaximumWidth(300)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setObjectName("scroll")
        content_layout = QGridLayout(content_widget)

        # Set vertical and horizontal spacing between items
        content_layout.setVerticalSpacing(15)
        content_layout.setHorizontalSpacing(10)

        # Set margins around the layout
        content_layout.setContentsMargins(10, 10, 10, 10)

        # Options title centered at the top
        options_label = QLabel("Recording Options")
        options_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        options_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        content_layout.addWidget(options_label, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        # Detection Tolerance
        label_dt = QLabel("Detection Tolerance:")
        label_dt.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(label_dt, 1, 0)
        self.dt_edit = QLineEdit(str(self.detection_tolerance))
        self.dt_edit.setFixedWidth(100)
        content_layout.addWidget(self.dt_edit, 1, 1)

        # Hit Threshold
        label_ht = QLabel("Hit Threshold:")
        label_ht.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(label_ht, 2, 0)
        self.ht_edit = QLineEdit(str(self.hit_threshold))
        self.ht_edit.setFixedWidth(100)
        content_layout.addWidget(self.ht_edit, 2, 1)

        # Recording Delay
        label_rd = QLabel("Recording Delay (ms):")
        label_rd.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(label_rd, 3, 0)
        self.rd_edit = QLineEdit(str(self.recording_delay))
        self.rd_edit.setFixedWidth(100)
        content_layout.addWidget(self.rd_edit, 3, 1)

        # Recording Duration
        label_rdu = QLabel("Recording Duration (ms):")
        label_rdu.setAlignment(Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(label_rdu, 4, 0)
        self.rdu_edit = QLineEdit(str(self.recording_duration))
        self.rdu_edit.setFixedWidth(100)
        content_layout.addWidget(self.rdu_edit, 4, 1)

        # Set the content widget inside the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 0, 3, 5, 1)  # Placed in the rightmost column

        # ========== Bottom Section (Legend) ==========
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend: Black = 1, Blue = 3, Red = 2, Yellow = 0"))
        main_layout.addLayout(legend_layout, 4, 0, 1, 1)  # Span across two columns

        # Connect editingFinished signals to update our settings
        self.dt_edit.editingFinished.connect(self.update_advanced_settings)
        self.ht_edit.editingFinished.connect(self.update_advanced_settings)
        self.rd_edit.editingFinished.connect(self.update_advanced_settings)
        self.rdu_edit.editingFinished.connect(self.update_advanced_settings)

        self.setLayout(main_layout)

    def set_image(self, position):
        self.drum_widget.set_image(f"../Preferences/Striker_On_{position}.png")
        print(f"{position} button clicked")
        self.current_striker_config = position
        self.update_configuration_file()

    def select_config(self, config):
        self.config_widget.set_image(f"../Preferences/Sensor_Config_{config}.png")
        print(f"Config {config} selected")
        self.current_sensor_config = config
        self.update_configuration_file()

    def update_padding(self):
        pf = self.padding_slider.value()
        self.padding_label.setText(f"PF={pf}")
        if self.plot_fft:
            self.plot_fft.update_padding_factor(pf)

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

    def change_stylesheet(self):
        self.apply_stylesheet(self.stylesheet_dropdown.currentText())

    def update_advanced_settings(self):
        # Update detection tolerance
        try:
            self.detection_tolerance = float(self.dt_edit.text())
        except ValueError:
            self.dt_edit.setText(str(self.detection_tolerance))
        # Update hit threshold
        try:
            self.hit_threshold = float(self.ht_edit.text())
        except ValueError:
            self.ht_edit.setText(str(self.hit_threshold))
        # Update recording delay
        try:
            self.recording_delay = int(self.rd_edit.text())
        except ValueError:
            self.rd_edit.setText(str(self.recording_delay))
        # Update recording duration
        try:
            self.recording_duration = int(self.rdu_edit.text())
        except ValueError:
            self.rdu_edit.setText(str(self.recording_duration))
        self.update_configuration_file()

    def update_configuration_file(self):
        update_config_file(
            self.bolt_widget.bolts,
            self.current_striker_config,
            self.current_sensor_config,
            detection_tolerance=self.detection_tolerance,
            hit_threshold=self.hit_threshold,
            recording_delay=self.recording_delay,
            recording_duration=self.recording_duration,
        )
