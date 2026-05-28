import sqlite3
from typing import Optional
from models.evento import Evento

_SELECT = """
    SELECT id, nome, data, luogo, note, created_at
    FROM eventi
"""


def _to_evento(row: sqlite3.Row) -> Evento:
    return Evento(
        id=row['id'],
        nome=row['nome'],
        data=row['data'],
        luogo=row['luogo'],
        note=row['note'],
        created_at=row['created_at'],
    )


def get_all(conn: sqlite3.Connection) -> list[Evento]:
    rows = conn.execute(_SELECT + " ORDER BY data DESC, nome").fetchall()
    return [_to_evento(r) for r in rows]


def get_by_id(conn: sqlite3.Connection, evento_id: int) -> Optional[Evento]:
    row = conn.execute(_SELECT + " WHERE id = ?", (evento_id,)).fetchone()
    return _to_evento(row) if row else None


def has_gare(conn: sqlite3.Connection, evento_id: int) -> bool:
    n = conn.execute(
        "SELECT COUNT(*) FROM gare WHERE evento_id = ?", (evento_id,)
    ).fetchone()[0]
    return n > 0


def insert(conn: sqlite3.Connection, evento: Evento) -> int:
    cur = conn.execute(
        "INSERT INTO eventi (nome, data, luogo, note) VALUES (?,?,?,?)",
        (evento.nome, evento.data, evento.luogo, evento.note),
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, evento: Evento) -> None:
    conn.execute(
        "UPDATE eventi SET nome=?, data=?, luogo=?, note=? WHERE id=?",
        (evento.nome, evento.data, evento.luogo, evento.note, evento.id),
    )
    conn.commit()


def delete(conn: sqlite3.Connection, evento_id: int) -> None:
    conn.execute("DELETE FROM eventi WHERE id = ?", (evento_id,))
    conn.commit()
