import sys
from PyQt6.QtWidgets import QApplication
from db.connection import get_connection, close_connection
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    get_connection()

    win = MainWindow()
    win.show()

    result = app.exec()
    close_connection()
    sys.exit(result)


if __name__ == '__main__':
    main()
