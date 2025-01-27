import csv
import os
from datetime import datetime  # Add this import statement

from PySide6.QtWidgets import QMessageBox, QFileDialog


class DataRecorder:
    def __init__(self):
        super().__init__()
        self.data_records = []  # Store all recorded data
        self.recording = False   # State to check if recording is active

    def start_recording(self):
        self.recording = True
        self.data_records.clear()  # Clear previous data
        print("Recording started...")  # Debugging line

    def stop_recording(self):
        self.recording = False
        print("Recording stopped.")  # Debugging line

    def record_data(self, timeus, sensor_id, accel_x, accel_y, accel_z):
        if self.recording:
            # Append the new data to the records
            self.data_records.append([int(timeus), sensor_id, accel_x, accel_y, accel_z])

    def export_data(self):
        if len(self.data_records) > 0:
            filename, _ = QFileDialog.getSaveFileName(
                None, "Export Data", "", "CSV Files (*.csv)")
            if filename:
                try:
                    with open(filename, "w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration", "Z Acceleration"])
                        writer.writerows(self.data_records)
                    QMessageBox.information(None, "Export Success", "Data exported successfully.")
                except Exception:
                    QMessageBox.warning(None, "Export Error", "Failed to export data.")
            else:
                QMessageBox.warning(None, "Export Error", "Invalid filename.")
        else:
            QMessageBox.warning(None, "Export Error", "No data to export.")

    def export_default(self):
        # Create the directory if it does not exist
        directory = os.path.expanduser("../Cached_Samples/")  # Use expanduser to handle home directory
        os.makedirs(directory, exist_ok=True)  # Create the directory if it doesn't exist

        if len(self.data_records) > 0:
            # Generate a default filename based on the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(directory, f"samples_{timestamp}.csv")
            self.last_saved_file = filename

            try:
                with open(filename, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration",
                                     "Z Acceleration"])
                    writer.writerows(self.data_records)
            except Exception:
                QMessageBox.warning(None, "Export Error", "Failed to export data.")
        else:
            QMessageBox.warning(None, "Export Error", "No data to export.")
