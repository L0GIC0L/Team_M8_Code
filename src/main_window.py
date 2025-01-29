import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QTabWidget,QToolTip
from PySide6.QtGui import QFont

from csv_combiner_tab import CSVCombinerWidget
from fft_analysis_tab import PlotFFT
from serial_plotter_tab import SerialPlotterTab
from settings_tab import Settings, load_stylesheet

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Team M8 Frequency Analyzer")
        self.setGeometry(10, 10, 1280, 720)

        self.tab_widget = QTabWidget()

        # Add Serial Plotter tab
        self.plot_serial = SerialPlotterTab()
        self.tab_widget.addTab(self.plot_serial, "Serial Plotter")

        # Add Sensor Data Plot tab
        self.plot_fft = PlotFFT()  # Assuming PlotFFT is defined elsewhere
        self.tab_widget.addTab(self.plot_fft, "Sensor Data Plot")

        # Add CSV Combiner tab
        self.csvcombiner = CSVCombinerWidget()
        self.tab_widget.addTab(self.csvcombiner, "CSV Combiner")

        # Add Settings tab
        self.settings = Settings(self.plot_fft, self.plot_serial)  # Assuming Settings is defined elsewhere
        self.tab_widget.addTab(self.settings, "Settings")

        self.setCentralWidget(self.tab_widget)

        # Enhance UI with tooltips
        self._set_tooltips()

        # Apply stylesheet
        self.load_stylesheet("style_dark")

    def _set_tooltips(self):
        QToolTip.setFont(QFont('SansSerif', 10))
        self.tab_widget.setTabToolTip(0, "Monitor and plot serial data")
        self.tab_widget.setTabToolTip(1, "Plot sensor data with FFT analysis")
        self.tab_widget.setTabToolTip(2, "Combine CSV files for analysis")
        self.tab_widget.setTabToolTip(3, "Adjust settings for plot configurations")

    def load_stylesheet(self, style_name):
        # Assuming load_stylesheet function is defined elsewhere
        try:
            load_stylesheet(QApplication.instance(), style_name)
        except Exception as e:
            print(f"Error loading stylesheet: {e}")


# Main application entry
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

