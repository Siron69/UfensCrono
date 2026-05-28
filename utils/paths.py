import sys
import os


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
