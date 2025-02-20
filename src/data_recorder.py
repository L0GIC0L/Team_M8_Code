import csv
import os
import json
import math
from datetime import datetime
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog

class DataRecorder(QThread):
    recording_started = Signal()
    recording_stopped = Signal()
    auto_recording_started = Signal()
    auto_recording_stopped = Signal()
    impact_detected_signal = Signal()

    def __init__(self):
        super().__init__()
        self.data_records = []
        self.recording = False
        self.auto_record_mode = False
        self.auto_pending = False
        self.impact_detected_time = None
        self.auto_record_start_time = None
        self.delay_timer = None  # Timer for delayed recording start
        self.recording_duration = 10  # Duration for auto recording in seconds
        self.last_saved_file = None

    def run(self):
        # No need to call exec_() here unless using an event loop
        pass

    def start_recording(self):
        self.data_records.clear()
        self.recording = True
        self.recording_started.emit()
        print("Recording started...")

    def stop_recording(self):
        self.recording = False
        self.recording_stopped.emit()
        print("Recording stopped.")

    def start_auto_recording(self):
        self.data_records.clear()
        self.auto_record_mode = True
        self.auto_pending = False
        self.recording = False
        self.impact_detected_time = None
        self.auto_record_start_time = None
        self.delay_timer = None
        self.auto_recording_started.emit()
        print("Auto Recording Mode Enabled...")

    def stop_auto_recording(self):
        self.auto_record_mode = False
        self.auto_pending = False
        self.recording = False
        if self.delay_timer is not None:
            self.delay_timer.stop()
            self.delay_timer = None
        self.auto_recording_stopped.emit()
        print("Auto Recording Mode Disabled...")

    def auto_record_data(self, timeus, sensor_id, accel_x, accel_y, accel_z):
        if not self.auto_record_mode:
            return

        magnitude = math.sqrt(accel_x ** 2 + accel_y ** 2 + accel_z ** 2)

        # Detect impact and initiate pending state
        if not self.recording and not self.auto_pending and magnitude >= 3:
            self.auto_pending = True
            self.impact_detected_signal.emit()
            print("Impact detected! Waiting 10 seconds to start auto recording.")

            # Start a QTimer to handle the delay before recording
            self.delay_timer = QTimer()
            self.delay_timer.setSingleShot(True)
            self.delay_timer.timeout.connect(self.start_delayed_recording)
            self.delay_timer.start(3000)  # Delay in milliseconds (10 seconds)

    def start_delayed_recording(self):
        self.recording = True
        self.auto_pending = False
        self.auto_record_start_time = datetime.now()
        print("Auto recording started after delay.")

        # Start a QTimer to stop recording after the specified duration
        self.stop_timer = QTimer()
        self.stop_timer.setSingleShot(True)
        self.stop_timer.timeout.connect(self.stop_auto_recording_session)
        self.stop_timer.start(self.recording_duration * 1000)  # Duration in milliseconds

    def stop_auto_recording_session(self):
        self.recording = False
        print(f"Auto recording ended after {self.recording_duration} seconds.")
        # Use the "preset" mode for exporting as before
        self.export_data("preset")
        self.data_records.clear()
        self.auto_recording_stopped.emit()

    def record_data(self, timeus, sensor_id, accel_x, accel_y, accel_z):
        if self.recording:
            self.data_records.append([int(timeus), sensor_id, accel_x, accel_y, accel_z])

    def export_data(self, mode="data"):
        if not self.data_records:
            QMessageBox.warning(None, "Export Error", "No data to export.")
            return

        # Determine the file path based on the chosen mode
        if mode == "data":
            filename, _ = QFileDialog.getSaveFileName(None, "Export Data", "", "CSV Files (*.csv)")
            if not filename:
                QMessageBox.warning(None, "Export Error", "Invalid filename.")
                return
            file_path = filename
            export_method = "dialog"
        elif mode == "default":
            directory = os.path.expanduser("../Cached_Samples/")
            os.makedirs(directory, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(directory, f"samples_{timestamp}.csv")
            export_method = "default"
        elif mode == "preset":
            config_path = os.path.expanduser("../Preferences/config.json")
            try:
                with open(config_path, "r") as config_file:
                    config = json.load(config_file)
            except Exception as e:
                print(f"Error reading config file: {e}")
                QMessageBox.warning(None, "Export Error", "Failed to load configuration file.")
                return

            # Map striker configuration to abbreviations
            striker_map = {"Front": "F", "Right": "R", "Left": "L"}
            striker_config = striker_map.get(config.get("striker_configuration", ""), "U")  # "U" for Unknown
            # Sensor configuration: Expecting "A", "B", or "C"
            sensor_config = config.get("sensor_configuration", "A")
            # Convert bolt configuration to a string of 1s and 0s
            bolt_config = "".join(["1" if b else "0" for b in config.get("bolt_configuration", [])])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{striker_config}{sensor_config}{bolt_config}_{timestamp}.csv"
            directory = os.path.expanduser("../Preset_Samples/")
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, filename)
            export_method = "preset"
        else:
            QMessageBox.warning(None, "Export Error", "Invalid export mode specified.")
            return

        self.last_saved_file = file_path

        try:
            with open(file_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(
                    ["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration", "Z Acceleration"])
                writer.writerows(self.data_records)
            if export_method == "dialog":
                QMessageBox.information(None, "Export Success", "Data exported successfully.")
            print(f"Data exported to {file_path}")
        except Exception as e:
            print(f"Error exporting data: {e}")
            QMessageBox.warning(None, "Export Error", "Failed to export data.")
