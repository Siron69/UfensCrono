import sqlite3
from typing import Optional
from models.atleta import Atleta

_SELECT = """
    SELECT id, nome, cognome, sesso, data_nascita, luogo_nascita,
           nazionalita, codice_fiscale, societa, codice_societa,
           tessera, tessera2, ente, categoria, scad_certificato,
           stato_cert, telefono, cellulare, email, note,
           source_id, source_order_id, created_at, updated_at
    FROM atleti
"""


def _to_atleta(row: sqlite3.Row) -> Atleta:
    return Atleta(
        id=row['id'],
        nome=row['nome'],
        cognome=row['cognome'],
        sesso=row['sesso'],
        data_nascita=row['data_nascita'],
        luogo_nascita=row['luogo_nascita'],
        nazionalita=row['nazionalita'] or 'ITA',
        codice_fiscale=row['codice_fiscale'],
        societa=row['societa'],
        codice_societa=row['codice_societa'],
        tessera=row['tessera'],
        tessera2=row['tessera2'],
        ente=row['ente'],
        categoria=row['categoria'],
        scad_certificato=row['scad_certificato'],
        stato_cert=row['stato_cert'],
        telefono=row['telefono'],
        cellulare=row['cellulare'],
        email=row['email'],
        note=row['note'],
        source_id=row['source_id'],
        source_order_id=row['source_order_id'],
        created_at=row['created_at'],
        updated_at=row['updated_at'],
    )


def get_all(conn: sqlite3.Connection, search: str = "", sesso: str = "") -> list[Atleta]:
    params: list = []
    where: list[str] = []

    if search:
        where.append("(cognome LIKE ? OR nome LIKE ? OR societa LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if sesso in ('M', 'F'):
        where.append("sesso = ?")
        params.append(sesso)

    sql = _SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY cognome, nome"

    return [_to_atleta(r) for r in conn.execute(sql, params).fetchall()]


def get_by_id(conn: sqlite3.Connection, atleta_id: int) -> Optional[Atleta]:
    row = conn.execute(_SELECT + " WHERE id = ?", (atleta_id,)).fetchone()
    return _to_atleta(row) if row else None


def has_iscrizioni(conn: sqlite3.Connection, atleta_id: int) -> bool:
    n = conn.execute(
        "SELECT COUNT(*) FROM iscrizioni WHERE atleta_id = ?", (atleta_id,)
    ).fetchone()[0]
    return n > 0


def insert(conn: sqlite3.Connection, atleta: Atleta) -> int:
    cur = conn.execute(
        """INSERT INTO atleti (nome, cognome, sesso, data_nascita, luogo_nascita,
               nazionalita, codice_fiscale, societa, codice_societa, tessera,
               tessera2, ente, categoria, scad_certificato, stato_cert,
               telefono, cellulare, email, note)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (atleta.nome, atleta.cognome, atleta.sesso, atleta.data_nascita,
         atleta.luogo_nascita, atleta.nazionalita, atleta.codice_fiscale,
         atleta.societa, atleta.codice_societa, atleta.tessera, atleta.tessera2,
         atleta.ente, atleta.categoria, atleta.scad_certificato, atleta.stato_cert,
         atleta.telefono, atleta.cellulare, atleta.email, atleta.note),
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, atleta: Atleta) -> None:
    conn.execute(
        """UPDATE atleti SET nome=?, cognome=?, sesso=?, data_nascita=?,
               luogo_nascita=?, nazionalita=?, codice_fiscale=?, societa=?,
               codice_societa=?, tessera=?, tessera2=?, ente=?, categoria=?,
               scad_certificato=?, stato_cert=?, telefono=?, cellulare=?,
               email=?, note=?, updated_at=datetime('now')
           WHERE id=?""",
        (atleta.nome, atleta.cognome, atleta.sesso, atleta.data_nascita,
         atleta.luogo_nascita, atleta.nazionalita, atleta.codice_fiscale,
         atleta.societa, atleta.codice_societa, atleta.tessera, atleta.tessera2,
         atleta.ente, atleta.categoria, atleta.scad_certificato, atleta.stato_cert,
         atleta.telefono, atleta.cellulare, atleta.email, atleta.note,
         atleta.id),
    )
    conn.commit()


def delete(conn: sqlite3.Connection, atleta_id: int) -> None:
    conn.execute("DELETE FROM atleti WHERE id = ?", (atleta_id,))
    conn.commit()
