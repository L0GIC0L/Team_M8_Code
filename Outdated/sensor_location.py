import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSizePolicy
)
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QPoint, QRect, QSize


class BoltWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.bolt_count = 20
        self.bolts = [True] * self.bolt_count  # True means the bolt is present
        self.bolt_positions = []
        self.setMinimumSize(200, 200)
        self.update_bolt_positions()

    def update_bolt_positions(self):
        self.bolt_positions.clear()
        size = min(self.width(), self.height())
        center = QPoint(self.width() // 2, self.height() // 2)
        radius = size // 2 - 15

        for i in range(self.bolt_count):
            angle = (-2*math.pi * (i+math.pi/2+14)) / self.bolt_count
            x = center.x() + radius * math.cos(angle)
            y = center.y() + radius * math.sin(angle)
            rect = QRect(int(x - 15), int(y - 15), 25, 25)
            self.bolt_positions.append(rect)

    def resizeEvent(self, event):
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
        position = event.position().toPoint()

        for i, rect in enumerate(self.bolt_positions):
            if rect.contains(position):
                self.bolts[i] = not self.bolts[i]  # Toggle bolt state
                self.update()
                print(f"Bolt state: {''.join('1' if b else '0' for b in self.bolts)}")
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
        size = min(self.width(), self.height()) - 20  # Adjust padding as needed
        self.scaled_pixmap = self.pixmap.scaled(
            size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
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

        if self.scaled_pixmap:
            pixmap_rect = self.scaled_pixmap.rect()
            pixmap_rect.moveCenter(circle_rect.center())
            painter.drawPixmap(pixmap_rect.topLeft(), self.scaled_pixmap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Configuration Selector")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top layout with the three widgets
        top_layout = QHBoxLayout()
        main_layout.addLayout(top_layout)

        self.drum_widget = ImageWidget("../Preferences/Striker_On_Front.png")
        self.config_widget = ImageWidget("../Preferences/Sensor_Config_A.png")
        self.bolt_widget = BoltWidget()

        top_layout.addWidget(self.drum_widget)
        top_layout.addWidget(self.config_widget)
        top_layout.addWidget(self.bolt_widget)

        # Impact location buttons
        impact_layout = QHBoxLayout()
        main_layout.addLayout(impact_layout)
        positions = ['Front', 'Right', 'Left']
        for position in positions:
            btn = QPushButton(position)
            btn.clicked.connect(lambda _, pos=position: self.set_image(pos))
            impact_layout.addWidget(btn)

        # Sensor configuration buttons
        config_layout = QHBoxLayout()
        main_layout.addLayout(config_layout)
        configs = ['A', 'B', 'C']
        for config in configs:
            btn = QPushButton(f"Config {config}")
            btn.clicked.connect(lambda _, conf=config: self.select_config(conf))
            config_layout.addWidget(btn)

    def set_image(self, position):
        image_path = f"../Preferences/Striker_On_{position}.png"
        self.drum_widget.set_image(image_path)
        print(f"{position} button clicked")

    def select_config(self, config):
        config_path = f"../Preferences/Sensor_Config_{config}.png"
        self.config_widget.set_image(config_path)
        print(f"Config {config} selected")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())