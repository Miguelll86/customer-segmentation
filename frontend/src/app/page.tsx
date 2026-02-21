'use client';

import { useState } from 'react';
import { Upload, BarChart3, Users, Megaphone } from 'lucide-react';
import Link from 'next/link';

// Base senza /api finale, per evitare URL tipo .../api/api/upload (404)
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/api\/?$/, '').replace(/\/$/, '');

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError('Seleziona un file Excel o CSV.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const url = API_BASE ? `${API_BASE}/api/upload` : '/api/upload';
      const res = await fetch(url, { method: 'POST', body: formData });
      let data: { detail?: string; analysis_id?: string };
      try {
        data = await res.json();
      } catch {
        if (!res.ok) setError(`Errore ${res.status}. Avvia il backend (porta 8000) e riprova.`);
        else setError('Risposta non valida dal server.');
        return;
      }
      if (!res.ok) throw new Error(data.detail || 'Upload fallito');
      setAnalysisId(data.analysis_id ?? null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Errore di caricamento';
      if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('Load failed')) {
        setError('Impossibile contattare il backend. Avvia il server (cd backend && python -m flask run o python app/main.py sulla porta 8000) e riprova.');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <header className="border-b border-[var(--border)] bg-[var(--card)]/50 px-6 py-4">
        <h1 className="text-xl font-semibold text-[var(--text)]">
          Customer Segmentation & Marketing AI
        </h1>
        <p className="text-sm text-[var(--muted)]">
          Carica i dati arrivi, visualizza segmenti e campagne
        </p>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-10">
        <section className="card mb-8">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-medium">
            <Upload className="h-5 w-5" />
            Caricamento dati arrivi
          </h2>
          <p className="mb-4 text-sm text-[var(--muted)]">
            File <strong>.xlsx</strong>, <strong>.xls</strong> o <strong>.csv</strong>. Colonne: numero notti, numero ospiti, canale, giorno arrivo, storico soggiorni, spesa media / tariffa, data arrivo, categoria camera. Se l’Excel dà errore, in Excel salva come <strong>CSV UTF-8</strong> (File → Salva con nome) e carica il .csv.
          </p>
          <form onSubmit={handleUpload} className="flex flex-wrap items-end gap-4">
            <label className="flex-1 min-w-[200px]">
              <span className="mb-2 block text-sm text-[var(--muted)]">File Excel o CSV</span>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="input w-full"
              />
            </label>
            <button type="submit" disabled={loading} className="btn-primary disabled:opacity-50">
              {loading ? 'Caricamento...' : 'Carica e analizza'}
            </button>
          </form>
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          {analysisId && (
            <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4">
              <p className="text-sm text-emerald-300">File elaborato correttamente.</p>
              <Link
                href={`/dashboard/${analysisId}`}
                className="mt-2 inline-flex items-center gap-2 text-[var(--accent)] hover:underline"
              >
                Apri dashboard
                <BarChart3 className="h-4 w-4" />
              </Link>
            </div>
          )}
        </section>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="card flex items-center gap-4">
            <div className="rounded-lg bg-segment-business/20 p-3">
              <BarChart3 className="h-8 w-8 text-segment-business" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Segmenti</p>
              <p className="font-medium">Business, Leisure, Coppia, Famiglia, Premium</p>
            </div>
          </div>
          <div className="card flex items-center gap-4">
            <div className="rounded-lg bg-segment-leisure/20 p-3">
              <Users className="h-8 w-8 text-segment-leisure" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Clienti</p>
              <p className="font-medium">Tabella filtrabile e score dettagliato</p>
            </div>
          </div>
          <div className="card flex items-center gap-4">
            <div className="rounded-lg bg-segment-premium/20 p-3">
              <Megaphone className="h-8 w-8 text-segment-premium" />
            </div>
            <div>
              <p className="text-sm text-[var(--muted)]">Campagne</p>
              <p className="font-medium">Suggerite per segmento</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
