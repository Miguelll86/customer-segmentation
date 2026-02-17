# Come pubblicare l’app (renderla visibile ad altri)

Puoi rendere l’app accessibile ad altre persone in due modi: **sulla tua rete** (gratis, veloce) o **su internet** (deploy in cloud, sempre raggiungibile).

---

## Opzione 1: Stessa rete (Wi‑Fi / LAN)

L’altra persona deve essere **sulla stessa rete** (stesso Wi‑Fi o stessa rete aziendale).

### Sul tuo Mac (dove gira l’app)

1. **Backend** – avvialo in ascolto su tutte le interfacce (già così con `0.0.0.0`):
   ```bash
   cd backend && source .venv/bin/activate && python3 -m app.main
   ```
2. **Frontend** – avvialo così:
   ```bash
   cd frontend && npm run dev
   ```
3. Trova il **tuo IP locale** (es. 192.168.1.120):
   ```bash
   ipconfig getifaddr en0
   ```
   (Su Windows: `ipconfig` e cerca “Indirizzo IPv4”.)

### CORS per l’altro dispositivo

L’altro deve aprire il **frontend** usando il tuo IP, non `localhost`.  
Imposta la variabile d’ambiente `CORS_ORIGINS` prima di avviare il backend, sostituendo `TUO_IP` con il valore trovato (es. `192.168.1.120`):

```bash
export CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://TUO_IP:3000"
cd backend && python3 -m app.main
```

### Cosa dare all’altra persona

- **URL da aprire nel browser:** `http://TUO_IP:3000`  
  (es. `http://192.168.1.120:3000`)

**Limiti:** funziona solo finché il tuo computer è acceso e l’app è in esecuzione; solo chi è sulla stessa rete può accedere.

---

## Opzione 2: Pubblicare su internet (cloud)

L’app diventa raggiungibile da chiunque abbia il link. Servono due parti:

- **Frontend (Next.js)** → es. **Vercel** (gratis)
- **Backend (Flask)** → es. **Render** (gratis con limiti)

### 1. Preparare il progetto (Git)

Se non l’hai già fatto, crea un repository Git nella cartella del progetto:

```bash
cd /Users/miguel/customer-segmentation-app
git init
git add .
git commit -m "Customer Segmentation App"
```

Poi crea un repo su **GitHub** (o GitLab) e collegalo:

```bash
git remote add origin https://github.com/TUO-USER/TUO-REPO.git
git push -u origin main
```

(Sostituisci `TUO-USER` e `TUO-REPO` con i tuoi.)

---

### 2. Deploy del backend su Render

1. Vai su [render.com](https://render.com) e registrati (anche con GitHub).
2. **New → Web Service**.
3. Collega il repo GitHub del progetto.
4. Imposta:
   - **Name:** `customer-segmentation-api` (o come preferisci)
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app.main:app`  
     (aggiungi `gunicorn` in `backend/requirements.txt` se non c’è)
5. Clicca **Create Web Service**.
6. Quando il deploy è finito, copia l’**URL del servizio** (es. `https://customer-segmentation-api.onrender.com`).  
   Questo è l’URL del backend (senza `/api` alla fine).

**Variabile d’ambiente sul backend (Render):**

- **CORS_ORIGINS** = `https://TUO-SITO.vercel.app`  
  (lo imposterai dopo aver pubblicato il frontend; puoi aggiungerlo in un secondo momento).

---

### 3. Aggiungere Gunicorn al backend

Su Render si usa un server WSGI. Nella cartella `backend` aggiungi a `requirements.txt`:

```
gunicorn>=21.0.0
```

E assicurati che il comando di avvio sia:

```text
gunicorn app.main:app
```

(dove `app.main` è il modulo e `app` è l’istanza Flask).

---

### 4. Deploy del frontend su Vercel

1. Vai su [vercel.com](https://vercel.com) e accedi (anche con GitHub).
2. **Add New → Project** e importa lo **stesso** repository GitHub.
3. Imposta:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js
4. **Environment Variables** (obbligatorio per il frontend):
   - **Name:** `NEXT_PUBLIC_API_URL`  
   - **Value:** `https://customer-segmentation-api.onrender.com`  
     (l’URL del backend Render, **senza** `/api`).
5. **Deploy**.

Al termine avrai un URL tipo `https://customer-segmentation-xxx.vercel.app`.

---

### 5. Aggiornare CORS sul backend (Render)

Torna su Render → tuo Web Service → **Environment** e aggiungi (o modifica):

- **CORS_ORIGINS** = `https://customer-segmentation-xxx.vercel.app`  
  (l’URL esatto del sito Vercel).

Salva e aspetta il redeploy.

---

### 6. Cosa dare all’altra persona

- **Link da condividere:** l’URL del sito Vercel (es. `https://customer-segmentation-xxx.vercel.app`).

Chi apre quel link vedrà l’app e potrà caricare file e usare la dashboard; il backend è già su Render e accetta richieste dal frontend grazie a CORS.

---

## Riepilogo

| Obiettivo              | Cosa fare |
|------------------------|-----------|
| Solo un’altra persona, stessa rete | Opzione 1: avvia backend + frontend, imposta `CORS_ORIGINS` con il tuo IP, condividi `http://TUO_IP:3000`. |
| Pubblicare su internet | Opzione 2: backend su Render, frontend su Vercel, `NEXT_PUBLIC_API_URL` e `CORS_ORIGINS` configurati come sopra. |

Se mi dici se preferisci “solo rete locale” o “su internet” posso adattare i passaggi al tuo caso (es. solo Render, solo Vercel, altro servizio).
