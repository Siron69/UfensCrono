import sys
import os


def get_resource_path(relative_path: str) -> str:
    """Percorso assoluto a un file risorsa (funziona sia in sviluppo che nel .exe PyInstaller).

    In sviluppo:  <project_root>/<relative_path>
    In .exe:      <sys._MEIPASS>/<relative_path>
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    return os.path.normpath(os.path.join(base, relative_path))


def get_data_dir() -> str:
    """
    Restituisce il percorso della cartella 'data/'.
    In sviluppo:  <project_root>/data/
    In .exe:      <cartella_exe>/data/
    """
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
        base = os.path.join(base, '..')
    return os.path.normpath(os.path.join(base, 'data'))


def get_db_path() -> str:
    return os.path.join(get_data_dir(), 'ufenscrono.db')


def get_backup_dir() -> str:
    return os.path.join(get_data_dir(), 'backup')


def get_export_dir() -> str:
    return os.path.join(get_data_dir(), 'export')
