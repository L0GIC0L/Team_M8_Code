from PySide6.QtCore import QIODevice, QThread, Signal
from PySide6.QtSerialPort import QSerialPort

class SerialReader(QThread):
    data_received = Signal(str, float, float, float, float)

    def __init__(self, port_name="/dev/ttyACM0", baud_rate=1000000):
        super().__init__()
        self.port_name = port_name
        self.baud_rate = baud_rate
        self.serial = QSerialPort()
        self.serial.setPortName(self.port_name)
        self.serial.setBaudRate(self.baud_rate)
        self.serial.readyRead.connect(self.read_data)

    def run(self):
        if not self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
            print(f"Failed to open port {self.serial.portName()}")
        else:
            print(f"Connected to {self.serial.portName()}!")
        self.exec_()  # Start the event loop for the thread

    def set_port(self, port_name):
        self.port_name = port_name
        if self.serial.isOpen():
            self.serial.close()
        self.serial.setPortName(port_name)
        print(f"Port set to {port_name}")
        self.start_serial()

    def set_speed(self, speed="400"):
        if self.serial.write((str(speed) + '\n').encode()) and self.serial.isOpen():
            print(f"Successfully changed speed to {speed}.")
        else:
            print(f"Failed to set speed to {speed}.")

    def start_serial(self):
        if not self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
            print(f"Failed to open port {self.serial.portName()}")
        else:
            print(f"Connected to {self.serial.portName()}!")

    def read_data(self):
        while self.serial.canReadLine():
            line = self.serial.readLine().data().decode().strip()
            parts = line.split()
            if len(parts) == 5:
                sensor_id, timeus, accel_x, accel_y, accel_z = parts
                try:
                    timeus = float(timeus)
                    accel_x = float(accel_x)
                    accel_y = float(accel_y)
                    accel_z = float(accel_z)
                    self.data_received.emit(sensor_id, timeus, accel_x, accel_y, accel_z)
                except ValueError:
                    print("Error parsing data.")

    def stop_serial(self):
        if self.serial.isOpen():
            self.serial.close()
