from PySide6.QtCore import QIODevice, QThread, Signal
from PySide6.QtSerialPort import QSerialPort

class SerialReader(QThread):
    # Define a generic data_received signal with sensor_id
    data_received = Signal(str, float, float, float, float)

    def __init__(self, port_name="/dev/ttyACM0", baud_rate=1000000):
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

    def set_speed(self, speed = "400"):
        if self.serial.write((str(speed) + '\n').encode()) & self.serial.open(QIODevice.OpenModeFlag.ReadWrite):
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