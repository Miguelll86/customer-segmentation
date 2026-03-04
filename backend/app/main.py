"""
Backend Flask: upload Excel, segmentazione, campagne, dashboard data.
Compatibile Python 3.14 (no Pydantic/FastAPI). Nessun export Excel; risultati via API.
"""
import csv
import io
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

import pandas as pd
from flask import Flask, jsonify, request, abort

from app.campaigns import get_all_campaigns_by_segment
from app.excel_parser import parse_and_segment
from app.models import Segment, SegmentedCustomer
from app.operator_refinement import get_indicatori_definitions, segment_from_operator_input

try:
    from flask_cors import CORS
except ImportError:
    CORS = None

# In-memory store (in produzione usare PostgreSQL)
_store: dict[str, list[SegmentedCustomer]] = {}
# Feedback operatore per segmento: analysis_id -> row_index -> { segment?, ...campi_manuali, updated_at }
# Usato per apprendere e aggiornare lo scoring (modello statistico / aggiustamento pesi)
_operator_feedback: dict[str, dict[int, dict]] = {}

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


def _effective_revenue(c) -> float:
    """Revenue del cliente: da campo revenue o, se mancante, spesa_media * numero_notti."""
    if c.revenue is not None and c.revenue > 0:
        return float(c.revenue)
    if c.spesa_media is not None and c.numero_notti is not None and c.numero_notti > 0:
        return c.spesa_media * c.numero_notti
    return 0.0


def _scores_with_operator_boost(scores_dict: dict, chosen_segment: str) -> dict:
    """Dato lo scoring originale e il segmento da feedback operatore, restituisce score con boost per far riflettere le % l'input operatore. Premium (deprecato) → leisure."""
    key_map = {"Business": "business", "Leisure": "leisure", "Coppia": "coppia", "Famiglia": "famiglia", "Premium": "leisure"}
    key = key_map.get(chosen_segment)
    if not key or key not in scores_dict:
        return scores_dict
    out = dict(scores_dict)
    out[key] = (out.get(key) or 0) + 15
    return out


def _effective_adr(c) -> float:
    """ADR del cliente: spesa_media o, se mancante, revenue / numero_notti."""
    if c.spesa_media is not None and c.spesa_media > 0:
        return float(c.spesa_media)
    if c.revenue is not None and c.numero_notti is not None and c.numero_notti > 0:
        return c.revenue / c.numero_notti
    return 0.0


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
        revenues = [_effective_revenue(c) for c in list_c]
        adrs = [_effective_adr(c) for c in list_c if _effective_adr(c) > 0]
        rev_tot = sum(revenues)
        adr = sum(adrs) / len(adrs) if adrs else 0
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
    adr_sum = sum(_effective_adr(c) for c in customers)
    adr_count = sum(1 for c in customers if _effective_adr(c) > 0)
    overall_adr = adr_sum / adr_count if adr_count else 0
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
            "anticipo_giorni": c.anticipo_giorni,
            "prenotante": c.prenotante,
            "numero_bambini": c.numero_bambini,
        })
    return jsonify(out)


@app.route("/api/analysis/<analysis_id>/customer/<int:row_index>", methods=["GET"])
def get_customer(analysis_id: str, row_index: int):
    """Dettaglio singolo cliente per scheda (percentuali segmenti). Include feedback operatore se presente."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    found = next((c for c in customers if c.row_index == row_index), None)
    if not found:
        abort(404, "Cliente non trovato")
    feedback = (_operator_feedback.get(analysis_id) or {}).get(row_index)
    segment_display = found.segment.value
    scores_out = found.scores.to_dict()
    if feedback and feedback.get("segment"):
        seg = feedback["segment"]
        if seg == "Premium":
            seg = "Leisure"  # retrocompat: Premium fusionato in Leisure
        try:
            Segment(seg)  # valida
            segment_display = seg
            scores_out = _scores_with_operator_boost(scores_out, seg)
        except ValueError:
            pass
    out = {
        "row_index": found.row_index,
        "segment": segment_display,
        "scores": scores_out,
        "numero_notti": found.numero_notti,
        "numero_ospiti": found.numero_ospiti,
        "canale": found.canale,
        "giorno_arrivo": found.giorno_arrivo,
        "storico_soggiorni": found.storico_soggiorni,
        "spesa_media": found.spesa_media,
        "cliente_id": found.cliente_id,
        "nome_cliente": found.nome_cliente,
        "data_arrivo": found.data_arrivo,
        "categoria_camera": found.categoria_camera,
        "revenue": found.revenue,
        "anticipo_giorni": found.anticipo_giorni,
        "prenotante": found.prenotante,
        "numero_bambini": found.numero_bambini,
        "operator_feedback": feedback,
    }
    return jsonify(out)


@app.route("/api/analysis/<analysis_id>/customer/<int:row_index>/feedback", methods=["POST"])
def save_operator_feedback(analysis_id: str, row_index: int):
    """
    Salva input operatore: note di prenotazione, richieste speciali, servizi, indicatori.
    Il segmento viene ricalcolato solo da indicatori e testo (note/richieste).
    Body: { "note_prenotazione"?, "richieste_speciali"?, "servizi_selezionati"?, "indicatori"?: [] }
    """
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    found = next((c for c in customers if c.row_index == row_index), None)
    if not found:
        abort(404, "Cliente non trovato")
    data = request.get_json(silent=True) or {}
    note_prenotazione = (data.get("note_prenotazione") or "").strip() or None
    richieste_speciali = (data.get("richieste_speciali") or "").strip() or None
    servizi_selezionati = data.get("servizi_selezionati")
    if servizi_selezionati is not None and not isinstance(servizi_selezionati, list):
        servizi_selezionati = [servizi_selezionati]
    indicatori = data.get("indicatori")
    if indicatori is not None and not isinstance(indicatori, list):
        indicatori = [indicatori] if indicatori else []

    segment_computed = None
    if indicatori or note_prenotazione or richieste_speciali or servizi_selezionati:
        segment_computed = segment_from_operator_input(
            indicatori=indicatori or None,
            note_prenotazione=note_prenotazione,
            richieste_speciali=richieste_speciali,
            servizi_selezionati=servizi_selezionati,
        ).value

    segment_final = segment_computed
    if segment_final is None and analysis_id in _operator_feedback and row_index in _operator_feedback[analysis_id]:
        segment_final = _operator_feedback[analysis_id][row_index].get("segment")

    if analysis_id not in _operator_feedback:
        _operator_feedback[analysis_id] = {}
    payload = {
        "note_prenotazione": note_prenotazione,
        "richieste_speciali": richieste_speciali,
        "servizi_selezionati": servizi_selezionati,
        "indicatori": indicatori,
        "segment_computed": segment_computed,
        "segment": segment_final,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    _operator_feedback[analysis_id][row_index] = payload
    return jsonify({
        "ok": True,
        "message": "Input operatore salvato. Segmento aggiornato in base a note, richieste e indicatori." if segment_final else "Input salvato.",
        "feedback": payload,
        "segment": segment_final,
    })


@app.route("/api/analysis/<analysis_id>/customer/<int:row_index>/refresh", methods=["POST"])
def refresh_customer_profile(analysis_id: str, row_index: int):
    """Simula aggiornamento profilo durante il soggiorno (ricalcolo segmentazione)."""
    customers = _store.get(analysis_id)
    if not customers:
        abort(404, "Analisi non trovata")
    found = next((c for c in customers if c.row_index == row_index), None)
    if not found:
        abort(404, "Cliente non trovato")
    # Per ora restituisce gli stessi dati; in futuro qui si può ricalcolare con dati aggiornati
    return jsonify({
        "ok": True,
        "message": "Profilo aggiornato. Elaborato con i dati attuali del soggiorno.",
        "customer": {
            "row_index": found.row_index,
            "segment": found.segment.value,
            "scores": found.scores.to_dict(),
            "numero_notti": found.numero_notti,
            "numero_ospiti": found.numero_ospiti,
            "canale": found.canale,
            "giorno_arrivo": found.giorno_arrivo,
            "storico_soggiorni": found.storico_soggiorni,
            "spesa_media": found.spesa_media,
            "cliente_id": found.cliente_id,
            "nome_cliente": found.nome_cliente,
            "data_arrivo": found.data_arrivo,
            "categoria_camera": found.categoria_camera,
            "revenue": found.revenue,
            "anticipo_giorni": found.anticipo_giorni,
            "prenotante": found.prenotante,
            "numero_bambini": found.numero_bambini,
        },
    })


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


@app.route("/api/operator-indicators")
def list_operator_indicators():
    """Elenco indicatori comportamentali per la scheda (note, richieste, servizi → segmento)."""
    return jsonify({"indicatori": get_indicatori_definitions()})


# Gestione errori HTTP per restituire JSON
@app.errorhandler(400)
@app.errorhandler(404)
def json_error(e):
    return jsonify({"detail": e.description or str(e)}), e.code


@app.errorhandler(500)
def handle_500(e):
    """Restituisce JSON anche per errori 500 così il frontend può mostrare il messaggio."""
    detail = getattr(e, "description", None) or str(e) if e else "Errore interno del server"
    return jsonify({"detail": detail}), 500


@app.errorhandler(Exception)
def handle_exception(e):
    """Cattura eccezioni non gestite e restituisce 500 in JSON."""
    app.logger.exception(e)
    return jsonify({"detail": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
