"""
Campagne marketing per segmento – Hotel Barion (Bari, Puglia).
Basate su servizi reali: area congressi, Barion Wellness, ristorante cucina pugliese,
vista mare, parcheggio gratuito, tour e lidi convenzionati. Vedi www.barionhotel.it
"""
from app.models import Segment, CampaignItem

# 4 campagne per segmento – focus upselling: upgrade, extra, pacchetti a valore aggiunto
DEFAULT_CAMPAIGNS: dict[Segment, list[dict]] = {
    Segment.BUSINESS: [
        {"titolo": "Upgrade a Deluxe con vista mare", "descrizione": "Passa a camera Deluxe o Superior: spazio in più, scrivania, vista mare. Supplemento contenuto; produttività e comfort. Proponi al check-in o in prenotazione.", "tipo": "upgrade"},
        {"titolo": "Pacchetto meeting: sala + coffee break + pranzo", "descrizione": "Vendi l’intero pacchetto: area congressi + coffee break e pranzo in ristorante. Un’unica soluzione a valore aggiunto invece della sola camera.", "tipo": "pacchetto"},
        {"titolo": "Transfer aeroporto / stazione", "descrizione": "Offri navetta o transfer su prenotazione (aeroporto Bari, stazione Torre a Mare). Servizio a pagamento che semplifica l’arrivo e genera extra revenue.", "tipo": "servizio"},
        {"titolo": "Cena in ristorante dopo il meeting", "descrizione": "Upsell serale: cena in ristorante cucina pugliese invece della cena fuori. Menù business o degustazione. Aumenta il revenue per coperto.", "tipo": "upsell"},
    ],
    Segment.LEISURE: [
        {"titolo": "Upgrade a camera vista mare", "descrizione": "Proponi il passaggio a Deluxe/Superior con vista mare: differenza di prezzo chiara, valore percepito alto. Ideale per soggiorni di 2+ notti.", "tipo": "upgrade"},
        {"titolo": "Tour o escursione in aggiunta", "descrizione": "Vendi tour guidati (Polignano, Alberobello, grotte, Salento) o gite in barca come extra. Pacchetto soggiorno + esperienza a prezzo conveniente rispetto al prezzo separato.", "tipo": "upsell"},
        {"titolo": "Mezza pensione o cena in ristorante", "descrizione": "Aggiungi colazione plus cena (mezza pensione) o almeno una cena in ristorante cucina pugliese. Upsell a tavola con margine sul ristorante.", "tipo": "pacchetto"},
        {"titolo": "Suite o Deluxe con servizi inclusi", "descrizione": "Proponi la categoria superiore (Suite/Deluxe) con minibar gratuito e vista mare come pacchetto premium. Prezzo ben posizionato per massimizzare l'ADR.", "tipo": "upgrade"},
        {"titolo": "Pacchetto wellness + cucina pugliese", "descrizione": "Vendi accesso Barion Wellness + cena degustazione in ristorante come pacchetto benessere e gusto. Alto valore percepito, forte margine.", "tipo": "pacchetto"},
        {"titolo": "Transfer e esperienze su misura", "descrizione": "Offri transfer dedicati (aeroporto, tour) e esperienze esclusive (Venture Vibes, Pugliamare) a prezzo premium. Servizi a valore aggiunto ad alto margine.", "tipo": "upsell"},
        {"titolo": "Late checkout e servizi concierge", "descrizione": "Monetizza late checkout e servizi su richiesta (prenotazioni ristoranti, transfer): pacchetto concierge o singoli supplementi. Revenue da servizi.", "tipo": "servizio"},
        {"titolo": "Lido convenzionato: pass giornaliero", "descrizione": "Vendi l’accesso a lidi convenzionati (Mama Luna Beach ecc.) come add-on: pass giornaliero o pacchetto multi-giorno. Revenue extra e guest più soddisfatto.", "tipo": "upsell"},
    ],
    Segment.COPPIA: [
        {"titolo": "Upgrade camera con vista + late checkout", "descrizione": "Pacchetto a pagamento: camera Superior/Deluxe vista mare + late checkout (es. entro le 16). Un unico prezzo per un weekend di qualità in più.", "tipo": "upgrade"},
        {"titolo": "Cena romantica + Barion Wellness", "descrizione": "Vendi il pacchetto coppia: cena per due in ristorante + accesso area benessere. Prezzo pacchetto vantaggioso rispetto al prezzo separato; forte upsell.", "tipo": "upsell"},
        {"titolo": "Supplemento minibar / champagne in camera", "descrizione": "Offri bottiglia di champagne o upgrade minibar in camera come sorpresa (anniversario, richiesta). Extra a prezzo premium, facile da proporre al check-in.", "tipo": "upsell"},
        {"titolo": "Tour o esperienza per due", "descrizione": "Aggiungi un’esperienza: tour borghi, gita in barca, degustazione. Vendila come “esperienza per due” a prezzo coppia; incrementa il ticket medio.", "tipo": "pacchetto"},
    ],
    Segment.FAMIGLIA: [
        {"titolo": "Upgrade a camera family o collegata", "descrizione": "Proponi camera più grande o due camere collegate a prezzo family. Maggiore comfort e revenue per notte; ideale per 3+ notti.", "tipo": "upgrade"},
        {"titolo": "Mezza pensione famiglia", "descrizione": "Vendi colazione + cena per tutta la famiglia (mezza pensione). Prezzo per adulto e bambino; margine sul ristorante e soddisfazione per i genitori.", "tipo": "pacchetto"},
        {"titolo": "Escursione o tour per la famiglia", "descrizione": "Vendi come extra tour a grotte, trulli o lido family: pacchetto “giornata in famiglia” a prezzo unico. Aumenta il valore del soggiorno e il revenue.", "tipo": "upsell"},
        {"titolo": "Culla, letto aggiunto, colazione bambini", "descrizione": "Monetizza i servizi family: culla/letto aggiunto a prezzo chiaro; colazione bambini inclusa nel pacchetto. Upsell su ogni componente del soggiorno.", "tipo": "upsell"},
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
