import sys

from PySide6.QtWidgets import QMainWindow, QApplication, QTabWidget

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
        self.plot_serial = SerialPlotterTab()
        self.tab_widget.addTab(self.plot_serial, "Serial Plotter")

        # Add SensorPlot tab
        self.plot_fft = PlotFFT()  # Assuming PlotFFT is defined elsewhere
        self.tab_widget.addTab(self.plot_fft, "Sensor Data Plot")

        # Add CSV combiner tab
        self.csvcombiner = CSVCombinerWidget()
        self.tab_widget.addTab(self.csvcombiner, "CSV Combiner")

        # Add Settings tab
        self.settings = Settings(self.plot_fft,self.plot_serial)  # Assuming PlotFFT is defined elsewhere
        self.tab_widget.addTab(self.settings, "Settings")

        self.setCentralWidget(self.tab_widget)

        load_stylesheet(QApplication.instance(),"style_dark")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
