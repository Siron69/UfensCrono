import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from db.connection import get_connection, close_connection
from ui.main_window import MainWindow
from utils.paths import get_resource_path


def _set_windows_app_id() -> None:
    """Imposta l'AppUserModelID su Windows.

    Senza questa chiamata, Windows associa la finestra al processo python.exe
    e mostra la sua icona nella barra delle applicazioni invece di quella dell'app.
    Deve essere chiamata PRIMA di creare QApplication.
    """
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            'Ufens.UfensCrono.1'
        )
    except Exception:
        pass   # Non-Windows o ctypes non disponibile


def main() -> None:
    _set_windows_app_id()   # deve stare PRIMA di QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Usa il file .ico (multi-risoluzione: 16/32/48/256 px) per una resa
    # ottimale nella taskbar e nella title bar di Windows.
    # Fallback al PNG se l'ICO non fosse presente.
    ico_path = get_resource_path('ui/media/logoUfens.ico')
    png_path = get_resource_path('ui/media/logoUfens.png')
    import os
    icon = QIcon(ico_path if os.path.exists(ico_path) else png_path)
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
