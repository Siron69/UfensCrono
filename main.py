import sys
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow
from db.connection import get_connection, close_connection
from db.migrations import get_version


def main() -> None:
    app = QApplication(sys.argv)

    conn = get_connection()
    version = get_version(conn)

    win = QMainWindow()
    win.setWindowTitle("UfensCrono")
    label = QLabel(f"DB pronto — schema v{version}")
    label.setContentsMargins(20, 20, 20, 20)
    win.setCentralWidget(label)
    win.resize(400, 120)
    win.show()

    result = app.exec()
    close_connection()
    sys.exit(result)


if __name__ == '__main__':
    main()
