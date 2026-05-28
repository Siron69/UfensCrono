import sqlite3
from typing import Optional
from models.gara import Gara, Iscrizione, Categoria

# ── Gare ────────────────────────────────────────────────────────────────────

_SELECT_GARA = """
    SELECT id, evento_id, nome, tipo, distanza_m, stato,
           start_ts, start_wall, note, created_at
    FROM gare
"""


def _to_gara(row: sqlite3.Row) -> Gara:
    return Gara(
        id=row['id'], evento_id=row['evento_id'], nome=row['nome'],
        tipo=row['tipo'], distanza_m=row['distanza_m'], stato=row['stato'],
        start_ts=row['start_ts'], start_wall=row['start_wall'],
        note=row['note'], created_at=row['created_at'],
    )


def get_by_evento(conn: sqlite3.Connection, evento_id: int) -> list[Gara]:
    rows = conn.execute(
        _SELECT_GARA + " WHERE evento_id = ? ORDER BY created_at", (evento_id,)
    ).fetchall()
    return [_to_gara(r) for r in rows]


def get_by_id(conn: sqlite3.Connection, gara_id: int) -> Optional[Gara]:
    row = conn.execute(_SELECT_GARA + " WHERE id = ?", (gara_id,)).fetchone()
    return _to_gara(row) if row else None


def count_iscritti(conn: sqlite3.Connection, gara_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM iscrizioni WHERE gara_id = ?", (gara_id,)
    ).fetchone()[0]


def insert(conn: sqlite3.Connection, gara: Gara) -> int:
    cur = conn.execute(
        """INSERT INTO gare (evento_id, nome, tipo, distanza_m, note)
           VALUES (?,?,?,?,?)""",
        (gara.evento_id, gara.nome, gara.tipo, gara.distanza_m, gara.note),
    )
    conn.commit()
    return cur.lastrowid


def update(conn: sqlite3.Connection, gara: Gara) -> None:
    conn.execute(
        """UPDATE gare SET nome=?, tipo=?, distanza_m=?, note=? WHERE id=?""",
        (gara.nome, gara.tipo, gara.distanza_m, gara.note, gara.id),
    )
    conn.commit()


def delete(conn: sqlite3.Connection, gara_id: int) -> None:
    conn.execute("DELETE FROM gare WHERE id = ?", (gara_id,))
    conn.commit()


def avvia_gara(conn: sqlite3.Connection, gara_id: int, start_ts: float, start_wall: str) -> None:
    conn.execute(
        "UPDATE gare SET stato='in_corso', start_ts=?, start_wall=? WHERE id=?",
        (start_ts, start_wall, gara_id),
    )
    conn.commit()


def concludi_gara(conn: sqlite3.Connection, gara_id: int) -> None:
    conn.execute("UPDATE gare SET stato='conclusa' WHERE id=?", (gara_id,))
    conn.commit()


# ── Iscrizioni ───────────────────────────────────────────────────────────────

_SELECT_ISCR = """
    SELECT i.id, i.gara_id, i.atleta_id, i.pettorale, i.pettorale_circ,
           i.codice_chip, i.quota, i.stato_lw,
           i.categoria_calc, i.categoria_override, i.partecipa,
           a.nome AS atleta_nome, a.cognome AS atleta_cognome,
           a.sesso AS atleta_sesso, a.data_nascita AS atleta_data_nascita,
           a.societa AS atleta_societa
    FROM iscrizioni i
    JOIN atleti a ON a.id = i.atleta_id
"""


def _to_iscrizione(row: sqlite3.Row) -> Iscrizione:
    return Iscrizione(
        id=row['id'], gara_id=row['gara_id'], atleta_id=row['atleta_id'],
        pettorale=row['pettorale'], pettorale_circ=row['pettorale_circ'],
        codice_chip=row['codice_chip'], quota=row['quota'],
        stato_lw=row['stato_lw'],
        categoria_calc=row['categoria_calc'],
        categoria_override=row['categoria_override'],
        partecipa=row['partecipa'],
        atleta_nome=row['atleta_nome'], atleta_cognome=row['atleta_cognome'],
        atleta_sesso=row['atleta_sesso'],
        atleta_data_nascita=row['atleta_data_nascita'],
        atleta_societa=row['atleta_societa'],
    )


def get_iscrizioni(conn: sqlite3.Connection, gara_id: int) -> list[Iscrizione]:
    rows = conn.execute(
        _SELECT_ISCR + " WHERE i.gara_id = ? ORDER BY CAST(i.pettorale AS INTEGER), i.pettorale",
        (gara_id,)
    ).fetchall()
    return [_to_iscrizione(r) for r in rows]


def get_iscrizione_by_id(conn: sqlite3.Connection, iscr_id: int) -> Optional[Iscrizione]:
    row = conn.execute(_SELECT_ISCR + " WHERE i.id = ?", (iscr_id,)).fetchone()
    return _to_iscrizione(row) if row else None


def next_pettorale(conn: sqlite3.Connection, gara_id: int) -> str:
    rows = conn.execute(
        "SELECT pettorale FROM iscrizioni WHERE gara_id = ?", (gara_id,)
    ).fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r['pettorale']))
        except ValueError:
            pass
    return str(max(nums) + 1) if nums else "1"


def next_pettorale_evento(conn: sqlite3.Connection, evento_id: int) -> str:
    """Prossimo numero pettorale libero considerando tutte le gare dell'evento."""
    rows = conn.execute(
        """SELECT i.pettorale FROM iscrizioni i
           JOIN gare g ON g.id = i.gara_id
           WHERE g.evento_id = ?""",
        (evento_id,),
    ).fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(r['pettorale']))
        except ValueError:
            pass
    return str(max(nums) + 1) if nums else "1"


def get_pettorale_conflitto(
    conn: sqlite3.Connection,
    evento_id: int,
    pettorale: str,
    exclude_gara_id: Optional[int] = None,
) -> Optional[str]:
    """Controlla se il pettorale è già usato in un'altra gara dello stesso evento.

    Returns:
        Nome della gara in cui è già usato, oppure None se il pettorale è libero.
    """
    q = """
        SELECT g.nome FROM iscrizioni i
        JOIN gare g ON g.id = i.gara_id
        WHERE g.evento_id = ? AND i.pettorale = ?
    """
    params: list = [evento_id, pettorale]
    if exclude_gara_id is not None:
        q += " AND g.id != ?"
        params.append(exclude_gara_id)
    row = conn.execute(q, params).fetchone()
    return row['nome'] if row else None


def add_iscrizione(
    conn: sqlite3.Connection,
    gara_id: int,
    atleta_id: int,
    pettorale: str,
    categoria_calc: Optional[str] = None,
    categoria_override: Optional[str] = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO iscrizioni (gara_id, atleta_id, pettorale, categoria_calc, categoria_override)
           VALUES (?,?,?,?,?)""",
        (gara_id, atleta_id, pettorale, categoria_calc, categoria_override),
    )
    conn.commit()
    return cur.lastrowid


def update_iscrizione(conn: sqlite3.Connection, iscr: Iscrizione) -> None:
    conn.execute(
        """UPDATE iscrizioni SET pettorale=?, categoria_override=? WHERE id=?""",
        (iscr.pettorale, iscr.categoria_override, iscr.id),
    )
    conn.commit()


def remove_iscrizione(conn: sqlite3.Connection, iscr_id: int) -> None:
    conn.execute("DELETE FROM iscrizioni WHERE id = ?", (iscr_id,))
    conn.commit()


def atleti_iscritti_ids(conn: sqlite3.Connection, gara_id: int) -> set[int]:
    rows = conn.execute(
        "SELECT atleta_id FROM iscrizioni WHERE gara_id = ?", (gara_id,)
    ).fetchall()
    return {r['atleta_id'] for r in rows}


# ── Categorie ────────────────────────────────────────────────────────────────

_SELECT_CAT = "SELECT id, gara_id, nome, sesso, eta_min, eta_max, ordine FROM categorie"


def _to_categoria(row: sqlite3.Row) -> Categoria:
    return Categoria(
        id=row['id'], gara_id=row['gara_id'], nome=row['nome'],
        sesso=row['sesso'], eta_min=row['eta_min'],
        eta_max=row['eta_max'], ordine=row['ordine'],
    )


def get_categorie(conn: sqlite3.Connection, gara_id: int) -> list[Categoria]:
    rows = conn.execute(
        _SELECT_CAT + " WHERE gara_id = ? ORDER BY ordine, nome", (gara_id,)
    ).fetchall()
    return [_to_categoria(r) for r in rows]


def insert_categoria(conn: sqlite3.Connection, cat: Categoria) -> int:
    cur = conn.execute(
        "INSERT INTO categorie (gara_id, nome, sesso, eta_min, eta_max, ordine) VALUES (?,?,?,?,?,?)",
        (cat.gara_id, cat.nome, cat.sesso, cat.eta_min, cat.eta_max, cat.ordine),
    )
    conn.commit()
    return cur.lastrowid


def update_categoria(conn: sqlite3.Connection, cat: Categoria) -> None:
    conn.execute(
        "UPDATE categorie SET nome=?, sesso=?, eta_min=?, eta_max=?, ordine=? WHERE id=?",
        (cat.nome, cat.sesso, cat.eta_min, cat.eta_max, cat.ordine, cat.id),
    )
    conn.commit()


def delete_categoria(conn: sqlite3.Connection, cat_id: int) -> None:
    conn.execute("DELETE FROM categorie WHERE id = ?", (cat_id,))
    conn.commit()
