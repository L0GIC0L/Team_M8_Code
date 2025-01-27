import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QLabel, QSlider

def load_stylesheet(app, style_name):
    # Map stylesheet names to file paths
    stylesheet_path = os.path.join(os.path.dirname(__file__), f"../Preferences/{style_name}.qss")

    # Check if the file exists
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Error: Stylesheet file '{stylesheet_path}' not found.")
        app.setStyleSheet("")  # Reset to default if file is missing

class Settings(QWidget):
    def __init__(self, plot_fft_instance,serial_plotter_instance):
        super().__init__()
        self.plot_fft = plot_fft_instance  # Reference to PlotFFT instance
        self.plot_serial = serial_plotter_instance  # Reference to serial plotter instance
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

            source_color = self.plot_fft.container_widget.palette().color(
            self.plot_fft.container_widget.backgroundRole())
            color_hex = source_color.name()
            self.plot_fft.set_background(color_hex)
            self.plot_serial.set_background(color_hex)


        elif selected_style == "Dark Mode":
            load_stylesheet(QApplication.instance(), "style_dark")

            source_color = self.plot_fft.container_widget.palette().color(
            self.plot_fft.container_widget.backgroundRole())
            color_hex = source_color.name()
            self.plot_fft.set_background(color_hex)
            self.plot_serial.set_background(color_hex)

        elif selected_style == "Light Mode":
            load_stylesheet(QApplication.instance(), "style_light")

            source_color = self.plot_fft.container_widget.palette().color(
            self.plot_fft.container_widget.backgroundRole())
            color_hex = source_color.name()
            self.plot_fft.set_background(color_hex)
            self.plot_serial.set_background(color_hex)
