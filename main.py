import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from src.ui.main_window import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("interview_cracker.log"),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
