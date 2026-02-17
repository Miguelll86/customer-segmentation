# Customer Segmentation & Marketing AI

Web App con dashboard per **segmentazione clienti** e **campagne marketing** personalizzate. Caricamento file Excel arrivi, algoritmo di scoring a 5 segmenti, generazione campagne e dashboard interattiva. **Nessun export Excel in output** — tutti i risultati sono visualizzati in dashboard.

## Segmenti

- **Business** – Pacchetto corporate midweek, sconto ricorrente, upgrade veloce  
- **Leisure** – Offerta stagionale, esperienze locali, early booking  
- **Coppia** – Pacchetto romantico, cena + spa, late checkout  
- **Famiglia** – Bambini gratis, pacchetto family, attività kids  
- **Premium** – Concierge dedicato, upgrade prioritario, evento esclusivo  

## Requisiti

- **Backend**: Python 3.11–3.14, Flask, pandas, openpyxl (compatibile con **Python 3.14**)
- **Frontend**: Node 18+, Next.js 14, React, Recharts  

## Avvio rapido

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 -m app.main
```

Il server sarà su **http://localhost:8000**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Apri [http://localhost:3000](http://localhost:3000). Carica un file Excel (vedi formato sotto) e apri la dashboard.

### Formato Excel

Il file deve contenere almeno alcune di queste colonne (nomi in italiano o inglese):

| numero notti | numero ospiti | canale   | giorno arrivo | storico soggiorni | spesa media | data arrivo | categoria camera |
|--------------|---------------|----------|---------------|-------------------|-------------|-------------|------------------|
| 2            | 1             | corporate| lun           | 3                 | 180         | 2024-01-15  | Deluxe           |
| 4            | 2             | booking  | ven           | 0                 | 120         | 2024-02-20  | Standard         |

Per un file di prova, dalla cartella `backend` esegui:  
`python scripts/generate_sample_excel.py`  
Verrà creato `backend/sample_arrivi.xlsx`.

## API (Backend)

- `POST /api/upload` – Carica Excel, restituisce `analysis_id`
- `GET /api/analysis/{id}/overview` – KPI e distribuzione segmenti
- `GET /api/analysis/{id}/customers?segment=&skip=&limit=` – Tabella clienti (filtro e paginazione)
- `GET /api/analysis/{id}/marketing` – Campagne e stime revenue/ROI per segmento
- `GET /api/analysis/{id}/trend` – Trend settimanale segmenti

## Dashboard

1. **Overview KPI** – Totale arrivi, distribuzione %, ADR, revenue, valore cliente medio  
2. **Segment Visualization** – Grafico torta, barre revenue per categoria  
3. **Customer Insights** – Tabella filtrabile per segmento, score dettagliato (B/L/C/F/P)  
4. **Marketing Intelligence** – Campagne per segmento, revenue potenziale, conversion rate, ROI  

## Algoritmo di scoring

Assegnazione **una sola categoria** per cliente tramite punteggio ponderato. In parità: **Premium > Business > Famiglia > Coppia > Leisure**.  
Parametri: numero notti, numero ospiti, canale, giorno arrivo, storico soggiorni, spesa media (top 25% per Premium), categoria camera.

## Estensioni future

- PostgreSQL per persistenza e storico conversioni  
- Auto-apprendimento: aggiustamento pesi da conversioni campagne  
- K-means opzionale per cluster reali  
- Integrazione email/CRM per campagne  

## Licenza

Uso interno / progetto.
# customer-segmentation
