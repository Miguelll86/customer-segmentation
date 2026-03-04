"""
Raffinamento segmento da input operatore: note di prenotazione, richieste speciali, servizi, indicatori comportamentali.
Regole di priorità in caso di sovrapposizione:
  Motivazione aziendale → Business prevale.
  Minori presenti → Famiglie prevale.
  Esperienza romantica dichiarata → Coppie prevale.
  Assenza indicatori specifici → Leisure (include ex-Premium) default.
"""
from app.models import Segment


# Indicatori comportamentali per segmento (chiave -> segmento)
INDICATORI_BUSINESS = {
    "arrivo_tarda_serata_lavoro",
    "fattura_aziendale",
    "scrivania_ambiente_silenzioso",
    "sala_meeting",
    "soggiorni_brevi_infrasettimanali",
    "checkin_checkout_rapido",
}
INDICATORI_FAMIGLIA = {
    "camera_tripla_quadrupla",
    "bambini",
    "culla_letto_aggiunto",
    "colazione_piu_componenti",
    "spa_con_minori",
}
INDICATORI_COPPIA = {
    "anniversario_occasione_romantica",
    "camera_tranquilla_superiore",
    "spa_coppia",
    "cena_romantica",
    "late_checkout_weekend",
}
# Leisure include ex-Premium (fusionati)
INDICATORI_LEISURE = {
    "attrazioni_turistiche",
    "parcheggio",
    "weekend",
    "tariffa_flessibile",
    "colazione_inclusa",
    "pet_friendly",
    "suite_executive",
    "servizi_personalizzati",
    "transfer_privato",
    "spa_esclusiva",
    "upgrade_volontario",
    "spesa_accessoria_elevata",
}

# Ordine di priorità per sovrapposizione (primo che matcha vince)
PRIORITA_INDICATORI = [
    (INDICATORI_BUSINESS, Segment.BUSINESS),
    (INDICATORI_FAMIGLIA, Segment.FAMIGLIA),
    (INDICATORI_COPPIA, Segment.COPPIA),
    (INDICATORI_LEISURE, Segment.LEISURE),
]

# Keyword in note/richieste (testo libero) -> indicatore
KEYWORDS_TO_INDICATOR = [
    # Business
    ("arrivo tardi", "arrivo_tarda_serata_lavoro"),
    ("tarda serata", "arrivo_tarda_serata_lavoro"),
    ("lavoro", "arrivo_tarda_serata_lavoro"),
    ("fattura aziendale", "fattura_aziendale"),
    ("fatturazione aziendale", "fattura_aziendale"),
    ("scrivania", "scrivania_ambiente_silenzioso"),
    ("silenzioso", "scrivania_ambiente_silenzioso"),
    ("lavorare", "scrivania_ambiente_silenzioso"),
    ("sala meeting", "sala_meeting"),
    ("meeting", "sala_meeting"),
    ("check-in rapido", "checkin_checkout_rapido"),
    ("check-out rapido", "checkin_checkout_rapido"),
    # Famiglia
    ("camera tripla", "camera_tripla_quadrupla"),
    ("camera quadrupla", "camera_tripla_quadrupla"),
    ("tripla", "camera_tripla_quadrupla"),
    ("quadrupla", "camera_tripla_quadrupla"),
    ("bambini", "bambini"),
    ("bambino", "bambini"),
    ("culla", "culla_letto_aggiunto"),
    ("letto aggiunto", "culla_letto_aggiunto"),
    ("letto aggiuntivo", "culla_letto_aggiunto"),
    ("colazione per", "colazione_piu_componenti"),
    # Coppia
    ("anniversario", "anniversario_occasione_romantica"),
    ("romantico", "anniversario_occasione_romantica"),
    ("romantica", "anniversario_occasione_romantica"),
    ("spa coppia", "spa_coppia"),
    ("coppia", "spa_coppia"),
    ("cena romantica", "cena_romantica"),
    ("late check-out", "late_checkout_weekend"),
    ("late checkout", "late_checkout_weekend"),
    # Premium
    ("suite", "suite_executive"),
    ("executive", "suite_executive"),
    ("transfer privato", "transfer_privato"),
    ("transfer", "transfer_privato"),
    ("spa esclusiva", "spa_esclusiva"),
    ("upgrade", "upgrade_volontario"),
    # Leisure
    ("attrazioni", "attrazioni_turistiche"),
    ("turismo", "attrazioni_turistiche"),
    ("parcheggio", "parcheggio"),
    ("pet friendly", "pet_friendly"),
    ("cane", "pet_friendly"),
    ("animale", "pet_friendly"),
]


# Servizi selezionati (etichetta UI) -> indicatore
SERVIZI_TO_INDICATOR = {
    "colazione inclusa": "colazione_inclusa",
    "sala meeting": "sala_meeting",
    "spa": "spa_coppia",  # generico, può essere anche spa_esclusiva
    "transfer": "transfer_privato",
    "culla": "culla_letto_aggiunto",
    "letto aggiunto": "culla_letto_aggiunto",
    "late check-out": "late_checkout_weekend",
    "cena": "cena_romantica",
    "parcheggio": "parcheggio",
    "pet friendly": "pet_friendly",
    "fattura aziendale": "fattura_aziendale",
    "upgrade": "upgrade_volontario",
}


def _servizi_to_indicators(servizi: list[str]) -> set[str]:
    """Mappa servizi selezionati (etichette) a indicatori."""
    if not servizi:
        return set()
    out = set()
    for s in servizi:
        if not s:
            continue
        key = str(s).strip().lower()
        if key in SERVIZI_TO_INDICATOR:
            out.add(SERVIZI_TO_INDICATOR[key])
    return out


def _parse_indicators_from_text(text: str) -> set[str]:
    """Estrae indicatori da testo libero (note, richieste) tramite keyword."""
    if not text or not isinstance(text, str):
        return set()
    t = text.strip().lower()
    found = set()
    for keyword, indicatore in KEYWORDS_TO_INDICATOR:
        if keyword in t:
            found.add(indicatore)
    return found


def segment_from_operator_input(
    indicatori: list[str] | None = None,
    note_prenotazione: str | None = None,
    richieste_speciali: str | None = None,
    servizi_selezionati: list[str] | None = None,
) -> Segment:
    """
    Determina il segmento in base a indicatori, servizi, note e richieste.
    Applica le regole di priorità: Business > Famiglie > Coppie > Leisure (default).
    """
    indicatori_set: set[str] = set()
    if indicatori:
        indicatori_set = {str(i).strip() for i in indicatori if i}
    if servizi_selezionati:
        indicatori_set |= _servizi_to_indicators(servizi_selezionati)
    if note_prenotazione:
        indicatori_set |= _parse_indicators_from_text(note_prenotazione)
    if richieste_speciali:
        indicatori_set |= _parse_indicators_from_text(richieste_speciali)

    for indicatori_seg, segment in PRIORITA_INDICATORI:
        if indicatori_set & indicatori_seg:
            return segment
    return Segment.LEISURE


def get_indicatori_definitions() -> list[dict]:
    """Restituisce le definizioni degli indicatori per la UI (etichetta, chiave, segmento)."""
    return [
        {"key": k, "segment": "Business", "label": _label_business(k)} for k in sorted(INDICATORI_BUSINESS)
    ] + [
        {"key": k, "segment": "Famiglia", "label": _label_famiglia(k)} for k in sorted(INDICATORI_FAMIGLIA)
    ] + [
        {"key": k, "segment": "Coppia", "label": _label_coppia(k)} for k in sorted(INDICATORI_COPPIA)
    ] + [
        {"key": k, "segment": "Leisure", "label": _label_leisure_or_premium(k)} for k in sorted(INDICATORI_LEISURE)
    ]


def _label_business(k: str) -> str:
    labels = {
        "arrivo_tarda_serata_lavoro": "Arrivo tarda serata per lavoro",
        "fattura_aziendale": "Richiesta fattura aziendale",
        "scrivania_ambiente_silenzioso": "Scrivania / ambiente silenzioso per lavorare",
        "sala_meeting": "Interesse sala meeting",
        "soggiorni_brevi_infrasettimanali": "Soggiorno breve infrasettimanale",
        "checkin_checkout_rapido": "Check-in/out rapido",
    }
    return labels.get(k, k.replace("_", " ").title())


def _label_famiglia(k: str) -> str:
    labels = {
        "camera_tripla_quadrupla": "Camera tripla o quadrupla",
        "bambini": "Presenza bambini",
        "culla_letto_aggiunto": "Culla o letto aggiunto",
        "colazione_piu_componenti": "Colazione per più componenti",
        "spa_con_minori": "Accesso spa con minori",
    }
    return labels.get(k, k.replace("_", " ").title())


def _label_coppia(k: str) -> str:
    labels = {
        "anniversario_occasione_romantica": "Anniversario / occasione romantica",
        "camera_tranquilla_superiore": "Camera tranquilla o superiore",
        "spa_coppia": "Percorso spa di coppia",
        "cena_romantica": "Cena romantica",
        "late_checkout_weekend": "Late check-out weekend",
    }
    return labels.get(k, k.replace("_", " ").title())


def _label_premium(k: str) -> str:
    labels = {
        "suite_executive": "Suite o categoria executive",
        "servizi_personalizzati": "Servizi personalizzati",
        "transfer_privato": "Transfer privato",
        "spa_esclusiva": "Spa in esclusiva",
        "upgrade_volontario": "Upgrade volontario",
        "spesa_accessoria_elevata": "Elevata spesa accessoria",
    }
    return labels.get(k, k.replace("_", " ").title())


def _label_leisure(k: str) -> str:
    labels = {
        "attrazioni_turistiche": "Interesse attrazioni turistiche",
        "parcheggio": "Richiesta parcheggio",
        "weekend": "Prenotazione weekend",
        "tariffa_flessibile": "Tariffa flessibile",
        "colazione_inclusa": "Colazione inclusa",
        "pet_friendly": "Cane / camera pet friendly",
    }
    return labels.get(k, k.replace("_", " ").title())


def _label_leisure_or_premium(k: str) -> str:
    """Etichetta per indicatori Leisure (include ex-Premium)."""
    return _label_premium(k) if k in {
        "suite_executive", "servizi_personalizzati", "transfer_privato",
        "spa_esclusiva", "upgrade_volontario", "spesa_accessoria_elevata"
    } else _label_leisure(k)
