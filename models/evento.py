from dataclasses import dataclass
from typing import Optional


@dataclass
class Evento:
    id: Optional[int] = None
    nome: str = ""
    data: str = ""
    luogo: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[str] = None
