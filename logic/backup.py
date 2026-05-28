import os
import shutil
from datetime import datetime

from utils.paths import get_db_path, get_backup_dir


def crea_backup(nome_gara: str) -> str:
    """Copia il DB nella cartella backup e restituisce il percorso del file creato."""
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_safe = nome_gara.replace(' ', '_').replace('/', '-')[:40]
    dest = os.path.join(backup_dir, f"{nome_safe}_{ts}.db")
    shutil.copy2(get_db_path(), dest)
    return dest
