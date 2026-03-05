"""
Algoritmo di scoring ponderato per segmentazione clienti.
Una sola categoria primaria per cliente; in parità: Business > Famiglia > Coppia > Leisure (Leisure include ex-Premium).
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
    spesa_media: float | None,
    categoria_camera: str,
    threshold_top25: float | None,
    is_vacation_period: bool,
    media_spesa: float | None = None,
    anticipo_giorni: int | None = None,
    prenotante: str | None = None,
    numero_bambini: int | None = None,
) -> Scores:
    """Calcola i 4 punteggi per un singolo record (combinazioni giorno+notti, spesa, anticipo, prenotante, bambini). Storico soggiorni non usato."""
    cn = _norm(canale)
    gn = _norm(giorno_arrivo)
    is_weekend = gn in {"ven", "sab", "dom", "venerdì", "sabato", "domenica", "friday", "saturday", "sunday"}
    is_midweek = gn in GIORNI_MIDWEEK
    business = leisure = coppia = famiglia = 0

    # --- Combinazioni giorno arrivo + numero notti ---
    if is_weekend and numero_notti == 1:
        business += 2  # weekend breve spesso business
        coppia += 1
    if is_weekend and 2 <= numero_notti <= 3:
        coppia += 3
        leisure += 2
    if is_weekend and numero_notti >= 4:
        famiglia += 2
        leisure += 1
    if is_midweek and 1 <= numero_notti <= 2:
        business += 3
    if is_midweek and numero_notti >= 3:
        leisure += 1
        famiglia += 1

    # --- BUSINESS ---
    if gn in GIORNI_MIDWEEK:
        business += 2
    if numero_ospiti == 1:
        business += 3
    if 1 <= numero_notti <= 2:
        business += 2
    if cn in CANALI_CORPORATE_GDS or "gds" in cn or "corporate" in cn:
        business += 2
    # Anticipo: last minute (0-7 giorni) spesso business
    if anticipo_giorni is not None and 0 <= anticipo_giorni <= 7:
        business += 2
    # Prenotante: agenzia/azienda/tour operator → business
    if prenotante:
        pn = _norm(prenotante)
        if any(x in pn for x in ["agenzia", "agency", "azienda", "corporate", "tour operator", "to ", "gds", "business"]):
            business += 2

    # --- LEISURE ---
    if numero_notti >= 3:
        leisure += 2
    if is_weekend:
        leisure += 1
    if any(x in cn for x in ["ota", "booking", "expedia", "leisure"]):
        leisure += 2
    # Spesa sotto media → spesso leisure
    if media_spesa is not None and spesa_media is not None and spesa_media < media_spesa:
        leisure += 1
    # Prenotazione in anticipo (30+ giorni) → leisure
    if anticipo_giorni is not None and anticipo_giorni >= 30:
        leisure += 1
    if prenotante and ("cliente" in _norm(prenotante) or "guest" in _norm(prenotante)):
        leisure += 1

    # --- COPPIA ---
    if numero_ospiti == 2:
        coppia += 3
    if 1 <= numero_notti <= 3:
        coppia += 2
    if gn in GIORNI_COPPIA:
        coppia += 3
    if any(x in cn for x in ["ota", "booking", "expedia", "leisure"]):
        coppia += 1
    if numero_bambini is not None and numero_bambini == 0 and numero_ospiti == 2:
        coppia += 2

    # --- FAMIGLIA ---
    if numero_ospiti >= 3:
        famiglia += 3
    if numero_notti >= 3:
        famiglia += 2
    if gn in GIORNI_WEEKEND:
        famiglia += 2
    if is_vacation_period:
        famiglia += 2
    # Presenza bambini → forte segnale famiglia
    if numero_bambini is not None and numero_bambini >= 1:
        famiglia += 4
    if anticipo_giorni is not None and anticipo_giorni >= 30:
        famiglia += 1  # prenotazioni family spesso in anticipo

    # --- LEISURE (include ex-Premium: alta spesa, categoria camera, direct) ---
    if _is_high_spend(spesa_media, threshold_top25):
        leisure += 4
    if media_spesa is not None and spesa_media is not None and spesa_media >= media_spesa:
        leisure += 1
    if numero_notti >= 4:
        leisure += 2
    if cn in CANALI_DIRETTO or "direct" in cn or "diretto" in cn:
        leisure += 2
    if _is_high_room_category(categoria_camera):
        leisure += 2

    return Scores(
        business=business,
        leisure=leisure,
        coppia=coppia,
        famiglia=famiglia,
    )


KEY_TO_SEGMENT = {
    "business": Segment.BUSINESS,
    "leisure": Segment.LEISURE,
    "coppia": Segment.COPPIA,
    "famiglia": Segment.FAMIGLIA,
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
