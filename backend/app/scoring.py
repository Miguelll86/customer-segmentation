"""
Algoritmo di scoring ponderato per segmentazione clienti.
Una sola categoria primaria per cliente; in parità: Premium > Business > Famiglia > Coppia > Leisure.
"""
from typing import Any

from app.models import Segment, Scores, SEGMENT_PRIORITY


# Normalizzazione canali
CANALI_CORPORATE_GDS = {"corporate", "gds", "corporate/gds", "aziendale"}
CANALI_OTA_LEISURE = {"ota", "booking", "booking.com", "expedia", "leisure", "vacanza"}
CANALI_DIRETTO = {"direct", "diretto", "sito", "web", "phone", "telefono"}

GIORNI_MIDWEEK = {"lun", "mar", "mer", "lunedì", "martedì", "mercoledì", "monday", "tuesday", "wednesday"}
GIORNI_WEEKEND = {"ven", "sab", "dom", "venerdì", "sabato", "domenica", "friday", "saturday", "sunday"}
GIORNI_COPPIA = GIORNI_WEEKEND

MESI_VACANZE = {6, 7, 8, 12, 1}


def _norm(s: Any) -> str:
    if s is None or (isinstance(s, float) and (s != s)):
        return ""
    return str(s).strip().lower()


def _norm_float(v: Any) -> float | None:
    if v is None or (isinstance(v, float) and (v != v)):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _is_high_spend(spesa: float | None, threshold_top25: float | None) -> bool:
    if threshold_top25 is None or spesa is None:
        return False
    return spesa >= threshold_top25


def _is_high_room_category(cat: str) -> bool:
    if not cat:
        return False
    c = _norm(cat)
    return any(x in c for x in ("suite", "deluxe", "premium", "superior", "executive", "junior", "presidential"))


def compute_scores(
    numero_notti: int,
    numero_ospiti: int,
    canale: str,
    giorno_arrivo: str,
    storico_soggiorni: int,
    spesa_media: float | None,
    categoria_camera: str,
    threshold_top25: float | None,
    is_vacation_period: bool,
) -> Scores:
    """Calcola i 5 punteggi per un singolo record."""
    cn = _norm(canale)
    gn = _norm(giorno_arrivo)
    business = leisure = coppia = famiglia = premium = 0

    # BUSINESS
    if gn in GIORNI_MIDWEEK:
        business += 3
    if numero_ospiti == 1:
        business += 3
    if 1 <= numero_notti <= 2:
        business += 2
    if cn in CANALI_CORPORATE_GDS or "gds" in cn or "corporate" in cn:
        business += 2
    if storico_soggiorni > 0 and numero_notti <= 2:
        business += 1

    # LEISURE
    if numero_notti >= 3:
        leisure += 2
    if gn in {"ven", "sab", "dom", "venerdì", "sabato", "domenica", "friday", "saturday", "sunday"}:
        leisure += 1
    if any(x in cn for x in ["ota", "booking", "expedia", "leisure"]):
        leisure += 2
    if storico_soggiorni == 0:
        leisure += 1

    # COPPIA
    if numero_ospiti == 2:
        coppia += 3
    if 1 <= numero_notti <= 3:
        coppia += 2
    if gn in GIORNI_COPPIA:
        coppia += 3
    if any(x in cn for x in ["ota", "booking", "expedia", "leisure"]):
        coppia += 1

    # FAMIGLIA
    if numero_ospiti >= 3:
        famiglia += 3
    if numero_notti >= 3:
        famiglia += 2
    if gn in GIORNI_WEEKEND:
        famiglia += 2
    if is_vacation_period:
        famiglia += 2

    # PREMIUM
    if _is_high_spend(spesa_media, threshold_top25):
        premium += 4
    if storico_soggiorni >= 3:
        premium += 3
    if numero_notti >= 4:
        premium += 2
    if cn in CANALI_DIRETTO or "direct" in cn or "diretto" in cn:
        premium += 2
    if _is_high_room_category(categoria_camera):
        premium += 2

    return Scores(
        business=business,
        leisure=leisure,
        coppia=coppia,
        famiglia=famiglia,
        premium=premium,
    )


KEY_TO_SEGMENT = {
    "business": Segment.BUSINESS,
    "leisure": Segment.LEISURE,
    "coppia": Segment.COPPIA,
    "famiglia": Segment.FAMIGLIA,
    "premium": Segment.PREMIUM,
}


def assign_segment(scores: Scores) -> Segment:
    """Assegna il segmento con punteggio massimo; in parità usa SEGMENT_PRIORITY."""
    d = scores.to_dict()
    best_score = max(d.values())
    candidates_enum = [KEY_TO_SEGMENT[k] for k, v in d.items() if v == best_score]
    for seg in SEGMENT_PRIORITY:
        if seg in candidates_enum:
            return seg
    return Segment.LEISURE
