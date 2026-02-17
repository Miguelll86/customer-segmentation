# Deploy passo passo – Customer Segmentation App

Segui questi passi in ordine. Tempo stimato: ~15 minuti.

---

## Passo 1: Crea il repository su GitHub

1. Vai su [github.com](https://github.com) e accedi.
2. Clicca **+** → **New repository**.
3. Nome (es. `customer-segmentation-app`), **Public**, non spuntare README (il progetto esiste già).
4. Clicca **Create repository**.
5. **Non** clonare il repo: useremo la cartella che hai già. Tieni aperta la pagina del repo (vedrai le istruzioni "push an existing repository").

---

## Passo 2: Carica il progetto su GitHub (dal Mac)

Apri il **Terminale** e esegui (sostituisci `TUO-USER` e `customer-segmentation-app` con il tuo username e il nome del repo):

```bash
cd /Users/miguel/customer-segmentation-app

git init
git add .
git commit -m "App segmentazione clienti - pronto per deploy"

git branch -M main
git remote add origin https://github.com/TUO-USER/customer-segmentation-app.git
git push -u origin main
```

Se GitHub chiede login, usa le tue credenziali (o un Personal Access Token se hai l’autenticazione a 2 fattori).

---

## Passo 3: Deploy del backend su Render

1. Vai su [render.com](https://render.com) e **Sign up** (puoi usare **Sign in with GitHub**).
2. Clicca **New +** → **Web Service**.
3. **Connect a repository**: se non vedi il repo, clicca **Configure account** e autorizza Render su GitHub, poi seleziona **customer-segmentation-app**.
4. Compila:
   - **Name:** `customer-segmentation-api` (o come preferisci)
   - **Region:** scegli la più vicina (es. Frankfurt)
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app.main:app`
5. **Advanced** (opzionale): in **Environment** aggiungi per ora:
   - **CORS_ORIGINS** = `https://localhost:3000`  
   (lo aggiorneremo al passo 5 con l’URL Vercel.)
6. Clicca **Create Web Service**.
7. Attendi il primo deploy (2–5 minuti). Se fallisce, controlla i log (soprattutto che **Root Directory** sia `backend` e **Start Command** sia `gunicorn app.main:app`).
8. Quando è **Live**, copia l’**URL del servizio** (es. `https://customer-segmentation-api.onrender.com`).  
   **Tienilo a portata di mano** per i prossimi passi.

---

## Passo 4: Deploy del frontend su Vercel

1. Vai su [vercel.com](https://vercel.com) e **Sign up** (puoi usare **Continue with GitHub**).
2. Clicca **Add New…** → **Project**.
3. Importa il repository **customer-segmentation-app** (se non lo vedi, collega prima il tuo account GitHub).
4. Imposta:
   - **Root Directory:** clicca **Edit** e inserisci `frontend`
   - **Framework Preset:** Next.js (dovrebbe essere già selezionato)
5. **Environment Variables** – clicca e aggiungi:
   - **Name:** `NEXT_PUBLIC_API_URL`  
   - **Value:** l’URL del backend Render **senza** `/api` alla fine  
     (es. `https://customer-segmentation-api.onrender.com`)
6. Clicca **Deploy**.
7. Attendi 1–2 minuti. Al termine avrai un link tipo `https://customer-segmentation-app-xxx.vercel.app`.  
   **Copia questo URL** (è l’URL del frontend).

---

## Passo 5: Collega backend e frontend (CORS)

1. Torna su **Render** → il tuo servizio **customer-segmentation-api** → **Environment**.
2. Modifica **CORS_ORIGINS** (o aggiungilo se non c’era) e imposta come valore **esattamente** l’URL del frontend Vercel (es. `https://customer-segmentation-app-xxx.vercel.app`).  
   Nessuno spazio, nessun `/` finale.
3. Salva. Render farà un **redeploy** automatico (attendi che torni **Live**).

---

## Passo 6: Prova l’app

1. Apri nel browser l’**URL Vercel** (il frontend).
2. Carica un file (Excel o CSV di esempio).
3. Clicca **Apri dashboard** e verifica che i dati e i grafici si vedano correttamente.

Se qualcosa non funziona:
- **Upload che fallisce:** controlla che `NEXT_PUBLIC_API_URL` su Vercel sia l’URL Render **senza** `/api`.
- **Errore CORS / “blocked”:** controlla che **CORS_ORIGINS** su Render sia **esattamente** l’URL del sito Vercel (stesso che usi per aprire l’app).

---

## Riepilogo URL

| Ruolo   | Dove   | URL esempio |
|--------|--------|-------------|
| Backend | Render | `https://customer-segmentation-api.onrender.com` |
| Frontend | Vercel | `https://customer-segmentation-app-xxx.vercel.app` |

**Link da condividere con altri:** l’URL del frontend (Vercel).

---

## Note

- **Render (piano free):** il backend va in “sleep” dopo un po’ di inattività; la prima richiesta dopo il risveglio può richiedere 30–60 secondi.
- **Dati in memoria:** le analisi caricate non sono salvate su disco; se il servizio si riavvia, i dati si perdono. Per persistenza servirebbe un database (es. PostgreSQL su Render).
- Per aggiornare l’app in futuro: modifica il codice, poi `git add .` → `git commit -m "..."` → `git push`. Render e Vercel faranno il redeploy in automatico.
