import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOverrideCursor(QCursor(Qt.CursorShape.ArrowCursor))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
