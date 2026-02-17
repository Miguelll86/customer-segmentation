"""Modelli per dati arrivi e segmentazione (solo stdlib: dataclasses + Enum). Compatibile Python 3.14."""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional


class Segment(str, Enum):
    BUSINESS = "Business"
    LEISURE = "Leisure"
    COPPIA = "Coppia"
    FAMIGLIA = "Famiglia"
    PREMIUM = "Premium"


# Priorità per parità: Premium > Business > Famiglia > Coppia > Leisure
SEGMENT_PRIORITY = [
    Segment.PREMIUM,
    Segment.BUSINESS,
    Segment.FAMIGLIA,
    Segment.COPPIA,
    Segment.LEISURE,
]


@dataclass
class Scores:
    """Punteggi per ogni segmento."""
    business: int = 0
    leisure: int = 0
    coppia: int = 0
    famiglia: int = 0
    premium: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SegmentedCustomer:
    """Cliente con segmento e punteggi."""
    row_index: int
    segment: Segment
    scores: Scores
    numero_notti: Optional[int] = None
    numero_ospiti: Optional[int] = None
    canale: Optional[str] = None
    giorno_arrivo: Optional[str] = None
    storico_soggiorni: Optional[int] = None
    spesa_media: Optional[float] = None
    cliente_id: Optional[str] = None
    nome_cliente: Optional[str] = None
    data_arrivo: Optional[str] = None
    categoria_camera: Optional[str] = None
    revenue: Optional[float] = None


@dataclass
class CampaignItem:
    """Singola campagna per segmento."""
    titolo: str
    descrizione: str
    tipo: str
    segmento: Segment

    def to_dict(self) -> dict:
        return {
            "titolo": self.titolo,
            "descrizione": self.descrizione,
            "tipo": self.tipo,
            "segmento": self.segmento.value,
        }
