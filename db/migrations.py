import sqlite3
import os
import glob

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version INTEGER NOT NULL
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM _schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO _schema_version (version) VALUES (0)")
    conn.commit()


def get_version(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT version FROM _schema_version").fetchone()[0]


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute("UPDATE _schema_version SET version = ?", (version,))
    conn.commit()


def run_migrations(conn: sqlite3.Connection) -> None:
    _ensure_version_table(conn)
    current = get_version(conn)

    pattern = os.path.join(_MIGRATIONS_DIR, '*.sql')
    files = sorted(glob.glob(pattern))

    for path in files:
        filename = os.path.basename(path)
        try:
            number = int(filename.split('_')[0])
        except ValueError:
            continue
        if number <= current:
            continue
        with open(path, 'r', encoding='utf-8') as f:
            sql = f.read()
        conn.executescript(sql)
        _set_version(conn, number)
