"""
Backend Flask: upload Excel, segmentazione, campagne, dashboard data.
Compatibile Python 3.14 (no Pydantic/FastAPI). Nessun export Excel; risultati via API.
"""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date
from typing import Optional

import pandas as pd
from flask import Flask, jsonify, request, abort

from app.campaigns import get_all_campaigns_by_segment
from app.excel_parser import parse_and_segment
from app.models import Segment, SegmentedCustomer

try:
    from flask_cors import CORS
except ImportError:
    CORS = None

# In-memory store (in produzione usare PostgreSQL)
_store: dict[str, list[SegmentedCustomer]] = {}

app = Flask(__name__)
if CORS is not None:
    import os
    _origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").strip().split(",")
    _origins = [o.strip() for o in _origins if o.strip()]
    CORS(app, origins=_origins, supports_credentials=True)


@app.route("/api/upload", methods=["POST"])
def upload_excel():
    """Carica file Excel con dati arrivi. Restituisce analysis_id (nessun file in output)."""
    file = request.files.get("file")
    if not file or not file.filename:
        abort(400, "Nessun file caricato")
    fn = file.filename.lower()
    if not (fn.endswith(".xlsx") or fn.endswith(".xls") or fn.endswith(".csv")):
        abort(400, "File deve essere .xlsx, .xls o .csv")
    try:
        contents = file.read()
        if fn.endswith(".csv"):
            try:
                text = contents.decode("utf-8")
            except UnicodeDecodeError:
                text = contents.decode("latin-1")
            # Lettura CSV con stdlib per evitare errori "expected pattern" di pandas
            reader = csv.DictReader(io.StringIO(text), delimiter=",", quotechar='"')
            rows = list(reader)
            if not rows:
                abort(400, "Il file CSV è vuoto")
            df = pd.DataFrame(rows)
        else:
            # .xlsx con openpyxl; .xls con xlrd (se installato)
            engine = "openpyxl" if fn.endswith(".xlsx") else None
            try:
                df = pd.read_excel(io.BytesIO(contents), engine=engine, dtype=str)
            except Exception as xls_err:
                if fn.endswith(".xls"):
                    abort(400, "File .xls non supportato. In Excel: File → Salva con nome → formato 'Cartella di lavoro Excel (.xlsx)' o 'CSV UTF-8', poi ricarica.")
                raise xls_err
            df = df.replace({"nan": None, "": None, "NaN": None})
    except Exception as e:
        err_msg = str(e)
        if "pattern" in err_msg.lower() or "match" in err_msg.lower() or "expected" in err_msg.lower():
            abort(400, "File non leggibile. Usa un CSV con virgola come separatore (prima riga = intestazioni).")
        abort(400, f"File non valido: {err_msg}")
    if df.empty:
        abort(400, "Il file è vuoto")
    try:
        customers, _ = parse_and_segment(df)
    except Exception as e:
        err_msg = str(e)
        if "pattern" in err_msg.lower() or "match" in err_msg.lower() or "expected" in err_msg.lower():
            abort(400, "Errore nei dati. Controlla date e numeri (usa formato 2024-01-15 per le date).")
        abort(400, f"Errore elaborazione: {err_msg}")
    if not customers:
        abort(400, "Nessuna riga analizzata. Controlla che il file abbia la prima riga con le intestazioni (es. numero notti, numero ospiti, canale, data arrivo, ...). Vedi istruzioni nella pagina.")
    analysis_id = str(uuid.uuid4())
    _store[analysis_id] = customers
    return jsonify({
        "analysis_id": analysis_id,
        "total_arrivals": len(customers),
        "message": "File elaborato. Usa analysis_id per la dashboard.",
    })


@app.route("/api/analysis/<analysis_id>/overview")
def get_overview(analysis_id: str):
    """KPI overview: totale arrivi, distribuzione segmenti, ADR, revenue, valore cliente medio."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    total = len(customers)
    by_segment = defaultdict(list)
    for c in customers:
        by_segment[c.segment].append(c)
    segment_stats = []
    for seg in Segment:
        list_c = by_segment.get(seg, [])
        count = len(list_c)
        pct = (count / total * 100) if total else 0
        revenues = [c.revenue for c in list_c if c.revenue is not None]
        spendings = [c.spesa_media for c in list_c if c.spesa_media is not None]
        adr = sum(spendings) / len(spendings) if spendings else 0
        rev_tot = sum(revenues) if revenues else 0
        val_medio = (rev_tot / count) if count else 0
        segment_stats.append({
            "segment": seg.value,
            "count": count,
            "percentuale": round(pct, 1),
            "adr_medio": round(adr, 2),
            "revenue_totale": round(rev_tot, 2),
            "valore_cliente_medio": round(val_medio, 2),
        })
    total_revenue = sum(s["revenue_totale"] for s in segment_stats)
    overall_adr = sum(c.spesa_media or 0 for c in customers) / total if total else 0
    return jsonify({
        "total_arrivals": total,
        "total_revenue": round(total_revenue, 2),
        "adr_medio_generale": round(overall_adr, 2),
        "valore_cliente_medio_generale": round(total_revenue / total, 2) if total else 0,
        "segment_distribution": segment_stats,
    })


@app.route("/api/analysis/<analysis_id>/customers")
def get_customers(analysis_id: str):
    """Tabella clienti filtrabile per segmento, con score dettagliato."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    segment = request.args.get("segment")
    if segment:
        try:
            seg_enum = Segment(segment)
        except ValueError:
            abort(400, "Segmento non valido")
        customers = [c for c in customers if c.segment == seg_enum]
    try:
        skip = max(0, int(request.args.get("skip", 0)))
        limit = max(1, min(500, int(request.args.get("limit", 100))))
    except (TypeError, ValueError):
        skip, limit = 0, 100
    out = []
    for c in customers[skip : skip + limit]:
        out.append({
            "row_index": c.row_index,
            "segment": c.segment.value,
            "scores": c.scores.to_dict(),
            "numero_notti": c.numero_notti,
            "numero_ospiti": c.numero_ospiti,
            "canale": c.canale,
            "giorno_arrivo": c.giorno_arrivo,
            "storico_soggiorni": c.storico_soggiorni,
            "spesa_media": c.spesa_media,
            "cliente_id": c.cliente_id,
            "nome_cliente": c.nome_cliente,
            "data_arrivo": c.data_arrivo,
            "categoria_camera": c.categoria_camera,
            "revenue": c.revenue,
        })
    return jsonify(out)


@app.route("/api/analysis/<analysis_id>/customers/count")
def get_customers_count(analysis_id: str):
    """Conteggio clienti (per paginazione), opzionale per segmento."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    segment = request.args.get("segment")
    if segment:
        try:
            seg_enum = Segment(segment)
            customers = [c for c in customers if c.segment == seg_enum]
        except ValueError:
            pass
    return jsonify({"count": len(customers)})


@app.route("/api/analysis/<analysis_id>/marketing")
def get_marketing(analysis_id: str):
    """Marketing Intelligence: campagne per segmento, revenue potenziale, conversion/ROI (placeholder)."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    by_segment = defaultdict(list)
    for c in customers:
        by_segment[c.segment].append(c)
    campaigns_by_segment = get_all_campaigns_by_segment()
    segment_summaries = []
    for seg in Segment:
        list_c = by_segment.get(seg, [])
        count = len(list_c)
        revenues = [c.revenue for c in list_c if c.revenue is not None]
        rev_tot = sum(revenues) if revenues else 0
        campagne = campaigns_by_segment.get(seg, [])
        revenue_potenziale = round(rev_tot * 1.15, 2)
        segment_summaries.append({
            "segment": seg.value,
            "count": count,
            "revenue_attuale": round(rev_tot, 2),
            "revenue_potenziale_stimata": revenue_potenziale,
            "conversion_rate_storico": 0.12,
            "roi_stimato": 2.5,
            "campagne": [x.to_dict() for x in campagne],
        })
    return jsonify({
        "segmenti": segment_summaries,
        "campagne_globali": {s.value: [c.to_dict() for c in get_all_campaigns_by_segment()[s]] for s in Segment},
    })


@app.route("/api/analysis/<analysis_id>/trend")
def get_trend(analysis_id: str):
    """Trend settimanale segmenti (per data_arrivo se presente)."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    week_segment: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for c in customers:
        if c.data_arrivo:
            try:
                y, m, d = map(int, c.data_arrivo.split("-")[:3])
                w = date(y, m, d).isocalendar()[1]
                key = f"{y}-W{w}"
            except Exception:
                key = "N/A"
        else:
            key = "N/A"
        week_segment[key][c.segment.value] += 1
    trend = [{"week": week, "segmenti": dict(week_segment[week])} for week in sorted(week_segment.keys(), reverse=True)[:12]]
    return jsonify({"trend_settimanale": trend})


@app.route("/api/segments")
def list_segments():
    """Elenco segmenti (per UI)."""
    return jsonify({"segments": [s.value for s in Segment]})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# Gestione errori HTTP per restituire JSON
@app.errorhandler(400)
@app.errorhandler(404)
def json_error(e):
    return jsonify({"detail": e.description or str(e)}), e.code


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
