from dataclasses import dataclass
from typing import Optional


@dataclass
class Risultato:
    id: Optional[int] = None
    iscrizione_id: int = 0
    tempo_ms: Optional[int] = None
    tempo_override: Optional[str] = None
    stato: str = "ok"
    ordine_arrivo: Optional[int] = None
    note_arbitro: Optional[str] = None
    updated_at: Optional[str] = None
    # campi JOIN
    atleta_nome: Optional[str] = None
    atleta_cognome: Optional[str] = None
    atleta_sesso: Optional[str] = None
    atleta_data_nascita: Optional[str] = None
    pettorale: Optional[str] = None
    categoria_effettiva: Optional[str] = None

    @property
    def nome_atleta(self) -> str:
        return f"{self.atleta_cognome or ''} {self.atleta_nome or ''}".strip()
