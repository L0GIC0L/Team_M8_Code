import sys
import pandas as pd
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QSlider, QLabel, QPushButton, QFileDialog
from PyQt6.QtCore import Qt
import pyqtgraph as pg
from scipy.signal import find_peaks
from scipy import signal

class SensorPlot(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set up the main window
        self.setWindowTitle("Sensor Data Plot with FFT")
        self.setGeometry(100, 100, 800, 600)

        # Create a central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Create the toggle button for PSD/FFT
        self.toggle_button = QPushButton("Show PSD")
        self.toggle_button.clicked.connect(self.toggle_plot)

        # Create two PlotWidgets: one for time domain and one for frequency domain
        self.plot_widget_time = pg.PlotWidget()  # Time domain plot
        self.plot_widget_time.setBackground("#252525")
        self.plot_widget_fft = pg.PlotWidget()  # Frequency domain plot
        self.plot_widget_fft.setBackground("#252525")

        # Create sliders for setting the FFT time interval and tolerance
        self.start_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_time_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)

        # Set ranges for sliders based on data length and tolerance
        self.start_time_slider.setRange(0, 100)
        self.end_time_slider.setRange(0, 100)
        self.tolerance_slider.setRange(1, 100)  # Example range for tolerance

        self.start_time_slider.setValue(0)
        self.end_time_slider.setValue(100)
        self.tolerance_slider.setValue(10)  # Example default tolerance

        self.start_time_slider.valueChanged.connect(self.update_plot)
        self.end_time_slider.valueChanged.connect(self.update_plot)
        self.tolerance_slider.valueChanged.connect(self.update_plot)

        # Add labels for the sliders
        self.start_time_label = QLabel("Start Time: 0 µs")
        self.end_time_label = QLabel("End Time: 100 µs")
        self.tolerance_label = QLabel("Tolerance: 10 dB")

        # Create the export button
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_data)

        # Create the open CSV button
        self.open_button = QPushButton("Open CSV")
        self.open_button.clicked.connect(self.open_csv)

        # Add widgets to the layout
        layout.addWidget(self.plot_widget_time)
        layout.addWidget(self.start_time_label)
        layout.addWidget(self.start_time_slider)
        layout.addWidget(self.end_time_label)
        layout.addWidget(self.end_time_slider)
        layout.addWidget(self.tolerance_label)
        layout.addWidget(self.tolerance_slider)
        layout.addWidget(self.plot_widget_fft)
        layout.addWidget(self.export_button)  # Add the export button to the layout
        layout.addWidget(self.open_button)  # Add the open CSV button to the layout
        layout.addWidget(self.toggle_button)  # Add the toggle button to the layout

        # Set the layout to the central widget
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Load, filter, and plot the data
        self.data = pd.DataFrame()  # Empty DataFrame initially
        self.data_filtered = pd.DataFrame()

        self.positive_freqs = np.array([])  # Placeholder for frequency data
        self.positive_magnitudes_dB = np.array([])  # Placeholder for magnitudes

        self.plot_mode = "FFT"  # Default mode

    def toggle_plot(self):
        """Toggle between PSD and FFT plotting."""
        if self.plot_mode == "FFT":
            self.plot_mode = "PSD"
            self.toggle_button.setText("Show FFT")
        else:
            self.plot_mode = "FFT"
            self.toggle_button.setText("Show PSD")

        # Update the plot with the current mode
        self.update_plot()

    def load_data(self, file_path):
        try:
            data = pd.read_csv(file_path)

            # Check if the time data is monotonic
            if not data['Time [microseconds]'].is_monotonic_increasing:
                print("Warning: Time data is not monotonic. Sorting the data might be affecting the interpretation.")

            data = data.sort_values(by='Time [microseconds]')
            return data
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame()

    def plot_time_domain(self, data):
        time = data['Time [microseconds]'].to_numpy()
        x_accel = data['X Acceleration'].to_numpy()
        y_accel = data['Y Acceleration'].to_numpy()
        z_accel = data['Z Acceleration'].to_numpy()

        self.plot_widget_time.clear()

        pen1 = pg.mkPen(color='#2541B2')
        pen2 = pg.mkPen(color='#1768AC')
        pen3 = pg.mkPen(color='#06BEE1')

        self.plot_widget_time.plot(time, x_accel, pen=pen1, name='X Acceleration')
        self.plot_widget_time.plot(time, y_accel, pen=pen2, name='Y Acceleration')
        self.plot_widget_time.plot(time, z_accel, pen=pen3, name='Z Acceleration')

        self.plot_widget_time.addLegend()
        self.plot_widget_time.setLabel('left', 'Acceleration (m/s²)')
        self.plot_widget_time.setLabel('bottom', 'Time (microseconds)')
        self.plot_widget_time.setTitle("Filtered Accelerometer Data (Time Domain)")

    def open_csv(self):
        """Open a file dialog to select and load a CSV file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")

        if file_path:
            self.data = self.load_data(file_path)
            self.data_filtered = self.filter_data(self.data)

            if not self.data_filtered.empty:
                self.setup_sliders()
                self.plot_time_domain(self.data_filtered)

                default_tolerance = self.tolerance_slider.value()
                self.plot_frequency_domain(self.data_filtered,
                                           self.start_time_slider.value(),
                                           self.end_time_slider.value(),
                                           default_tolerance)
            else:
                print("No data available after filtering.")

    def filter_data(self, data):
        if data.empty:
            return data

        percentiles = {
            'time': data['Time [microseconds]'].quantile([0.005, 0.995]),
            'x_accel': data['X Acceleration'].quantile([0.005, 0.995]),
            'y_accel': data['Y Acceleration'].quantile([0.005, 0.995]),
            'z_accel': data['Z Acceleration'].quantile([0.005, 0.995]),
        }

        data_filtered = data[
            (data['Time [microseconds]'] >= percentiles['time'].iloc[0]) &
            (data['Time [microseconds]'] <= percentiles['time'].iloc[1]) &
            (data['X Acceleration'] >= percentiles['x_accel'].iloc[0]) &
            (data['X Acceleration'] <= percentiles['x_accel'].iloc[1]) &
            (data['Y Acceleration'] >= percentiles['y_accel'].iloc[0]) &
            (data['Y Acceleration'] <= percentiles['y_accel'].iloc[1]) &
            (data['Z Acceleration'] >= percentiles['z_accel'].iloc[0]) &
            (data['Z Acceleration'] <= percentiles['z_accel'].iloc[1])
            ]

        return data_filtered

    def setup_sliders(self):
        """Setup the sliders based on the filtered data."""
        time_values = self.data_filtered['Time [microseconds]'].to_numpy()

        # Set the maximum values based on the actual time range
        self.start_time_slider.setRange(0, len(time_values) - 1)
        self.end_time_slider.setRange(0, len(time_values) - 1)

        # Set default values based on the data length
        self.start_time_slider.setValue(0)
        self.end_time_slider.setValue(len(time_values) - 1)

        self.update_labels()

    def update_labels(self):
        """Update the labels to show actual time values and tolerance."""
        start_index = self.start_time_slider.value()
        end_index = self.end_time_slider.value()

        # Get the actual time values based on indices
        start_time = self.data_filtered['Time [microseconds]'].iloc[start_index]
        end_time = self.data_filtered['Time [microseconds]'].iloc[end_index]

        tolerance_value = self.tolerance_slider.value()

        self.start_time_label.setText(f"Start Time: {start_time:.2f} µs")
        self.end_time_label.setText(f"End Time: {end_time:.2f} µs")
        self.tolerance_label.setText(f"Tolerance: {tolerance_value} dB")

    def update_plot(self):
        """Update the FFT or PSD plot based on the sliders."""
        self.update_labels()
        start_index = self.start_time_slider.value()
        end_index = self.end_time_slider.value()
        tolerance_value = self.tolerance_slider.value()

        if start_index < end_index:
            if self.plot_mode == "FFT":
                self.plot_frequency_domain(self.data_filtered, start_index, end_index, tolerance_value)
            else:  # If the mode is PSD
                self.plot_frequency_domain(self.data_filtered, start_index, end_index, tolerance_value, mode='PSD')
        else:
            print("Start index must be less than end index.")

    def plot_frequency_domain(self, data, start_index, end_index, tolerance, mode='FFT'):
        z_accel = data['Z Acceleration'].to_numpy()[start_index:end_index]
        time = data['Time [microseconds]'].to_numpy()[start_index:end_index]

        print(len(z_accel))

        N = len(z_accel)
        if N < 2:  # FFT requires at least 2 points
            print("Not enough data points for FFT.")
            return

        dt = np.mean(np.diff(time)) * 1e-6  # Mean time difference in seconds
        freq = np.fft.fftfreq(N, dt)
        fft_z_accel = np.fft.fft(z_accel)

        print(f"dt (sampling interval in seconds): {dt}")
        print(f"Max frequency (Nyquist): {1 / (2 * dt)} Hz")

        # Calculate Power Spectral Density (PSD)
        psd = (np.abs(fft_z_accel) ** 2) / (N * dt)  # Power normalization
        self.positive_freqs = freq[:N // 2]
        self.positive_psd = psd[:N // 2]  # Take only the positive frequencies

        # Clear previous plot
        self.plot_widget_fft.clear()

        pen4 = pg.mkPen(color='#F7F5FB')

        # Check the mode and plot accordingly
        if mode == 'PSD':
            self.plot_widget_fft.plot(self.positive_freqs, 10 * np.log10(self.positive_psd), pen=pen4)  # Convert to dB
            self.plot_widget_fft.setLabel('left', 'PSD (dB/Hz)')
            self.plot_widget_fft.setTitle("Power Spectral Density of Z Acceleration (Frequency Domain)")
        else:  # FFT mode
            magnitudes = np.abs(fft_z_accel)[:N // 2]
            self.plot_widget_fft.plot(self.positive_freqs, magnitudes, pen=pen4)  # Plot FFT magnitudes
            self.plot_widget_fft.setLabel('left', 'Magnitude')
            self.plot_widget_fft.setTitle("FFT of Z Acceleration (Frequency Domain)")

        # Identify natural frequencies based on tolerance
        peaks, _ = find_peaks(10 * np.log10(self.positive_psd), height=tolerance)
        natural_frequencies = self.positive_freqs[peaks]
        print(f"Natural Frequencies: {natural_frequencies}")

    def export_data(self):
        """Export the trimmed data based on slider selection to a CSV file."""
        start_index = self.start_time_slider.value()
        end_index = self.end_time_slider.value()

        # Ensure the indices are in a valid range
        if start_index >= end_index:
            print("Invalid time range selected. Start index must be less than end index.")
            return

        # Select the data within the chosen range
        trimmed_data = self.data_filtered.iloc[start_index:end_index]

        # Combine frequency data with time-domain data
        freq_data = pd.DataFrame({
            'Frequency (Hz)': self.positive_freqs,
            'Magnitude (dB)': self.positive_magnitudes_dB
        })

        # Open a file dialog to select the location to save the CSV
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")

        if file_path:
            try:
                # Save the time-domain data to a sheet
                trimmed_data.to_csv(file_path, index=False)

                # Save frequency-domain data to a new sheet
                freq_data.to_csv(file_path.replace(".csv", "_frequency.csv"), index=False)

                print(f"Data successfully exported to {file_path}")
            except Exception as e:
                print(f"Failed to export data: {e}")


def main():
    app = QApplication(sys.argv)

    # Load the stylesheet
    with open("Preferences/style_dark.qss", "r") as style_file:
        app.setStyleSheet(style_file.read())

    main_win = SensorPlot()
    main_win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
