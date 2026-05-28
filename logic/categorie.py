from typing import Optional
from models.gara import Categoria


def calcola_categoria(
    categorie: list[Categoria],
    data_nascita: str,
    sesso: str,
    anno_gara: int,
) -> Optional[str]:
    """
    Restituisce il nome della prima categoria che corrisponde all'atleta,
    rispettando ordine, sesso e range di età (anno_gara - anno_nascita).
    """
    try:
        anno_nascita = int(data_nascita.split('-')[0])
        eta = anno_gara - anno_nascita
    except Exception:
        return None

    for cat in sorted(categorie, key=lambda c: c.ordine):
        if cat.sesso not in (sesso, 'MF'):
            continue
        if cat.eta_min is not None and eta < cat.eta_min:
            continue
        if cat.eta_max is not None and eta > cat.eta_max:
            continue
        return cat.nome

    return None
