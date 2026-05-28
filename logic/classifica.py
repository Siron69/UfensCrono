from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from utils.tempo import ms_to_str, str_to_ms


@dataclass
class RigaClassifica:
    iscrizione_id: int
    risultato_id: Optional[int]
    pettorale: str
    nome: str
    cognome: str
    sesso: str
    categoria: str
    tempo_ms: Optional[int]
    tempo_override: Optional[str]
    stato: str          # ok / dsq / dnf / dns / ''
    ordine_arrivo: Optional[int]
    pos_assoluta: Optional[int] = None
    pos_sesso: Optional[int] = None
    pos_categoria: Optional[int] = None

    @property
    def tempo_effettivo_ms(self) -> Optional[int]:
        if self.tempo_override:
            return str_to_ms(self.tempo_override)
        return self.tempo_ms

    @property
    def tempo_display(self) -> str:
        ms = self.tempo_effettivo_ms
        return ms_to_str(ms) if ms is not None else "—"

    @property
    def nome_atleta(self) -> str:
        return f"{self.cognome} {self.nome}".strip()


def from_row(row: sqlite3.Row) -> RigaClassifica:
    return RigaClassifica(
        iscrizione_id=row['iscrizione_id'],
        risultato_id=row['risultato_id'],
        pettorale=row['pettorale'] or "",
        nome=row['atleta_nome'] or "",
        cognome=row['atleta_cognome'] or "",
        sesso=row['atleta_sesso'] or "",
        categoria=row['categoria'] or "",
        tempo_ms=row['tempo_ms'],
        tempo_override=row['tempo_override'],
        stato=row['stato'] or "",
        ordine_arrivo=row['ordine_arrivo'],
    )


def _sort_key(r: RigaClassifica):
    t = r.tempo_effettivo_ms
    is_ok = r.stato in ("ok", "")
    if is_ok and t is not None:
        return (0, t)
    if is_ok:
        return (1, 0)
    return (2, 0)


def calcola_classifica(righe: list[RigaClassifica]) -> list[RigaClassifica]:
    righe.sort(key=_sort_key)

    pos_assoluta = 1
    pos_per_sesso: dict[str, int] = {}
    pos_per_cat: dict[str, int] = {}

    for r in righe:
        if r.stato in ("ok", "") and r.tempo_effettivo_ms is not None:
            r.pos_assoluta = pos_assoluta
            pos_assoluta += 1

            sk = r.sesso.upper()
            pos_per_sesso[sk] = pos_per_sesso.get(sk, 0) + 1
            r.pos_sesso = pos_per_sesso[sk]

            ck = r.categoria
            pos_per_cat[ck] = pos_per_cat.get(ck, 0) + 1
            r.pos_categoria = pos_per_cat[ck]
        else:
            r.pos_assoluta = None
            r.pos_sesso = None
            r.pos_categoria = None

    return righe
