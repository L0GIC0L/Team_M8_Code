import csv
import os
import json
import math
from pathlib import Path

import numpy as np
from datetime import datetime
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QMessageBox, QFileDialog

import pandas as pd

from fft_analysis_tab import PlotFFT, process_frequency_data, detect_peaks

TOLERANCE = 300

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
        self.plot_fft_instance = PlotFFT()  # Initialize plotFFT instance

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
        self.export_data("modes")
        self.data_records.clear()
        self.auto_recording_stopped.emit()

    def record_data(self, timeus, sensor_id, accel_x, accel_y, accel_z):
        if self.recording:
            self.data_records.append([int(timeus), sensor_id, accel_x, accel_y, accel_z])

    def export_data(self, mode="data"):
        if not self.data_records:
            QMessageBox.warning(None, "Export Error", "No data to export.")
            return

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

            striker_map = {"Front": "F", "Right": "R", "Left": "L"}
            striker_config = striker_map.get(config.get("striker_configuration", ""), "U")
            sensor_config = config.get("sensor_configuration", "0")
            bolt_config = "".join(["1" if b else "0" for b in config.get("bolt_configuration", [])])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{striker_config}{sensor_config}{bolt_config}_{timestamp}.csv"
            directory = os.path.expanduser("../Preset_Samples/")
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, filename)
            export_method = "preset"
        elif mode == "modes":
            config_path = os.path.expanduser("../Preferences/config.json")
            try:
                with open(config_path, "r") as config_file:
                    config = json.load(config_file)
            except Exception as e:
                print(f"Error reading config file: {e}")
                QMessageBox.warning(None, "Export Error", "Failed to load configuration file.")
                return

            striker_map = {"Front": "F", "Right": "R", "Left": "L"}
            striker_config = striker_map.get(config.get("striker_configuration", ""), "U")
            sensor_config = config.get("sensor_configuration", "0")
            bolt_config = "".join(["1" if b else "0" for b in config.get("bolt_configuration", [])])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"MODES_{striker_config}{sensor_config}{bolt_config}_{timestamp}.csv"
            directory = os.path.expanduser("../Preset_Samples/")
            os.makedirs(directory, exist_ok=True)
            file_path = os.path.join(directory, filename)
            export_method = "modes"
        else:
            QMessageBox.warning(None, "Export Error", "Invalid export mode specified.")
            return

        self.last_saved_file = file_path

        try:
            if mode == "modes":
                data = pd.DataFrame(self.data_records,
                                    columns=["Time [microseconds]", "Accelerometer ID", "X Acceleration",
                                             "Y Acceleration", "Z Acceleration"])
                modes_data = []
                # Process each sensor and axis using the new global functions.
                for sensor_id in data["Accelerometer ID"].unique():
                    sensor_data = data[data["Accelerometer ID"] == sensor_id]
                    for axis in ["X Acceleration", "Y Acceleration", "Z Acceleration"]:
                        processed = process_frequency_data(
                            [sensor_data], axis,
                            self.plot_fft_instance.padding_factor,
                            self.plot_fft_instance.plot_mode
                        )
                        if processed:
                            freq_data = processed[0]
                            positive_freqs = freq_data["positive_freqs"]
                            positive_magnitudes = freq_data["positive_magnitudes"]

                            natural_frequencies, _ = detect_peaks(positive_freqs, positive_magnitudes, TOLERANCE )
                            for freq in natural_frequencies:
                                modes_data.append([sensor_id, axis, freq])
                # Merge the modes and export as a CSV.
                freq_dict = {}
                for sensor_id, axis, freq in modes_data:
                    if freq not in freq_dict:
                        freq_dict[freq] = {"sensor_ids": set(), "axes": set()}
                    freq_dict[freq]["sensor_ids"].add(sensor_id)
                    freq_dict[freq]["axes"].add(axis)
                combined_modes = []
                mode_number = 1
                for freq, values in freq_dict.items():
                    sensor_ids = ", ".join(map(str, sorted(values["sensor_ids"])))
                    axes = "".join(sorted([axis[0] for axis in values["axes"]])) + " Acceleration"
                    combined_modes.append([mode_number, freq, sensor_ids, axes])
                    mode_number += 1
                modes_df = pd.DataFrame(combined_modes,
                                        columns=["Mode Number", "Natural Frequency (Hz)", "Sensor ID", "Axis"])
                modes_df.to_csv(file_path, index=False)
                print(f"Natural frequencies exported to {file_path}")
            else:
                with open(file_path, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Time [microseconds]", "Accelerometer ID", "X Acceleration", "Y Acceleration",
                                     "Z Acceleration"])
                    writer.writerows(self.data_records)
                if export_method == "dialog":
                    QMessageBox.information(None, "Export Success", "Data exported successfully.")
                print(f"Data exported to {file_path}")
        except Exception as e:
            print(f"Error exporting data: {e}")
            QMessageBox.warning(None, "Export Error", "Failed to export data.")

        # If mode is preset, automatically process the FFT from the exported CSV.
        if mode == "preset":
            self.compute_fft_preset(file_path)

    def compute_fft_preset(self, file_path):
        try:
            data = pd.read_csv(file_path)
            data = data.apply(pd.to_numeric, errors='coerce')
            data = data.dropna(subset=['Time [microseconds]', 'X Acceleration', 'Y Acceleration', 'Z Acceleration'])
            datasets_filtered = []
            for sensor_id in data['Accelerometer ID'].unique():
                sensor_data = data[data['Accelerometer ID'] == sensor_id]
                for axis in ['X Acceleration', 'Y Acceleration', 'Z Acceleration']:
                    if axis not in sensor_data.columns:
                        print("Axis {} not found in sensor data. Skipping.".format(axis))
                        continue
                    axis_data = sensor_data[['Time [microseconds]', axis]].copy()
                    print("Processing {} for sensor {}".format(axis, sensor_id))
                    print(axis_data.head())
                    # Use the global process_frequency_data function
                    processed = process_frequency_data(
                        [axis_data], axis,
                        self.plot_fft_instance.padding_factor,
                        self.plot_fft_instance.plot_mode
                    )
                    if processed:
                        freq_data = processed[0]
                        datasets_filtered.append({
                            'sensor_id': sensor_id,
                            'axis': axis,
                            'positive_freqs': freq_data['positive_freqs'],
                            'positive_magnitudes': freq_data['positive_magnitudes']
                        })
                        # Export FFT data for debugging
                        df_fft = pd.DataFrame({
                            "Frequency (Hz)": freq_data['positive_freqs'],
                            "Magnitude": freq_data['positive_magnitudes']
                        })
                        debug_filename = f"FFT_Sensor_{sensor_id}_{axis.replace(' ', '_')}.csv"
                        debug_folder = Path.cwd() / "Preset_Samples" / "Debug_FFTs"
                        debug_folder.mkdir(parents=True, exist_ok=True)
                        debug_path = debug_folder / debug_filename
                        df_fft.to_csv(debug_path, index=False)
                        print(f"Exported FFT debug CSV to: {debug_path.resolve()}")
                    else:
                        print("FFT processing returned no results for sensor {} axis {}".format(sensor_id, axis))

            all_natural_frequencies = []
            for ds in datasets_filtered:
                pos_freqs = ds["positive_freqs"]
                pos_mags = ds["positive_magnitudes"]
                # Use a tolerance of 20 (adjust as needed)
                natural_freqs, _ = detect_peaks(pos_freqs, pos_mags, TOLERANCE)
                all_natural_frequencies.extend(natural_freqs)
            unique_freqs = np.unique(np.round(all_natural_frequencies, decimals=2))
            print("Detected Natural Frequencies:")
            for freq in unique_freqs:
                print("{:.2f} Hz".format(freq))
        except Exception as e:
            print("Error processing FFT: {}".format(e))
            QMessageBox.warning(None, "FFT Error", "Failed to process data for FFT.")
