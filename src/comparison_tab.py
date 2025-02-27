import os
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QSlider, QHBoxLayout, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt

class CSVFrequencyComparator(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.label = QLabel("Select CSV files to compare 'Natural Frequency (Hz)' values")
        self.button_select_files = QPushButton("Select Files")
        self.list_output = QListWidget()
        self.list_output.setSelectionMode(QListWidget.MultiSelection)

        self.slider_label = QLabel("Tolerance: 0.01 Hz")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100000)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.update_tolerance_label)

        self.sort_label = QLabel("Sort by:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Greatest Percent Difference", "Lowest to Highest Frequency"])
        self.sort_combo.currentIndexChanged.connect(self.sort_results)

        self.button_export = QPushButton("Export Selected Frequencies")
        self.button_export.clicked.connect(self.export_selected)

        layout.addWidget(self.label)
        layout.addWidget(self.button_select_files)

        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.slider_label)
        slider_layout.addWidget(self.slider)
        layout.addLayout(slider_layout)

        layout.addWidget(self.sort_label)
        layout.addWidget(self.sort_combo)
        layout.addWidget(self.list_output)
        layout.addWidget(self.button_export)

        self.button_select_files.clicked.connect(self.select_files)

        self.tolerance = 0.01
        self.last_files = []
        self.file_data = {}  # {file: dataframe}
        # Each group is a dict with keys: "f1", "f2", "diff", "values", "files", "sample_count"
        self.groups = []

    def update_tolerance_label(self, value):
        self.tolerance = value / 1000
        self.slider_label.setText(f"Tolerance: {self.tolerance:.3f} Hz")
        if self.last_files:
            self.process_files(self.last_files)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select CSV Files", "", "CSV Files (*.csv)")
        if files:
            self.process_files(files)

    def process_files(self, files):
        self.last_files = files
        self.file_data.clear()
        freq_records = []  # Each record: (frequency, file)
        try:
            for file in files:
                df = pd.read_csv(file)
                if 'Natural Frequency (Hz)' in df.columns:
                    self.file_data[file] = df
                    for freq in df['Natural Frequency (Hz)'].dropna().tolist():
                        freq_records.append((freq, file))
                else:
                    QMessageBox.warning(self, "Missing Column", f"File '{file}' lacks 'Natural Frequency (Hz)' column.")
            freq_records.sort(key=lambda r: r[0])
            groups = []
            while freq_records:
                record = freq_records.pop(0)
                group = [record]
                # Group frequencies by comparing to the first value in the group
                while freq_records and abs(freq_records[0][0] - group[0][0]) <= self.tolerance:
                    group.append(freq_records.pop(0))
                groups.append(group)
            self.groups = []
            for group in groups:
                values = [r[0] for r in group]
                f1 = min(values)
                f2 = max(values)
                diff = (f2 - f1) / f1 * 100 if f1 != 0 else 0.0
                files_set = {r[1] for r in group}
                sample_count = len(files_set)
                self.groups.append({
                    "f1": f1,
                    "f2": f2,
                    "diff": diff,
                    "values": values,
                    "files": files_set,
                    "sample_count": sample_count
                })
            self.sort_results()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

    def sort_results(self):
        # Filter out groups that only appear in one CSV
        display_groups = [g for g in self.groups if g["sample_count"] > 1]
        if self.sort_combo.currentText() == "Greatest Percent Difference":
            display_groups.sort(key=lambda g: g["diff"], reverse=True)
        else:
            display_groups.sort(key=lambda g: g["f1"])
        self.groups = display_groups
        self.list_output.clear()
        for group in self.groups:
            text = (f"{group['f1']:.3f} Hz ↔ {group['f2']:.3f} Hz | Diff: {group['diff']:.2f}% "
                    f"| Samples: {group['sample_count']}")
            item = QListWidgetItem(text)
            self.list_output.addItem(item)

    def export_selected(self):
        selected_items = self.list_output.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "No frequencies selected for export.")
            return

        export_rows = []
        for item in selected_items:
            row = self.list_output.row(item)
            group = self.groups[row]
            values = group["values"]
            mean_freq = sum(values) / len(values)
            deviation = (max(values) - min(values)) / mean_freq * 100 if mean_freq != 0 else 0.0
            sensor_ids = set()
            axes = set()
            for file in group["files"]:
                df = self.file_data[file]
                matches = df[abs(df['Natural Frequency (Hz)'] - mean_freq) <= self.tolerance]
                for _, row_data in matches.iterrows():
                    sensor_ids.add(str(row_data['Sensor ID']))
                    axes.add(str(row_data['Axis']))
            sensor_ids_str = ", ".join(sorted(sensor_ids))
            axes_str = ", ".join(sorted(axes))
            export_rows.append({
                "Natural Frequency (Hz)": mean_freq,
                "Sensor ID": sensor_ids_str,
                "Axis": axes_str,
                "Deviation (%)": deviation
            })
        export_rows.sort(key=lambda r: r["Natural Frequency (Hz)"])
        for idx, row in enumerate(export_rows, start=1):
            row["Mode Number"] = idx

        columns = ["Mode Number", "Natural Frequency (Hz)", "Sensor ID", "Axis", "Deviation (%)"]
        file, _ = QFileDialog.getSaveFileName(self, "Save Selected Frequencies", "selected_frequencies.csv", "CSV Files (*.csv)")
        if file:
            try:
                df_export = pd.DataFrame(export_rows)
                df_export = df_export[columns]
                df_export.to_csv(file, index=False)
                QMessageBox.information(self, "Success", "Selected frequencies exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while saving: {str(e)}")
