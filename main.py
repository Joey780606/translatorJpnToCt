# 程式進入點

import sys
from PySide6.QtWidgets import QApplication
from MainWindow import MainWindow


if __name__ == "__main__":
    App = QApplication(sys.argv)
    Window = MainWindow()
    Window.show()
    sys.exit(App.exec())
