# Flusso backend: note di prenotazione e percentuali

## Perché le percentuali si aggiornano solo dopo "Salva"

Le percentuali in scheda (le "prime due categorie") sono calcolate dagli **score** che il backend restituisce. Il backend non ricalcola nulla finché non invii il modulo con **"Salva input e aggiorna %"**.

1. **Modifichi** le note di prenotazione (o richieste speciali / servizi / indicatori) nella scheda.
2. **Clicchi "Salva input e aggiorna %"** → il frontend invia `POST /api/analysis/<id>/customer/<row_index>/feedback` con il corpo (es. `note_prenotazione`, `richieste_speciali`, `servizi_selezionati`, `indicatori`).
3. **Backend (POST feedback)**:
   - Estrae dagli indicatori e dal testo delle note/richieste le **parole chiave** (vedi legenda in scheda).
   - Determina un **segmento** in base a quali indicatori sono presenti (Business → Famiglia → Coppia → Leisure).
   - Salva il feedback (in memoria) incluso il segmento calcolato.
4. **Frontend** dopo il salvataggio fa un **refetch** del cliente: `GET /api/analysis/<id>/customer/<row_index>`.
5. **Backend (GET customer)**:
   - Se esiste feedback con un segmento, prende gli score originali (da Excel/parsing) e applica un **boost** (+15) allo score del segmento scelto.
   - Restituisce questi score modificati nella risposta.
6. Il frontend mostra le percentuali a partire da questi score: quindi **vedi il cambiamento solo dopo il refetch**, cioè dopo aver salvato.

Se modifichi solo il testo senza salvare, il backend non riceve nulla e le percentuali restano quelle attuali (o quelle dell’ultimo salvataggio).

## Come vengono usate le note di prenotazione

- Il testo delle **note di prenotazione** e delle **richieste speciali** viene passato a `_parse_indicators_from_text()` in `operator_refinement.py`.
- La funzione cerca **sottostringhe** (parole/frasi) nel testo (minuscolo). Esempi: "lavoro", "fattura aziendale", "bambini", "anniversario", "suite", "parcheggio".
- Ogni corrispondenza viene mappata a un **indicatore** (es. "lavoro" → Business, "anniversario" → Coppia). Se non trova nessuna parola riconosciuta, il segmento assegnato è **Leisure** (default).
- Per vedere un cambiamento chiaro nelle percentuali, usa parole della **legenda** in scheda; se il testo non contiene nessuna di quelle parole, il segmento resta Leisure e le percentuali cambiano poco (solo il boost su Leisure).

## Riepilogo

| Azione | Effetto |
|--------|--------|
| Modificare note/richieste e **non** salvare | Nessun effetto; percentuali invariate. |
| Modificare e cliccare **"Salva input e aggiorna %"** | Backend ricalcola il segmento, salva il feedback, al refetch restituisce score con boost → le percentuali si aggiornano. |
