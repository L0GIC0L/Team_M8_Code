import sys
from PyQt6.QtCore import QIODevice, QTimer
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo

class MaxValueDisplay(QWidget):
    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.max_value = float('-inf')

        self.init_ui()

    def init_ui(self):
        # Label to display the max value
        self.label = QLabel('Max Value: -', self)

        # Update button to manually update the max value label
        self.update_button = QPushButton('Update', self)
        self.update_button.clicked.connect(self.update_label)

        # Reset button to reset the max value
        self.reset_button = QPushButton('Reset', self)
        self.reset_button.clicked.connect(self.reset_max_value)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.update_button)
        layout.addWidget(self.reset_button)  # Add reset button to the layout

        self.setLayout(layout)
        self.setWindowTitle('Serial Max Value')

        # Timer to periodically update the label
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_label)
        self.timer.start(1000)  # Update every second

        # Connect the readyRead signal to a function to process serial data
        self.serial_port.readyRead.connect(self.read_serial_data)

    def read_serial_data(self):
        # Read all available data from the serial port
        while self.serial_port.canReadLine():
            data = self.serial_port.readLine().data().decode('utf-8').strip()
            try:
                value = float(data)
                if value > self.max_value:
                    self.max_value = value
            except ValueError:
                # Ignore lines that cannot be converted to float
                pass

    def update_label(self):
        # Update the label with the current max value
        self.label.setText(f'Max Value: {self.max_value}')

    def reset_max_value(self):
        # Reset the max value to negative infinity and update the label
        self.max_value = float('-inf')
        self.label.setText(f'Max Value: {self.max_value}')

def main():
    app = QApplication(sys.argv)

    # Initialize the serial port
    serial_port = QSerialPort()
    serial_port.setPortName("/dev/ttyACM0")  # Replace with your serial port
    serial_port.setBaudRate(9600)    # Set baud rate as an integer (9600)

    if not serial_port.open(QIODevice.OpenModeFlag.ReadOnly):
        print("Failed to open serial port")
        sys.exit(1)

    # Create the PyQt application window
    window = MaxValueDisplay(serial_port)
    window.show()

    # Start the Qt event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
