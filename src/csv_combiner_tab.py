import os
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QSlider, QHBoxLayout
)
from PySide6.QtCore import Qt


class CSVCombinerWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Layout
        layout = QVBoxLayout(self)

        # Widgets
        self.label = QLabel("Select CSV files to combine their 'Natural Frequency (Hz)' values")
        self.button_select_files = QPushButton("Select Files")
        self.button_select_folder = QPushButton("Select Folder")
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.button_save = QPushButton("Save Combined Values")
        self.button_save.setEnabled(False)

        # Tolerance slider
        self.slider_label = QLabel("Tolerance: 0.01 Hz")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)  # Represents 0.001 Hz
        self.slider.setMaximum(100)  # Represents 0.1 Hz
        self.slider.setValue(10)  # Default to 0.01 Hz
        self.slider.valueChanged.connect(self.update_tolerance_label)

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.button_select_files)
        layout.addWidget(self.button_select_folder)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.slider)
        layout.addLayout(slider_layout)

        layout.addWidget(self.text_output)
        layout.addWidget(self.button_save)

        # Signals
        self.button_select_files.clicked.connect(self.select_files)
        self.button_select_folder.clicked.connect(self.select_folder)
        self.button_save.clicked.connect(self.save_combined_values)

        # Data
        self.combined_values = []
        self.tolerance = 0.01  # Default tolerance
        self.last_files = []  # Store last processed files

    def update_tolerance_label(self, value):
        self.tolerance = value / 1000  # Convert slider value to Hz
        self.slider_label.setText(f"Tolerance: {self.tolerance:.3f} Hz")

        # If files have been processed, reprocess them with the new tolerance
        if self.last_files:
            self.process_files(self.last_files)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select CSV Files", "", "CSV Files (*.csv)")
        if files:
            self.process_files(files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        files = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(".csv") and "natural_frequencies" in f.lower()
        ]

        if not files:
            QMessageBox.warning(self, "No Files Found", "No relevant CSV files found in the selected folder.")
            return

        self.process_files(files)

    def process_files(self, files):
        self.last_files = files  # Store the last processed files
        self.combined_values = []
        try:
            freq_dict = {}

            for file in files:
                df = pd.read_csv(file)
                if 'Natural Frequency (Hz)' in df.columns:
                    for freq in df['Natural Frequency (Hz)'].dropna():
                        grouped = False
                        for key in list(freq_dict.keys()):
                            if abs(freq - key) <= self.tolerance:
                                freq_dict[key].append(freq)
                                grouped = True
                                break
                        if not grouped:
                            freq_dict[freq] = [freq]
                else:
                    QMessageBox.warning(self, "Missing Column",
                                        f"File '{file}' does not contain 'Natural Frequency (Hz)' column.")

            self.combined_values = [round(sum(values) / len(values), 3) for values in freq_dict.values()]
            self.combined_values.sort()

            self.text_output.setText("\n".join(map(str, self.combined_values)))
            self.button_save.setEnabled(bool(self.combined_values))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def save_combined_values(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save Combined Values", "combined_values.csv", "CSV Files (*.csv)")
        if not file:
            return

        try:
            df = pd.DataFrame({'Natural Frequency (Hz)': self.combined_values})
            df.to_csv(file, index=False)
            QMessageBox.information(self, "Success", "Combined values saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving: {str(e)}")
