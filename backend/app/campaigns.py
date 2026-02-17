"""
Generazione automatica campagne marketing per segmento.
Modificabili da backend (configurabili), tracciabili, collegabili a email/CRM.
"""
from app.models import Segment, CampaignItem

# Campagne predefinite per segmento (modificabili da config/DB in seguito)
DEFAULT_CAMPAIGNS: dict[Segment, list[dict]] = {
    Segment.BUSINESS: [
        {"titolo": "Pacchetto corporate midweek", "descrizione": "Tariffa riservata per soggiorni Lun-Mer con colazione e Wi-Fi incluso.", "tipo": "pacchetto"},
        {"titolo": "Sconto ricorrente aziendale", "descrizione": "Sconto del 15% per prenotazioni ripetute con contratto aziendale.", "tipo": "sconto"},
        {"titolo": "Upgrade veloce", "descrizione": "Upgrade a camera superiore al check-in se disponibile (supplemento ridotto).", "tipo": "upgrade"},
    ],
    Segment.LEISURE: [
        {"titolo": "Offerta stagionale", "descrizione": "Promozione early booking per le prossime stagioni con sconto fino al 20%.", "tipo": "stagionale"},
        {"titolo": "Esperienze locali", "descrizione": "Pacchetto esperienze (tour, degustazioni) in collaborazione con partner locali.", "tipo": "esperienza"},
        {"titolo": "Sconto prenotazione anticipata", "descrizione": "Fino al 25% di sconto per prenotazioni con almeno 30 giorni di anticipo.", "tipo": "early_booking"},
    ],
    Segment.COPPIA: [
        {"titolo": "Pacchetto romantico", "descrizione": "Notte romantica con champagne, fiori e late checkout incluso.", "tipo": "pacchetto"},
        {"titolo": "Cena + Spa", "descrizione": "Dinner per due e accesso spa con sconto dedicato alle coppie.", "tipo": "esperienza"},
        {"titolo": "Late checkout", "descrizione": "Check-out entro le 16:00 senza supplemento per soggiorni weekend.", "tipo": "servizio"},
    ],
    Segment.FAMIGLIA: [
        {"titolo": "Bambini gratis", "descrizione": "Soggiorno gratuito per bambini sotto i 12 anni in camera con i genitori.", "tipo": "sconto"},
        {"titolo": "Pacchetto family", "descrizione": "Family room + colazione bambini + attività kids club incluso.", "tipo": "pacchetto"},
        {"titolo": "Attività per bambini", "descrizione": "Animazione e laboratori per bambini nei weekend e in alta stagione.", "tipo": "esperienza"},
    ],
    Segment.PREMIUM: [
        {"titolo": "Concierge dedicato", "descrizione": "Concierge personale per prenotazioni ristoranti, transfer e esperienze su misura.", "tipo": "servizio"},
        {"titolo": "Upgrade prioritario", "descrizione": "Upgrade a suite o categoria superiore in base a disponibilità (priorità alta).", "tipo": "upgrade"},
        {"titolo": "Evento esclusivo", "descrizione": "Inviti a eventi riservati (degustazioni, serate) durante il soggiorno.", "tipo": "evento"},
        {"titolo": "Esperienza personalizzata", "descrizione": "Itinerari e attività cuciti su misura dal team concierge.", "tipo": "esperienza"},
    ],
}


def get_campaigns_for_segment(segment: Segment) -> list[CampaignItem]:
    """Restituisce le campagne suggerite per il segmento (modificabili da backend)."""
    raw = DEFAULT_CAMPAIGNS.get(segment, [])
    return [
        CampaignItem(segmento=segment, titolo=c["titolo"], descrizione=c["descrizione"], tipo=c["tipo"])
        for c in raw
    ]


def get_all_campaigns_by_segment() -> dict[Segment, list[CampaignItem]]:
    """Restituisce tutte le campagne per ogni segmento (per dashboard)."""
    return {seg: get_campaigns_for_segment(seg) for seg in Segment}
