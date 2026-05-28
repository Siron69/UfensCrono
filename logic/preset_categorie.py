"""Preset di categorie predefinite per una gara.

Uso::

    from logic.preset_categorie import genera_preset, PRESETS

    cats = genera_preset(gara_id=3, step=5)   # 5 a 5
    cats = genera_preset(gara_id=3, step=10)  # 10 a 10
"""

import math
from typing import Optional
from models.gara import Categoria


def _genera_fasce(
    step: int,
    inizio: int = 18,
    soglia_ultima: int = 80,
) -> list[tuple[int, Optional[int]]]:
    """Genera le fasce d'età con il passo indicato.

    La prima fascia parte da *inizio* e si estende fino al primo
    multiplo di *step* strettamente successivo (allineamento canonico):

        step=5,  inizio=18 → [(18,24), (25,29), (30,34), …, (75,79), (80,None)]
        step=10, inizio=18 → [(18,29), (30,39), (40,49), …, (70,79), (80,None)]

    L'ultima fascia è sempre aperta (eta_max=None → "80+").
    """
    fasce: list[tuple[int, Optional[int]]] = []

    # Primo confine allineato: il multiplo di step successivo a inizio
    # (math.ceil(18/5)+1)*5 = (4+1)*5 = 25  → prima fascia 18-24
    # (math.ceil(18/10)+1)*10 = (2+1)*10 = 30 → prima fascia 18-29
    first_aligned = (math.ceil(inizio / step) + 1) * step
    fasce.append((inizio, first_aligned - 1))

    eta = first_aligned
    while eta < soglia_ultima:
        fasce.append((eta, eta + step - 1))
        eta += step

    fasce.append((soglia_ultima, None))   # ultima fascia aperta (80+)
    return fasce


def _nome(sesso: str, eta_min: int, eta_max: Optional[int]) -> str:
    """Costruisce il nome della categoria, es. 'M25-29' oppure 'F80+'."""
    if eta_max is None:
        return f"{sesso}{eta_min}+"
    return f"{sesso}{eta_min}-{eta_max}"


def genera_preset(gara_id: int, step: int) -> list[Categoria]:
    """Restituisce la lista di Categoria per il preset richiesto.

    Args:
        gara_id: id della gara a cui assegnare le categorie.
        step:    ampiezza della fascia in anni — 5 oppure 10.

    Returns:
        Lista di Categoria (non ancora salvate nel DB) ordinate:
        prima tutti i M in ordine crescente di età, poi tutti gli F.
    """
    fasce = _genera_fasce(step)
    cats: list[Categoria] = []
    ordine = 1
    for sesso in ('M', 'F'):
        for eta_min, eta_max in fasce:
            cats.append(Categoria(
                gara_id=gara_id,
                nome=_nome(sesso, eta_min, eta_max),
                sesso=sesso,
                eta_min=eta_min,
                eta_max=eta_max,
                ordine=ordine,
            ))
            ordine += 1
    return cats


# Descrizioni leggibili per l'UI, indicizzate per ampiezza fascia
PRESETS: dict[int, str] = {
    5:  "5 a 5  — M/F 18-24, 25-29, 30-34 … 75-79, 80+",
    10: "10 a 10 — M/F 18-29, 30-39, 40-49 … 70-79, 80+",
}
