from dataclasses import dataclass
from typing import Optional


@dataclass
class Gara:
    id: Optional[int] = None
    evento_id: int = 0
    nome: str = ""
    tipo: Optional[str] = None
    distanza_m: Optional[int] = None
    stato: str = "bozza"
    start_ts: Optional[float] = None
    start_wall: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Iscrizione:
    id: Optional[int] = None
    gara_id: int = 0
    atleta_id: int = 0
    pettorale: str = ""
    pettorale_circ: Optional[str] = None
    codice_chip: Optional[str] = None
    quota: Optional[str] = None
    stato_lw: Optional[str] = None
    categoria_calc: Optional[str] = None
    categoria_override: Optional[str] = None
    partecipa: int = 1
    # campi denormalizzati dall'atleta (popolati dalle query con JOIN)
    atleta_nome: Optional[str] = None
    atleta_cognome: Optional[str] = None
    atleta_sesso: Optional[str] = None
    atleta_data_nascita: Optional[str] = None
    atleta_societa: Optional[str] = None

    @property
    def categoria_effettiva(self) -> Optional[str]:
        return self.categoria_override or self.categoria_calc

    @property
    def nome_atleta(self) -> str:
        return f"{self.atleta_cognome or ''} {self.atleta_nome or ''}".strip()


@dataclass
class Categoria:
    id: Optional[int] = None
    gara_id: Optional[int] = None
    nome: str = ""
    sesso: str = "MF"
    eta_min: Optional[int] = None
    eta_max: Optional[int] = None
    ordine: int = 0

    def descrizione(self) -> str:
        eta = ""
        if self.eta_min is not None and self.eta_max is not None:
            eta = f"{self.eta_min}-{self.eta_max} anni"
        elif self.eta_min is not None:
            eta = f"≥ {self.eta_min} anni"
        elif self.eta_max is not None:
            eta = f"≤ {self.eta_max} anni"
        parts = [self.sesso]
        if eta:
            parts.append(eta)
        return f"{self.nome} ({', '.join(parts)})"
