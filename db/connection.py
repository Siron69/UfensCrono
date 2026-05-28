import sqlite3
import os
from utils.paths import get_data_dir, get_db_path
from db.migrations import run_migrations

_connection: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'backup'), exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'export'), exist_ok=True)

        conn = sqlite3.connect(get_db_path(), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn)
        _connection = conn
    return _connection


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
