from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Atleta:
    id: Optional[int] = None
    nome: str = ""
    cognome: str = ""
    sesso: str = ""
    data_nascita: str = ""
    luogo_nascita: Optional[str] = None
    nazionalita: str = "ITA"
    codice_fiscale: Optional[str] = None
    societa: Optional[str] = None
    codice_societa: Optional[str] = None
    tessera: Optional[str] = None
    tessera2: Optional[str] = None
    ente: Optional[str] = None
    categoria: Optional[str] = None
    scad_certificato: Optional[str] = None
    stato_cert: Optional[str] = None
    telefono: Optional[str] = None
    cellulare: Optional[str] = None
    email: Optional[str] = None
    note: Optional[str] = None
    source_id: Optional[str] = None
    source_order_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def nome_completo(self) -> str:
        return f"{self.cognome} {self.nome}".strip()
