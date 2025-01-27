import os

import pandas as pd
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox


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

        # Add widgets to layout
        layout.addWidget(self.label)
        layout.addWidget(self.button_select_files)
        layout.addWidget(self.button_select_folder)
        layout.addWidget(self.text_output)
        layout.addWidget(self.button_save)

        # Signals
        self.button_select_files.clicked.connect(self.select_files)
        self.button_select_folder.clicked.connect(self.select_folder)
        self.button_save.clicked.connect(self.save_combined_values)

        # Data
        self.combined_values = []

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select CSV Files", "", "CSV Files (*.csv)"
        )

        if not files:
            return

        self.process_files(files)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder"
        )

        if not folder:
            return

        files = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(".csv") and "natural_frequencies" in f.lower()
        ]

        if not files:
            QMessageBox.warning(self, "No Files Found",
                                "No files with 'natural_frequencies' in their name were found in the selected folder.")
            return

        self.process_files(files)

    def process_files(self, files):
        self.combined_values = []
        try:
            # Store frequencies rounded to 3 decimal places
            freq_dict = {}

            for file in files:
                df = pd.read_csv(file)
                if 'Natural Frequency (Hz)' in df.columns:
                    for freq in df['Natural Frequency (Hz)'].dropna():
                        rounded_freq = round(freq, 3)
                        if rounded_freq in freq_dict:
                            freq_dict[rounded_freq].append(freq)
                        else:
                            freq_dict[rounded_freq] = [freq]
                else:
                    QMessageBox.warning(self, "Missing Column",
                                        f"File '{file}' does not contain 'Natural Frequency (Hz)' column.")

            # Now average the values with the same rounded frequency
            self.combined_values = [
                round(sum(values) / len(values), 3) for values in freq_dict.values()
            ]

            # Sort and display the combined values
            self.combined_values = sorted(self.combined_values)

            self.text_output.setText("\n".join(map(str, self.combined_values)))
            self.button_save.setEnabled(True if self.combined_values else False)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def save_combined_values(self):
        file, _ = QFileDialog.getSaveFileName(self, "Save Combined Values", "combined_values.csv",
                                              "CSV Files (*.csv)")

        if not file:
            return

        try:
            df = pd.DataFrame({'Natural Frequency (Hz)': self.combined_values})
            df.to_csv(file, index=False)
            QMessageBox.information(self, "Success", "Combined values saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving: {str(e)}")
