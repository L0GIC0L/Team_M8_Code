import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    try:
        # Initialize and show the main window
        main_window = MainWindow()
        main_window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"An unexpected error occurred while starting the application: {e}")

if __name__ == "__main__":
    main()
