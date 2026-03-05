# Formato Excel per export dal gestionale (PMS)

Questo documento spiega come impostare il file Excel (o CSV) da esportare dal tuo **gestionale alberghiero** per l’analisi di segmentazione clienti. La prima riga deve contenere le **intestazioni di colonna**; l’ordine delle colonne non conta.

---

## Export con queste colonne (supportato direttamente)

Se il tuo gestionale esporta **esattamente** queste colonne, l’app le riconosce e le usa così:

| Colonna nell’export | Uso nell’app |
|--------------------|--------------|
| **Cliente** (o Nome Cliente) | Nome dell’ospite |
| **data di prenotazione** | Data prenotazione → calcolo anticipo (giorni prima dell’arrivo) |
| **Arrivo** | Data di arrivo + giorno della settimana |
| **Partenza** | Data di partenza (se mancano i “Giorni”, si calcolano da Arrivo–Partenza) |
| **Giorni** | Notti di pernottamento |
| **Prenotante** (agenzia della prenotazione) | Chi ha prenotato → segmento Business/Leisure |
| **totale** (totale costo soggiorno) | Costo totale → **spesa media per notte** = totale ÷ Giorni |
| **Interi** (nr di adulti) | Adulti → **numero ospiti** = Interi + scontati |
| **scontati** (nr bambini) | Bambini → segmento Famiglia e totale ospiti |

Non serve rinominare le colonne: puoi caricare l’Excel così com’è. L’app calcola in automatico:
- **Anticipo** (giorni tra data di prenotazione e Arrivo)
- **Spesa per notte** (totale ÷ Giorni)
- **Numero ospiti** (Interi + scontati)

---

## Colonne obbligatorie / consigliate (formato generico)

| Nome colonna (consigliato) | Alias accettati | Descrizione | Esempio |
|----------------------------|-----------------|-------------|---------|
| **data arrivo** | data, arrival, check-in, data_arrivo | Data di arrivo | 2024-06-15 |
| **numero notti** | notti, nights, n. notti | Notti di soggiorno | 3 |
| **numero ospiti** | ospiti, guests, pax, prenotati, n. ospiti | Numero totale ospiti (adulti + bambini) | 4 |
| **canale** | channel, canale prenotazione, source | Canale di prenotazione | Booking.com, corporate, direct |
| **giorno arrivo** | day, weekday, giorno | Giorno della settimana (lun-dom) o numero 0-6 | ven |
| **spesa media** | spesa, tariffa, rate, adr, revenue, importo | Tariffa/spesa per notte (€) | 120.50 |
| **categoria camera** | camera, room, room type, categoria | Tipo di camera | Deluxe, Suite |

---

## Colonne opzionali (per algoritmo avanzato)

| Nome colonna (consigliato) | Alias accettati | Descrizione | Esempio |
|----------------------------|-----------------|-------------|---------|
| **cliente_id** | id, customer id, codice cliente | Codice cliente nel gestionale | C12345 |
| **nome cliente** | nome, name, guest name, nominativo | Nome dell’ospite | Rossi Mario |
| **data partenza** | departure, check-out, data partenza | Data di partenza (se assente, si usa data arrivo + notti) | 2024-06-18 |
| **anticipo giorni** | anticipo, lead time, giorni anticipo, giorni prenotazione | Quanti giorni prima dell’arrivo è stata fatta la prenotazione | 21 |
| **data prenotazione** | data prenotazione, booking date, prenotato il | Data in cui è stata effettuata la prenotazione (se non hai “anticipo giorni”) | 2024-05-25 |
| **prenotante** | booker, tipo prenotante, fonte, tipologia | Chi ha prenotato: cliente, agenzia, azienda, tour operator | agenzia |
| **numero bambini** | bambini, n. bambini, children, kids | Numero di bambini in soggiorno (o Sì/No) | 2 |

---

## Come esportare dal gestionale

1. **Report / Export arrivi**  
   Dal tuo PMS esporta un report di **arrivi** (o prenotazioni) con almeno: data arrivo, notti, ospiti, canale, tariffa/spesa. Aggiungi le colonne che il gestionale ti mette a disposizione (es. data prenotazione, tipo prenotante, bambini).

2. **Intestazioni**  
   Usa **una sola riga di intestazione** con i nomi delle colonne. Puoi usare i nomi italiani o gli alias nella tabella sopra (es. “numero notti” o “nights”).

3. **Formato file**  
   - **Excel:** salva come `.xlsx` (evita il vecchio `.xls`).  
   - **CSV:** separatore virgola, prima riga = intestazioni, encoding **UTF-8** (in Excel: “Salva con nome” → “CSV UTF-8”).

4. **Date**  
   Formati accettati: `YYYY-MM-DD` (es. 2024-06-15), `DD/MM/YYYY`, `MM/DD/YYYY`. Coerenza nella stessa colonna è preferibile.

5. **Anticipo prenotazione**  
   - Se il gestionale ha un campo **“giorni tra prenotazione e arrivo”** (lead time), esportalo come colonna **anticipo giorni** (numero).  
   - Se hai solo **data prenotazione** e **data arrivo**, esporta entrambe: l’app calcola automaticamente i giorni di anticipo.

6. **Prenotante**  
   Valori tipici da mappare nel PMS: “cliente” / “guest”, “agenzia”, “azienda” / “corporate”, “tour operator”. L’algoritmo usa questo per dare più peso a Business (agenzia/azienda) o Leisure/Coppia (cliente).

7. **Bambini**  
   - Colonna **numero bambini** (0, 1, 2, …) oppure  
   - Colonna **bambini** con valori Sì/No, 1/0, X/vuoto.  
   La presenza di bambini aumenta il punteggio del segmento **Famiglia**.

---

## Riepilogo: cosa usa l’algoritmo

- **Combinazioni giorno arrivo + notti:** es. weekend + 1 notte, midweek + 2 notti (Business), weekend + 3 notti (Coppia/Leisure).
- **Capacità di spesa:** sopra/sotto la media (e top 25% per Premium).
- **Numero prenotati:** 1 ospite → Business; 2 → Coppia; 3+ → Famiglia.
- **Anticipo:** pochi giorni (last minute) → Business; molti giorni (30+) → Leisure/Famiglia.
- **Prenotante:** agenzia/azienda/TO → Business; cliente → Leisure/Coppia.
- **Bambini:** almeno 1 bambino → forte segnale Famiglia.

---

## Esempio intestazioni (copy-paste per Excel)

```
data arrivo	numero notti	numero ospiti	canale	giorno arrivo	spesa media	categoria camera	cliente_id	nome cliente	anticipo giorni	prenotante	numero bambini
```

(separati da tabulazione; in CSV usa la virgola)
