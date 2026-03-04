"""
Parsing file Excel arrivi clienti.
Supporta colonne con nomi italiani o inglesi, flessibile su naming.
"""
import re
from datetime import datetime
from typing import Any

import pandas as pd

from app.models import SegmentedCustomer, Segment, Scores
from app.scoring import compute_scores, assign_segment


# Possibili alias per colonne Excel (italiano / inglese). L'ordine delle colonne nel file non conta.
# Supporto export gestionale: Cliente, data di prenotazione, Arrivo, Partenza, Giorni, Prenotante, totale, Interi, scontati
COLUMN_ALIASES = {
    "numero_notti": ["notti", "nights", "numero notti", "n. notti", "notte", "notti soggiorno", "giorni", "giorni pernottamento", "pernottamento"],
    "numero_ospiti": ["ospiti", "guests", "pax", "numero ospiti", "n. ospiti", "prenotati"],
    "canale": ["canale", "channel", "canale prenotazione", "source", "distribution"],
    "giorno_arrivo": ["giorno arrivo", "day", "arrival day", "giorno", "weekday", "giorno_arrivo"],
    "storico_soggiorni": ["storico", "storico soggiorni", "previous stays", "stays", "n. soggiorni", "soggiorni precedenti"],
    "spesa_media": ["spesa", "spesa media", "revenue", "adr", "amount", "importo", "spesa_media", "spesa media", "tariffa", "tariff", "rate", "prezzo"],
    "totale_soggiorno": ["totale", "totale costo soggiorno", "costo totale", "importo totale", "total", "totale soggiorno"],
    "cliente_id": ["id", "customer id", "guest id", "codice cliente", "id cliente"],
    "nome_cliente": ["nome", "nome cliente", "name", "guest name", "cliente nome", "nominativo", "cliente"],
    "data_arrivo": ["data", "data arrivo", "arrival", "arrival date", "check-in", "check in", "data_arrivo", "data arrivo", "arrivo"],
    "data_partenza": ["data partenza", "departure", "check-out", "check out", "data_partenza", "partenza"],
    "categoria_camera": ["camera", "room", "room type", "categoria", "tipo camera", "categoria_camera"],
    # Anticipo prenotazione: giorni tra prenotazione e arrivo (o data prenotazione per calcolo)
    "anticipo_giorni": ["anticipo", "anticipo giorni", "giorni anticipo", "lead time", "lead_time", "days in advance", "giorni prenotazione"],
    "data_prenotazione": ["data prenotazione", "data di prenotazione", "booking date", "data booking", "prenotato il", "created", "data creazione"],
    # Chi ha effettuato la prenotazione (es. agenzia)
    "prenotante": ["prenotante", "booker", "tipo prenotante", "fonte", "who booked", "tipologia", "tipo cliente", "agenzia della prenotazione", "agenzia"],
    # Adulti e bambini (export gestionale: Interi = adulti, scontati = bambini)
    "numero_adulti": ["interi", "nr di adulti", "n. adulti", "numero adulti", "adulti"],
    "numero_bambini": ["bambini", "numero bambini", "n. bambini", "children", "kids", "bambini soggiorno", "scontati", "nr bambini"],
}


def _normalize_column_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    n = name.strip().lower()
    n = re.sub(r"\s+", " ", n)
    return n


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    """Mappa nome logico -> nome colonna effettiva nel DataFrame."""
    out = {}
    cols_lower = {_normalize_column_name(c): c for c in df.columns}
    for logical, aliases in COLUMN_ALIASES.items():
        for al in aliases:
            an = _normalize_column_name(al)
            if an in cols_lower:
                out[logical] = cols_lower[an]
                break
        if logical not in out and logical in cols_lower:
            out[logical] = cols_lower[logical]
    return out


def _get_day_name(val: Any) -> str:
    """Da data o numero 0-6 o stringa giorno restituisce abbreviazione Lun/Mar/..."""
    days = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
    if pd.isna(val):
        return ""
    if isinstance(val, (int, float)):
        try:
            return days[int(val) % 7]
        except (ValueError, TypeError):
            return ""
    if isinstance(val, datetime):
        return days[val.weekday()]
    s = str(val).strip().lower()
    # Prima prova a interpretare come data (es. "2024-06-15"): così non restituiamo "202"
    dt = _parse_date(val)
    if dt is not None:
        return days[dt.weekday()]
    # Stringa numerica (es. "202" da Excel): usa come numero giorno
    if s.isdigit() or (s.replace(".", "", 1).replace(",", "", 1).isdigit()):
        try:
            n = int(float(s.replace(",", ".")))
            return days[n % 7]
        except (ValueError, TypeError):
            pass
    if len(s) >= 2:
        return s[:3]  # lun, mar, lunedì -> lun
    return s


def _parse_date(val: Any) -> datetime | None:
    """Converte valore in datetime (accetta Excel, stringhe DD/MM/YYYY, YYYY-MM-DD, ecc.)."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val
    try:
        dt = pd.to_datetime(val)
        if hasattr(dt, "to_pydatetime"):
            return dt.to_pydatetime()
        return datetime(dt.year, dt.month, dt.day)
    except Exception:
        pass
    s = str(val).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _nights_from_dates(arrivo: Any, partenza: Any) -> int | None:
    """Calcola numero notti da data arrivo e data partenza (se entrambe presenti)."""
    d1 = _parse_date(arrivo)
    d2 = _parse_date(partenza)
    if d1 is None or d2 is None:
        return None
    delta = (d2 - d1).days
    return max(0, delta) if isinstance(delta, int) else max(0, int(delta))


def _is_vacation_period(val: Any) -> bool:
    if pd.isna(val):
        return False
    dt = _parse_date(val)
    return dt.month in (1, 6, 7, 8, 12) if dt else False


def parse_and_segment(df: pd.DataFrame) -> tuple[list[SegmentedCustomer], float | None]:
    """
    Legge il DataFrame (da Excel), segmenta ogni riga, restituisce lista SegmentedCustomer
    e soglia spesa top 25% (per scoring Premium).
    """
    if df.empty:
        return [], None

    col_map = _map_columns(df)
    if not col_map:
        # Fallback: usa prima riga come header se necessario, oppure colonne 0,1,2...
        col_map = {}
        for i, c in enumerate(df.columns):
            if i == 0:
                col_map["cliente_id"] = c
            elif i == 1:
                col_map["data_arrivo"] = c
            elif i == 2:
                col_map["numero_notti"] = c
            elif i == 3:
                col_map["numero_ospiti"] = c
            elif i == 4:
                col_map["canale"] = c
            elif i == 5:
                col_map["giorno_arrivo"] = c
            elif i == 6:
                col_map["storico_soggiorni"] = c
            elif i == 7:
                col_map["spesa_media"] = c
            elif i == 8:
                col_map["categoria_camera"] = c
            elif i == 9:
                col_map["anticipo_giorni"] = c
            elif i == 10:
                col_map["prenotante"] = c
            elif i == 11:
                col_map["numero_bambini"] = c

    def get(row: pd.Series, key: str, default: Any = None):
        col = col_map.get(key)
        if col is None or col not in row:
            return default
        v = row.get(col)
        if pd.isna(v):
            return default
        return v

    # Soglia top 25% e media spesa (per capacità sopra/sotto media)
    # Se il file ha "totale" (costo soggiorno) ma non "spesa media", la calcoliamo come totale/giorni
    threshold_top25 = None
    media_spesa = None
    try:
        spesa_col = col_map.get("spesa_media")
        totale_col = col_map.get("totale_soggiorno")
        notti_col = col_map.get("numero_notti")
        if spesa_col and spesa_col in df.columns:
            series = pd.to_numeric(df[spesa_col], errors="coerce").dropna()
            if not series.empty:
                threshold_top25 = float(series.quantile(0.75))
                media_spesa = float(series.mean())
        elif totale_col and totale_col in df.columns and notti_col and notti_col in df.columns:
            totali = pd.to_numeric(df[totale_col], errors="coerce")
            notti_ser = pd.to_numeric(df[notti_col], errors="coerce").replace(0, float("nan"))
            series = (totali / notti_ser).dropna()
            if not series.empty:
                threshold_top25 = float(series.quantile(0.75))
                media_spesa = float(series.mean())
    except Exception:
        pass

    results: list[SegmentedCustomer] = []
    for idx, row in df.iterrows():
        try:
            i = int(idx) if isinstance(idx, (int, float)) else len(results)
            notti = int(pd.to_numeric(get(row, "numero_notti", 0), errors="coerce") or 0)
            if notti <= 0:
                calc = _nights_from_dates(get(row, "data_arrivo"), get(row, "data_partenza"))
                if calc is not None:
                    notti = calc
            # Ospiti: da colonna unica "numero_ospiti" oppure Interi + scontati (adulti + bambini)
            adulti_val = get(row, "numero_adulti")
            bambini_col_val = get(row, "numero_bambini")
            numero_bambini_from_col: int | None = None  # valorizzato se usiamo Interi/scontati
            if adulti_val is not None or bambini_col_val is not None:
                adulti = int(pd.to_numeric(adulti_val, errors="coerce") or 0)
                bambini_num = 0
                if bambini_col_val is not None:
                    s = str(bambini_col_val).strip().lower()
                    if s in ("sì", "si", "yes", "1", "x", "ok"):
                        bambini_num = 1
                    elif s not in ("no", "0", ""):
                        try:
                            bambini_num = int(pd.to_numeric(bambini_col_val, errors="coerce") or 0)
                        except (TypeError, ValueError):
                            pass
                numero_bambini_from_col = bambini_num
                ospiti = adulti + bambini_num
            else:
                ospiti = int(pd.to_numeric(get(row, "numero_ospiti", 0), errors="coerce") or 0)
            canale = str(get(row, "canale", "") or "")
            # Se il file ha solo "Prenotante" (agenzia) e non "canale", usalo come canale per la dashboard
            if not canale:
                prenotante_raw = get(row, "prenotante")
                if prenotante_raw is not None:
                    canale = str(prenotante_raw).strip()
            giorno_raw = get(row, "giorno_arrivo") or get(row, "data_arrivo")
            giorno = _get_day_name(giorno_raw)
            storico = int(pd.to_numeric(get(row, "storico_soggiorni", 0), errors="coerce") or 0)
            spesa = _norm_float(get(row, "spesa_media"))
            totale_val = _norm_float(get(row, "totale_soggiorno"))
            # Se c'è "totale" (costo soggiorno) e non abbiamo spesa per notte, ricavala: totale / giorni
            if spesa is None and notti > 0 and totale_val is not None and totale_val > 0:
                spesa = round(totale_val / notti, 2)
            cat_camera = str(get(row, "categoria_camera", "") or "")
            data_arrivo_raw = get(row, "data_arrivo")
            data_arrivo = None
            if data_arrivo_raw is not None:
                dt = _parse_date(data_arrivo_raw)
                data_arrivo = dt.strftime("%Y-%m-%d") if dt else str(data_arrivo_raw).strip()[:10] or None
            is_vacation = _is_vacation_period(data_arrivo_raw)

            # Anticipo: da colonna "anticipo_giorni" o da (data_arrivo - data_prenotazione)
            anticipo_giorni = None
            anticipo_val = get(row, "anticipo_giorni")
            if anticipo_val is not None:
                try:
                    anticipo_giorni = int(pd.to_numeric(anticipo_val, errors="coerce") or 0)
                except (TypeError, ValueError):
                    pass
            if anticipo_giorni is None:
                dt_arr = _parse_date(get(row, "data_arrivo"))
                dt_pren = _parse_date(get(row, "data_prenotazione"))
                if dt_arr and dt_pren and dt_pren <= dt_arr:
                    anticipo_giorni = (dt_arr - dt_pren).days

            prenotante = str(get(row, "prenotante", "") or "").strip() or None

            numero_bambini = numero_bambini_from_col if numero_bambini_from_col is not None else None
            if numero_bambini is None:
                bambini_val = get(row, "numero_bambini")
                if bambini_val is not None:
                    s = str(bambini_val).strip().lower()
                    if s in ("sì", "si", "yes", "1", "x", "ok"):
                        numero_bambini = 1
                    elif s in ("no", "0", ""):
                        numero_bambini = 0
                    else:
                        try:
                            numero_bambini = int(pd.to_numeric(bambini_val, errors="coerce") or 0)
                        except (TypeError, ValueError):
                            pass

            if notti <= 0:
                notti = 1
            if ospiti <= 0:
                ospiti = 1

            scores = compute_scores(
                numero_notti=notti,
                numero_ospiti=ospiti,
                canale=canale,
                giorno_arrivo=giorno,
                storico_soggiorni=storico,
                spesa_media=spesa,
                categoria_camera=cat_camera,
                threshold_top25=threshold_top25,
                is_vacation_period=is_vacation,
                media_spesa=media_spesa,
                anticipo_giorni=anticipo_giorni,
                prenotante=prenotante,
                numero_bambini=numero_bambini,
            )
            segment = assign_segment(scores)
            # Revenue: da totale soggiorno se presente, altrimenti spesa * notti
            if totale_val is not None and totale_val > 0:
                revenue = round(totale_val, 2)
            else:
                revenue = (spesa * notti) if spesa is not None else None
            results.append(
                SegmentedCustomer(
                    row_index=i,
                    segment=segment,
                    scores=scores,
                    numero_notti=notti,
                    numero_ospiti=ospiti,
                    canale=canale or None,
                    giorno_arrivo=giorno or None,
                    storico_soggiorni=storico,
                    spesa_media=spesa,
                    cliente_id=str(get(row, "cliente_id", "")) or None,
                    nome_cliente=str(get(row, "nome_cliente", "")).strip() or None,
                    data_arrivo=data_arrivo,
                    categoria_camera=cat_camera or None,
                    revenue=revenue,
                    anticipo_giorni=anticipo_giorni,
                    prenotante=prenotante,
                    numero_bambini=numero_bambini,
                )
            )
        except Exception:
            continue  # salta righe che danno errore
    return results, threshold_top25


def _norm_float(v: Any) -> float | None:
    """Converte in float; accetta formato europeo (1.234,56 o 1 234,56)."""
    if v is None or (isinstance(v, float) and (v != v)):
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        pass
    s = str(v).strip().replace(" ", "").replace("\u00a0", "")
    if "," in s and "." in s:
        # Mantieni solo la virgola come decimale
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None
