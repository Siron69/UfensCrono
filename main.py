import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from db.connection import get_connection, close_connection
from ui.main_window import MainWindow
from utils.paths import get_resource_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Icona su tutta l'applicazione (barra delle applicazioni Windows + title bar)
    icon = QIcon(get_resource_path('ui/media/logoUfens.png'))
    app.setWindowIcon(icon)

    get_connection()

    win = MainWindow()
    win.setWindowIcon(icon)   # assicura l'icona anche sulla finestra principale
    win.show()

    result = app.exec()
    close_connection()
    sys.exit(result)


if __name__ == '__main__':
    main()
