import sqlite3
from typing import Optional
from models.risultato import Risultato

_SELECT = """
    SELECT r.id, r.iscrizione_id, r.tempo_ms, r.tempo_override,
           r.stato, r.ordine_arrivo, r.note_arbitro, r.updated_at,
           a.nome AS atleta_nome, a.cognome AS atleta_cognome,
           a.sesso AS atleta_sesso, a.data_nascita AS atleta_data_nascita,
           i.pettorale,
           COALESCE(i.categoria_override, i.categoria_calc) AS categoria_effettiva
    FROM risultati r
    JOIN iscrizioni i ON i.id = r.iscrizione_id
    JOIN atleti a     ON a.id = i.atleta_id
"""


def _to_risultato(row: sqlite3.Row) -> Risultato:
    return Risultato(
        id=row['id'], iscrizione_id=row['iscrizione_id'],
        tempo_ms=row['tempo_ms'], tempo_override=row['tempo_override'],
        stato=row['stato'], ordine_arrivo=row['ordine_arrivo'],
        note_arbitro=row['note_arbitro'], updated_at=row['updated_at'],
        atleta_nome=row['atleta_nome'], atleta_cognome=row['atleta_cognome'],
        atleta_sesso=row['atleta_sesso'],
        atleta_data_nascita=row['atleta_data_nascita'],
        pettorale=row['pettorale'],
        categoria_effettiva=row['categoria_effettiva'],
    )


def get_arrivi(conn: sqlite3.Connection, gara_id: int) -> list[Risultato]:
    rows = conn.execute(
        _SELECT + " WHERE i.gara_id = ? ORDER BY r.ordine_arrivo ASC",
        (gara_id,)
    ).fetchall()
    return [_to_risultato(r) for r in rows]


def get_ultimo_arrivo(conn: sqlite3.Connection, gara_id: int) -> Optional[Risultato]:
    row = conn.execute(
        _SELECT + " WHERE i.gara_id = ? ORDER BY r.ordine_arrivo DESC LIMIT 1",
        (gara_id,)
    ).fetchone()
    return _to_risultato(row) if row else None


def count_arrivi(conn: sqlite3.Connection, gara_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM risultati r JOIN iscrizioni i ON i.id=r.iscrizione_id WHERE i.gara_id=?",
        (gara_id,)
    ).fetchone()[0]


def insert_arrivo(
    conn: sqlite3.Connection,
    iscrizione_id: int,
    tempo_ms: int,
    ordine_arrivo: int,
) -> int:
    cur = conn.execute(
        "INSERT INTO risultati (iscrizione_id, tempo_ms, ordine_arrivo) VALUES (?,?,?)",
        (iscrizione_id, tempo_ms, ordine_arrivo),
    )
    conn.commit()
    return cur.lastrowid


def delete_by_id(conn: sqlite3.Connection, risultato_id: int) -> None:
    conn.execute("DELETE FROM risultati WHERE id = ?", (risultato_id,))
    conn.commit()


def get_iscritti_arrivati_ids(conn: sqlite3.Connection, gara_id: int) -> set[int]:
    rows = conn.execute(
        """SELECT r.iscrizione_id FROM risultati r
           JOIN iscrizioni i ON i.id = r.iscrizione_id
           WHERE i.gara_id = ?""",
        (gara_id,)
    ).fetchall()
    return {r['iscrizione_id'] for r in rows}
