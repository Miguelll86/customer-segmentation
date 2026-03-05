# Come funziona l’applicativo e algoritmo di segmentazione

## 1. Flusso generale dell’applicativo

1. **Upload**  
   L’utente carica un file Excel/CSV con i dati degli arrivi (export dal gestionale/PMS).  
   Backend: `POST /api/upload` → legge il file, lo passa a `parse_and_segment()`.

2. **Parsing e segmentazione**  
   - **excel_parser**: mappa le colonne del file (nomi flessibili, vedi `FORMATO-EXCEL-GESTIONALE.md`), estrae per ogni riga: numero notti, ospiti, canale, giorno arrivo, spesa/totale, categoria camera, anticipo giorni, prenotante, numero bambini, date, ecc.  
   - Calcola **soglia top 25%** sulla spesa (per regole “alta spesa”) e **media spesa** (sotto/sopra media).  
   - Per ogni riga chiama **scoring.compute_scores()** con tutti i campi disponibili.  
   - **scoring.assign_segment()** assegna un solo segmento (quello con punteggio massimo; in parità usa la priorità).  
   - Output: lista di `SegmentedCustomer` (segmento + punteggi per tutti e 4 i segmenti) salvata in memoria con un `analysis_id`.

3. **Dashboard**  
   Il frontend usa `analysis_id` per:  
   - KPI (arrivi, revenue, ADR, valore cliente medio),  
   - distribuzione segmenti (grafici),  
   - tabella clienti con filtri.  
   Dati da: `GET /api/analysis/<id>/overview`, `/customers`, `/count`, ecc.

4. **Scheda cliente (modal)**  
   Clic sul nome → dettaglio singolo cliente:  
   - Segmento assegnato (eventualmente aggiornato dall’operatore).  
   - **Prime due categorie**: le due con percentuale più alta (calcolate dagli score: ogni score / somma * 100).  
   - Se l’operatore ha salvato un feedback, gli score restituiti hanno un **boost +15** sul segmento scelto → le percentuali riflettono l’input operatore.  
   - **Market Intelligence**: 5 campagne (3 dalla categoria con % più alta, 2 dalla seconda).  
   - Form **input operatore**: note prenotazione, richieste speciali, servizi, indicatori comportamentali. Salvataggio → ricalcolo segmento da indicatori/keyword e aggiornamento percentuali (dopo refetch).

5. **Raffinamento operatore**  
   - L’operatore inserisce note, richieste, servizi, indicatori (e opzionalmente in passato c’era override segmento; ora rimosso).  
   - Backend: `POST .../feedback` → `operator_refinement.segment_from_operator_input()` estrae indicatori da testo (keyword) e da servizi, applica le **priorità** (Business > Famiglia > Coppia > Leisure) e determina il segmento.  
   - Il segmento così calcolato viene salvato e usato per boost degli score e per le campagne “dedicate”.

---

## 2. Segmenti

L’applicativo usa **4 segmenti** (Leisure include l’ex-Premium):

| Segmento   | Significato sintetico                          |
|-----------|-----------------------------------------------|
| Business  | Viaggio lavoro, canali corporate/GDS, 1 ospite, soggiorni brevi infrasettimanali, last minute. |
| Leisure   | Turismo, OTA, alta spesa/camera premium, direct, soggiorni lunghi (ex-Premium incluso).        |
| Coppia    | 2 ospiti, weekend, 1–3 notti, nessun bambino, canale leisure.                                  |
| Famiglia  | 3+ ospiti, bambini, periodo vacanze, weekend, prenotazione in anticipo.                         |

In **parità di punteggio** l’ordine di priorità è: **Business > Famiglia > Coppia > Leisure**.

---

## 3. Algoritmo di scoring (completo)

L’algoritmo è un **punteggio ponderato per segmento**: ogni regola aggiunge **punti** a uno o più dei 4 segmenti.  
Il segmento assegnato è quello con **somma massima**; in parità si usa `SEGMENT_PRIORITY`.

### 3.1 Input usati dallo scoring

- `numero_notti`, `numero_ospiti`, `canale`, `giorno_arrivo` (giorno della settimana)  
- `spesa_media`, `categoria_camera`  
- `threshold_top25` (soglia 75° percentile sulla spesa), `media_spesa` (media), `is_vacation_period` (mese in 1,6,7,8,12)  
- Opzionali: `anticipo_giorni`, `prenotante`, `numero_bambini`

### 3.2 Regole per combinazione **giorno arrivo + numero notti**

| Condizione              | Business | Leisure | Coppia | Famiglia |
|-------------------------|----------|---------|--------|----------|
| Weekend + 1 notte       | +2       | —       | +1     | —        |
| Weekend + 2–3 notti     | —        | +2      | +3     | —        |
| Weekend + ≥4 notti      | —        | +1      | —      | +2       |
| Infrasettimanale + 1–2 notti | +3 | —       | —      | —        |
| Infrasettimanale + ≥3 notti  | — | +1      | —      | +1       |

### 3.3 Regole **Business**

| Condizione | Punti |
|------------|-------|
| Giorno arrivo infrasettimanale (lun–mer) | +2 |
| Numero ospiti = 1 | +3 |
| 1 ≤ numero notti ≤ 2 | +2 |
| Canale corporate/GDS/aziendale | +2 |
| Anticipo 0–7 giorni (last minute) | +2 |
| Prenotante contiene agenzia/azienda/corporate/tour operator/gds/business | +2 |

### 3.4 Regole **Leisure** (include ex-Premium)

| Condizione | Punti |
|------------|-------|
| Numero notti ≥ 3 | +2 |
| Giorno arrivo weekend | +1 |
| Canale OTA/booking/expedia/leisure | +2 |
| Spesa media < media_spesa | +1 |
| Anticipo ≥ 30 giorni | +1 |
| Prenotante contiene cliente/guest | +1 |
| Spesa ≥ soglia top 25% | +4 |
| Spesa ≥ media | +1 |
| Numero notti ≥ 4 | +2 |
| Canale direct/diretto/sito/web/phone | +2 |
| Categoria camera alta (suite, deluxe, premium, superior, executive, ecc.) | +2 |

### 3.5 Regole **Coppia**

| Condizione | Punti |
|------------|-------|
| Numero ospiti = 2 | +3 |
| 1 ≤ numero notti ≤ 3 | +2 |
| Giorno arrivo weekend (ven–dom) | +3 |
| Canale OTA/booking/expedia/leisure | +1 |
| Numero bambini = 0 e ospiti = 2 | +2 |

### 3.6 Regole **Famiglia**

| Condizione | Punti |
|------------|-------|
| Numero ospiti ≥ 3 | +3 |
| Numero notti ≥ 3 | +2 |
| Giorno arrivo weekend | +2 |
| Periodo vacanze (gen, giu, lug, ago, dic) | +2 |
| Numero bambini ≥ 1 | +4 |
| Anticipo ≥ 30 giorni | +1 |

---

## 4. Quante “combinazioni” ci sono

Non c’è un unico numero “combinazioni” perché:

- Lo **scoring** non è una tabella di combinazioni discrete: ogni regola può attivarsi in modo indipendente e i punti si **sommano**.  
- I **fattori** che entrano nelle regole sono molti; una stessa riga può far scattare decine di condizioni.

Si può comunque dare una stima per **dimensione** e **numero di regole**:

- **Fattori in ingresso** (con valori tipici):  
  - Giorno arrivo: 7 valori (lun–dom)  
  - Numero notti: 1, 2, 3, 4, … (es. 1–14)  
  - Numero ospiti: 1, 2, 3, 4+  
  - Canale: corporate/GDS, OTA/leisure, direct (+ assente/altro)  
  - Spesa: sotto media / circa media / sopra media / top 25%  
  - Categoria camera: standard vs alta (suite, deluxe, …)  
  - Anticipo: last minute (0–7), medio (8–29), anticipo (30+)  
  - Prenotante: tipo (cliente, agenzia, azienda, …)  
  - Numero bambini: 0, 1+  
  - Periodo: vacanze vs no  

- **Regole di scoring** (condizioni distinte che assegnano punti):  
  - Giorno+notti: 5 blocchi  
  - Business: 6 regole  
  - Leisure: 11 regole  
  - Coppia: 5 regole  
  - Famiglia: 6 regole  

In totale ci sono **circa 33+ regole** che possono applicarsi a una singola prenotazione; più fattori opzionali (anticipo, prenotante, bambini) aumentano le combinazioni effettive che si realizzano nei dati.

In sintesi: l’algoritmo non è “una combinazione = un segmento”, ma **un sistema di regole additive**; le “combinazioni” sono tutte le possibili combinazioni di fattori che fanno scattare un certo sottoinsieme di queste regole e quindi producono un vettore di 4 punteggi (business, leisure, coppia, famiglia) e da lì un segmento unico (max + priorità).

---

## 5. Assegnazione del segmento (da punteggi)

```text
1. Per ogni cliente si ha un vettore (business, leisure, coppia, famiglia).
2. Segmento = argmax(punteggi).
3. In parità: Business > Famiglia > Coppia > Leisure.
```

---

## 6. Raffinamento da input operatore

Dopo lo scoring iniziale, l’operatore può inserire:

- **Note di prenotazione** e **richieste speciali** (testo libero)  
- **Servizi selezionati** (checkbox)  
- **Indicatori comportamentali** (checkbox per segmento)

Il backend:

1. **Estrae indicatori dal testo**: cerca keyword (es. “lavoro”, “anniversario”, “bambini”, “suite”, “parcheggio”) e mappa a indicatori (es. `arrivo_tarda_serata_lavoro`, `anniversario_occasione_romantica`, `bambini`, `suite_executive`, `parcheggio`).  
2. **Mappa i servizi** selezionati a indicatori (es. “Sala meeting” → Business, “Culla” → Famiglia, “Late check-out” → Coppia).  
3. **Unisce** indicatori da testo, servizi e checkbox.  
4. **Applica priorità**: Business > Famiglia > Coppia > Leisure (primo segmento che ha almeno un indicatore attivo vince).  
5. Se nessun indicatore matcha → **Leisure** (default).  
6. Il segmento così ottenuto viene salvato e usato per:  
   - mostrare il segmento in scheda,  
   - applicare il boost +15 allo score di quel segmento (così le percentuali “prime due categorie” si aggiornano),  
   - determinare le 5 campagne Market Intelligence (3 per la % più alta, 2 per la seconda).

Le keyword e gli indicatori sono definiti in `operator_refinement.py` (KEYWORDS_TO_INDICATOR, SERVIZI_TO_INDICATOR, INDICATORI_* e PRIORITA_INDICATORI).

---

## 7. Riepilogo file principali

| File | Ruolo |
|------|--------|
| `backend/app/main.py` | API: upload, overview, customers, dettaglio cliente, feedback, marketing, trend. Store in-memory e boost score da feedback. |
| `backend/app/excel_parser.py` | Mapping colonne Excel/CSV, calcolo soglia top 25% e media spesa, chiamata a compute_scores e assign_segment. |
| `backend/app/scoring.py` | compute_scores (tutte le regole), assign_segment (max + priorità). |
| `backend/app/operator_refinement.py` | Indicatori per segmento, keyword→indicatore, servizi→indicatore, segment_from_operator_input e priorità. |
| `backend/app/models.py` | Segment (enum 4 valori), Scores (4 campi), SegmentedCustomer, CampaignItem. |
| `backend/app/campaigns.py` | Campagne per segmento (Market Intelligence). |
| `frontend/.../dashboard/[id]/page.tsx` | Dashboard, tabella clienti, modal scheda cliente, percentuali, Market Intelligence (5 campagne), form operatore. |

---

## 8. Documenti correlati

- **FORMATO-EXCEL-GESTIONALE.md**: come preparare l’export Excel (nomi colonne, formati).  
- **docs/BACKEND-FLUSSO-NOTE-PERCENTUALI.md**: perché le percentuali in scheda si aggiornano solo dopo “Salva” e come vengono usate le note.
