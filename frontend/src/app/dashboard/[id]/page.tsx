'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, TrendingUp, Users, Euro, PieChart, X, RefreshCw } from 'lucide-react';
import {
  PieChart as RechartsPie,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

// Base senza /api finale, per evitare URL tipo .../api/api/analysis/... (404)
const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/api\/?$/, '').replace(/\/$/, '');
const SEGMENT_COLORS: Record<string, string> = {
  Business: '#0ea5e9',
  Leisure: '#22c55e',
  Coppia: '#ec4899',
  Famiglia: '#f59e0b',
  Premium: '#22c55e', // retrocompat: ex-Premium fusionato in Leisure
};

type Overview = {
  total_arrivals: number;
  total_revenue: number;
  adr_medio_generale: number;
  valore_cliente_medio_generale: number;
  segment_distribution: Array<{
    segment: string;
    count: number;
    percentuale: number;
    adr_medio: number;
    revenue_totale: number;
    valore_cliente_medio: number;
  }>;
};

type CustomerRow = {
  row_index: number;
  segment: string;
  scores: Record<string, number>;
  numero_notti: number | null;
  numero_ospiti: number | null;
  canale: string | null;
  giorno_arrivo: string | null;
  storico_soggiorni: number | null;
  spesa_media: number | null;
  cliente_id: string | null;
  nome_cliente: string | null;
  data_arrivo: string | null;
  categoria_camera: string | null;
  revenue: number | null;
  anticipo_giorni: number | null;
  prenotante: string | null;
  numero_bambini: number | null;
  operator_feedback?: Record<string, unknown> | null;
};

type MarketingSegment = {
  segment: string;
  count: number;
  revenue_attuale: number;
  revenue_potenziale_stimata: number;
  conversion_rate_storico: number;
  roi_stimato: number;
  campagne: Array<{ titolo: string; descrizione: string; tipo: string }>;
};

type Marketing = {
  segmenti: MarketingSegment[];
};

type IndicatoreDef = { key: string; segment: string; label: string };

const SERVIZI_OPTIONS = [
  'Colazione inclusa', 'Sala meeting', 'Spa', 'Transfer', 'Culla', 'Letto aggiunto',
  'Late check-out', 'Cena', 'Parcheggio', 'Pet friendly', 'Fattura aziendale', 'Upgrade',
];

const SEGMENT_LABELS: Record<string, string> = {
  business: 'Business',
  leisure: 'Leisure',
  coppia: 'Coppia',
  famiglia: 'Famiglia',
};

function scoresToPercentages(scores: Record<string, number>): { segment: string; percent: number }[] {
  const keys = ['business', 'leisure', 'coppia', 'famiglia'];
  const total = keys.reduce((s, k) => s + (scores[k] ?? 0), 0);
  if (total === 0) {
    return keys.map((k) => ({ segment: SEGMENT_LABELS[k] ?? k, percent: 25 }));
  }
  return keys.map((k) => ({
    segment: SEGMENT_LABELS[k] ?? k,
    percent: Math.round(((scores[k] ?? 0) / total) * 1000) / 10,
  }));
}

function fetchApi<T>(path: string): Promise<T> {
  const url = API_BASE ? `${API_BASE}${path}` : path;
  return fetch(url).then(async (r) => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((data as { detail?: string }).detail || `Errore ${r.status}`);
    return data as T;
  });
}

export default function DashboardPage() {
  const params = useParams();
  const id = params?.id as string;
  const [overview, setOverview] = useState<Overview | null>(null);
  const [customers, setCustomers] = useState<CustomerRow[]>([]);
  const [marketing, setMarketing] = useState<Marketing | null>(null);
  const [segmentFilter, setSegmentFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerRow | null>(null);
  const [customerDetail, setCustomerDetail] = useState<CustomerRow | null>(null);
  const [profileUpdated, setProfileUpdated] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [notePrenotazione, setNotePrenotazione] = useState('');
  const [richiesteSpeciali, setRichiesteSpeciali] = useState('');
  const [serviziSelezionati, setServiziSelezionati] = useState<string[]>([]);
  const [indicatoriSelezionati, setIndicatoriSelezionati] = useState<string[]>([]);
  const [indicatoriDefinitions, setIndicatoriDefinitions] = useState<IndicatoreDef[]>([]);
  const [feedbackSaving, setFeedbackSaving] = useState(false);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const perPage = 20;

  useEffect(() => {
    const base = API_BASE || '';
    fetch(base + '/api/operator-indicators')
      .then((r) => r.json())
      .then((data: { indicatori?: IndicatoreDef[] }) => setIndicatoriDefinitions(data.indicatori || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!id || !selectedCustomer) {
      setCustomerDetail(null);
      setFeedbackSaved(false);
      return;
    }
    setFeedbackSaved(false);
    fetchApi<CustomerRow>(`/api/analysis/${id}/customer/${selectedCustomer.row_index}`)
      .then((d) => {
        setCustomerDetail(d);
        const fb = (d as CustomerRow & { operator_feedback?: Record<string, unknown> }).operator_feedback;
        setNotePrenotazione((fb?.note_prenotazione as string) ?? '');
        setRichiesteSpeciali((fb?.richieste_speciali as string) ?? '');
        setServiziSelezionati(Array.isArray(fb?.servizi_selezionati) ? (fb.servizi_selezionati as string[]) : []);
        setIndicatoriSelezionati(Array.isArray(fb?.indicatori) ? (fb.indicatori as string[]) : []);
      })
      .catch(() => setCustomerDetail(selectedCustomer));
  }, [id, selectedCustomer?.row_index]);

  const displayCustomer = customerDetail ?? selectedCustomer;

  useEffect(() => {
    if (!id) {
      setLoading(false);
      return;
    }
    setError(null);
    setLoading(true);
    Promise.all([
      fetchApi<Overview>(`/api/analysis/${id}/overview`),
      fetchApi<Marketing>(`/api/analysis/${id}/marketing`),
    ])
      .then(([ov, mk]) => {
        setOverview(ov);
        setMarketing(mk);
      })
      .catch(() => setError('Analisi non trovata'))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const seg = segmentFilter ? `&segment=${encodeURIComponent(segmentFilter)}` : '';
    fetchApi<CustomerRow[]>(`/api/analysis/${id}/customers?skip=${page * perPage}&limit=${perPage}${seg}`)
      .then(setCustomers)
      .catch(() => setCustomers([]));
  }, [id, segmentFilter, page]);

  if (loading && !overview) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-[var(--muted)]">Caricamento dashboard...</p>
      </div>
    );
  }
  if (!id) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-[var(--muted)]">ID analisi non disponibile. Torna all’upload e clicca su &quot;Apri dashboard&quot; dopo aver caricato un file.</p>
        <Link href="/" className="btn-secondary flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" /> Torna all’upload
        </Link>
      </div>
    );
  }
  if (error || !overview) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-red-400">{error || 'Analisi non trovata'}</p>
        <Link href="/" className="btn-secondary flex items-center gap-2">
          <ArrowLeft className="h-4 w-4" /> Torna all’upload
        </Link>
      </div>
    );
  }

  const pieData = overview.segment_distribution.map((s) => ({
    name: s.segment,
    value: s.count,
    color: SEGMENT_COLORS[s.segment] || '#64748b',
  }));

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--card)]/90 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-[var(--muted)] hover:text-[var(--text)]">
            <ArrowLeft className="h-4 w-4" /> Upload
          </Link>
          <h1 className="text-lg font-semibold">Dashboard segmentazione</h1>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* KPI Overview */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium text-[var(--text)]">Overview KPI</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="card flex items-center gap-4">
              <Users className="h-10 w-10 text-[var(--accent)]" />
              <div>
                <p className="text-sm text-[var(--muted)]">Totale arrivi</p>
                <p className="text-2xl font-bold">{overview.total_arrivals}</p>
              </div>
            </div>
            <div className="card flex items-center gap-4">
              <Euro className="h-10 w-10 text-emerald-500" />
              <div>
                <p className="text-sm text-[var(--muted)]">Revenue totale</p>
                <p className="text-2xl font-bold">€ {overview.total_revenue.toLocaleString('it-IT')}</p>
              </div>
            </div>
            <div className="card flex items-center gap-4">
              <TrendingUp className="h-10 w-10 text-amber-500" />
              <div>
                <p className="text-sm text-[var(--muted)]">ADR medio</p>
                <p className="text-2xl font-bold">€ {overview.adr_medio_generale.toLocaleString('it-IT')}</p>
              </div>
            </div>
            <div className="card flex items-center gap-4">
              <Euro className="h-10 w-10 text-violet-500" />
              <div>
                <p className="text-sm text-[var(--muted)]">Valore cliente medio</p>
                <p className="text-2xl font-bold">€ {overview.valore_cliente_medio_generale.toLocaleString('it-IT')}</p>
              </div>
            </div>
          </div>
        </section>

        {/* Segment Visualization */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium">Distribuzione segmenti</h2>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="card">
              <p className="mb-3 text-sm text-[var(--muted)]">Grafico a torta</p>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RechartsPie>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => [v, 'Arrivi']} />
                  </RechartsPie>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card">
              <p className="mb-3 text-sm text-[var(--muted)]">Revenue per categoria</p>
              <div className="h-[280px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overview.segment_distribution} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                    <XAxis dataKey="segment" tick={{ fill: 'var(--muted)', fontSize: 12 }} />
                    <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                      formatter={(v: number) => [`€ ${v.toLocaleString('it-IT')}`, 'Revenue']}
                    />
                    <Bar dataKey="revenue_totale" fill="var(--accent)" name="Revenue" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>

        {/* Customer Insights - Tabella */}
        <section className="mb-8">
          <h2 className="mb-4 text-lg font-medium">Customer Insights</h2>
          <div className="card overflow-hidden">
            <div className="mb-4 flex flex-wrap items-center gap-4">
              <label className="flex items-center gap-2">
                <span className="text-sm text-[var(--muted)]">Filtra segmento</span>
                <select
                  value={segmentFilter}
                  onChange={(e) => { setSegmentFilter(e.target.value); setPage(0); }}
                  className="input w-40"
                >
                  <option value="">Tutti</option>
                  {overview.segment_distribution.map((s) => (
                    <option key={s.segment} value={s.segment}>{s.segment}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                    <th className="p-3">#</th>
                    <th className="p-3">Cliente</th>
                    <th className="p-3">Segmento</th>
                    <th className="p-3">Notti</th>
                    <th className="p-3">Ospiti</th>
                    <th className="p-3">Canale</th>
                    <th className="p-3">Storico</th>
                    <th className="p-3">Costo giornaliero</th>
<th className="p-3">Revenue</th>
                                                    <th className="p-3">Anticipo</th>
                                                    <th className="p-3">Prenotante</th>
                                                    <th className="p-3">Bambini</th>
                                                    <th className="p-3">Score (B/L/C/F/P)</th>
                                                  </tr>
                                                </thead>
                                                <tbody>
                                                  {customers.map((c) => (
                                                    <tr key={c.row_index} className="border-b border-[var(--border)]/50 hover:bg-white/5">
                      <td className="p-3">{c.row_index + 1}</td>
                      <td className="p-3">
                        <button
                          type="button"
                          onClick={() => { setSelectedCustomer(c); setProfileUpdated(false); }}
                          className="font-medium text-left text-[var(--accent)] hover:underline focus:outline-none focus:ring-2 focus:ring-[var(--accent)] rounded"
                        >
                          {c.nome_cliente || c.cliente_id || 'Cliente'}
                        </button>
                      </td>
                      <td className="p-3">
                        <span
                          className="rounded px-2 py-0.5 text-xs font-medium"
                          style={{ backgroundColor: `${SEGMENT_COLORS[c.segment] || '#64748b'}30`, color: SEGMENT_COLORS[c.segment] }}
                        >
                          {c.segment}
                        </span>
                      </td>
                      <td className="p-3">{c.numero_notti ?? '-'}</td>
                      <td className="p-3">{c.numero_ospiti ?? '-'}</td>
                      <td className="p-3">{c.canale ?? '-'}</td>
                      <td className="p-3">{c.storico_soggiorni ?? '-'}</td>
                      <td className="p-3">{c.spesa_media != null ? `€ ${c.spesa_media.toFixed(2)}` : (c.revenue != null && c.numero_notti != null && c.numero_notti > 0 ? `€ ${(c.revenue / c.numero_notti).toFixed(2)}` : '-')}</td>
<td className="p-3">{c.revenue != null ? `€ ${c.revenue.toFixed(0)}` : '-'}</td>
                                                      <td className="p-3">{c.anticipo_giorni != null ? `${c.anticipo_giorni} gg` : '-'}</td>
                                                      <td className="p-3">{c.prenotante ?? '-'}</td>
                                                      <td className="p-3">{c.numero_bambini != null ? c.numero_bambini : '-'}</td>
                                                      <td className="p-3 font-mono text-xs">
                                                        {c.scores?.business ?? 0}/{c.scores?.leisure ?? 0}/{c.scores?.coppia ?? 0}/{c.scores?.famiglia ?? 0}
                                                      </td>
                                                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex justify-between border-t border-[var(--border)] pt-4">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary disabled:opacity-50"
              >
                Indietro
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={customers.length < perPage}
                className="btn-secondary disabled:opacity-50"
              >
                Avanti
              </button>
            </div>
          </div>
        </section>

        {/* Scheda cliente (modal orizzontale – tutto in una schermata) */}
        {selectedCustomer && displayCustomer && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3"
            onClick={() => setSelectedCustomer(null)}
            role="dialog"
            aria-modal="true"
            aria-labelledby="scheda-cliente-title"
          >
            <div
              className="card flex max-h-[95vh] w-full max-w-6xl flex-col overflow-hidden shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-4 py-2">
                <h2 id="scheda-cliente-title" className="text-lg font-semibold text-[var(--text)]">
                  {displayCustomer.nome_cliente || displayCustomer.cliente_id || 'Cliente'}
                </h2>
                <button
                  type="button"
                  onClick={() => setSelectedCustomer(null)}
                  className="rounded p-1 text-[var(--muted)] hover:bg-white/10 hover:text-[var(--text)]"
                  aria-label="Chiudi"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 overflow-y-auto p-4 lg:grid-cols-[1fr,1.4fr]">
                {/* Colonna sinistra: profilo e percentuali */}
                <div className="flex flex-col gap-3 border-r-0 border-[var(--border)] pr-0 lg:border-r lg:pr-4">
                  <p className="text-sm text-[var(--muted)]">
                    Segmento: <strong className="text-[var(--text)]" style={{ color: SEGMENT_COLORS[displayCustomer.segment] }}>{displayCustomer.segment}</strong>
                    {displayCustomer.data_arrivo && <> · Arrivo {displayCustomer.data_arrivo}</>}
                    {displayCustomer.operator_feedback && displayCustomer.operator_feedback.updated_at != null ? (
                      <span className="ml-2 text-xs text-emerald-400">(aggiornato da operatore)</span>
                    ) : null}
                  </p>
                  <p className="text-xs font-medium text-[var(--text)]">Prime due categorie (le % si aggiornano con l’input operatore)</p>
                  <div className="flex flex-wrap gap-2">
                    {(() => {
                      const percentages = scoresToPercentages(displayCustomer.scores || {});
                      const topTwoOnly = [...percentages].sort((a, b) => b.percent - a.percent).slice(0, 2);
                      return topTwoOnly.map(({ segment, percent }) => (
                        <div
                          key={segment}
                          className="flex items-center justify-between gap-2 rounded-lg px-3 py-2 ring-2 ring-[var(--accent)] bg-[var(--accent)]/10 font-semibold"
                        >
                          <span style={{ color: SEGMENT_COLORS[segment] || 'var(--text)' }}>{segment}</span>
                          <span className="font-mono text-sm">{percent}%</span>
                        </div>
                      ));
                    })()}
                  </div>

                  {/* Market Intelligence: 5 campagne – 3 dalla % più alta, 2 dalla seconda */}
                  {marketing && (() => {
                    const percentages = scoresToPercentages(displayCustomer.scores || {});
                    const topTwo = [...percentages].sort((a, b) => b.percent - a.percent).slice(0, 2);
                    const segNames = topTwo.map((p) => p.segment);
                    const campaignsBySeg = new Map(marketing.segmenti.map((s) => [s.segment, s.campagne || []]));
                    const picked: Array<{ titolo: string; descrizione: string; tipo: string; segment: string }> = [];
                    const takeFirst = 3;
                    const takeSecond = 2;
                    if (segNames[0]) {
                      const list = campaignsBySeg.get(segNames[0]) || [];
                      for (let i = 0; i < takeFirst && list[i]; i++) {
                        picked.push({ ...list[i], segment: segNames[0] } as { titolo: string; descrizione: string; tipo: string; segment: string });
                      }
                    }
                    if (segNames[1]) {
                      const list = campaignsBySeg.get(segNames[1]) || [];
                      for (let i = 0; i < takeSecond && list[i]; i++) {
                        picked.push({ ...list[i], segment: segNames[1] } as { titolo: string; descrizione: string; tipo: string; segment: string });
                      }
                    }
                    const toShow = picked.slice(0, 5);
                    if (toShow.length === 0) return null;
                    return (
                      <div className="mt-2 space-y-2">
                        <p className="text-xs font-medium text-[var(--text)]">Market Intelligence</p>
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                          {toShow.map((camp, idx) => (
                            <div
                              key={`${camp.segment}-${camp.titolo}-${idx}`}
                              className="rounded-lg border border-[var(--border)] bg-[var(--bg)]/60 p-2"
                              style={{ borderLeftWidth: '3px', borderLeftColor: SEGMENT_COLORS[camp.segment] || '#64748b' }}
                            >
                              <p className="text-xs font-medium text-[var(--text)] line-clamp-1">{camp.titolo}</p>
                              <p className="mt-0.5 text-[10px] text-[var(--muted)] line-clamp-2">{camp.descrizione}</p>
                              <span className="mt-1 inline-block rounded px-1.5 py-0.5 text-[10px] text-[var(--muted)] ring-1 ring-[var(--border)]">{camp.tipo}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {profileUpdated ? (
                    <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
                      Profilo aggiornato. Elaborato con i dati attuali del soggiorno.
                    </p>
                  ) : (
                    <button
                      type="button"
                      onClick={async () => {
                        setRefreshing(true);
                        try {
                          const url = API_BASE ? `${API_BASE}/api/analysis/${id}/customer/${selectedCustomer.row_index}/refresh` : `/api/analysis/${id}/customer/${selectedCustomer.row_index}/refresh`;
                          await fetch(url, { method: 'POST' });
                          setProfileUpdated(true);
                        } catch {
                          setProfileUpdated(true);
                        } finally {
                          setRefreshing(false);
                        }
                      }}
                      disabled={refreshing}
                      className="btn-secondary flex items-center justify-center gap-2 self-start disabled:opacity-50"
                    >
                      <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                      {refreshing ? 'Elaborazione...' : 'Elabora profilo durante il soggiorno'}
                    </button>
                  )}
                </div>

                {/* Colonna destra: input operatore */}
                <div className="space-y-3 overflow-y-auto">
                  <p className="text-sm font-medium text-[var(--text)]">Input operatore – raffina il segmento (le percentuali si ricalcolano al salvataggio)</p>
                  <div className="rounded-lg border border-[var(--border)]/60 bg-[var(--bg)]/80 px-3 py-2 text-xs text-[var(--muted)]">
                    <p className="font-medium text-[var(--text)] mb-1">Legenda – parole nelle note/richieste che orientano il segmento:</p>
                    <p><strong style={{ color: SEGMENT_COLORS['Business'] }}>Business:</strong> lavoro, fattura aziendale, meeting, scrivania, check-in rapido</p>
                    <p><strong style={{ color: SEGMENT_COLORS['Famiglia'] }}>Famiglia:</strong> bambini, culla, camera tripla/quadrupla</p>
                    <p><strong style={{ color: SEGMENT_COLORS['Coppia'] }}>Coppia:</strong> anniversario, romantico, cena romantica, spa coppia, late check-out</p>
                    <p><strong style={{ color: SEGMENT_COLORS['Leisure'] }}>Leisure:</strong> attrazioni, parcheggio, pet friendly, cane, suite, executive, transfer, upgrade</p>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    <label className="block sm:col-span-2">
                      <span className="mb-1 block text-xs text-[var(--muted)]">Note di prenotazione</span>
                      <textarea
                        value={notePrenotazione}
                        onChange={(e) => setNotePrenotazione(e.target.value)}
                        className="input w-full min-h-[48px]"
                        placeholder="Testo dalle note di prenotazione..."
                        rows={1}
                      />
                    </label>
                    <label className="block sm:col-span-2">
                      <span className="mb-1 block text-xs text-[var(--muted)]">Richieste speciali</span>
                      <textarea
                        value={richiesteSpeciali}
                        onChange={(e) => setRichiesteSpeciali(e.target.value)}
                        className="input w-full min-h-[48px]"
                        placeholder="Richieste particolari del cliente..."
                        rows={1}
                      />
                    </label>
                  </div>
                  <label className="block">
                    <span className="mb-1 block text-xs text-[var(--muted)]">Servizi selezionati</span>
                    <div className="flex flex-wrap gap-2">
                      {SERVIZI_OPTIONS.map((s) => (
                        <label key={s} className="flex cursor-pointer items-center gap-1.5 rounded border border-[var(--border)] px-2 py-1 text-xs hover:bg-white/5">
                          <input
                            type="checkbox"
                            checked={serviziSelezionati.includes(s)}
                            onChange={(e) => setServiziSelezionati((prev) => e.target.checked ? [...prev, s] : prev.filter((x) => x !== s))}
                          />
                          {s}
                        </label>
                      ))}
                    </div>
                  </label>
                  <div>
                    <span className="mb-2 block text-xs text-[var(--muted)]">Indicatori comportamentali</span>
                    <div className="flex flex-wrap gap-x-4 gap-y-2">
                      {['Business', 'Famiglia', 'Coppia', 'Leisure'].map((seg) => {
                        const items = indicatoriDefinitions.filter((i) => i.segment === seg);
                        if (items.length === 0) return null;
                        return (
                          <div key={seg} className="rounded border border-[var(--border)]/60 bg-white/5 p-2">
                            <p className="mb-1 text-xs font-medium" style={{ color: SEGMENT_COLORS[seg] }}>{seg}</p>
                            <div className="flex flex-wrap gap-x-2 gap-y-0.5">
                              {items.map((ind) => (
                                <label key={ind.key} className="flex cursor-pointer items-center gap-1 text-xs">
                                  <input
                                    type="checkbox"
                                    checked={indicatoriSelezionati.includes(ind.key)}
                                    onChange={(e) => setIndicatoriSelezionati((prev) => e.target.checked ? [...prev, ind.key] : prev.filter((k) => k !== ind.key))}
                                  />
                                  {ind.label}
                                </label>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={async () => {
                        setFeedbackSaving(true);
                        setFeedbackSaved(false);
                        try {
                          const url = API_BASE ? `${API_BASE}/api/analysis/${id}/customer/${selectedCustomer.row_index}/feedback` : `/api/analysis/${id}/customer/${selectedCustomer.row_index}/feedback`;
                          const res = await fetch(url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                              note_prenotazione: notePrenotazione || undefined,
                              richieste_speciali: richiesteSpeciali || undefined,
                              servizi_selezionati: serviziSelezionati.length ? serviziSelezionati : undefined,
                              indicatori: indicatoriSelezionati.length ? indicatoriSelezionati : undefined,
                            }),
                          });
                          await res.json().catch(() => ({}));
                          setFeedbackSaved(true);
                          const updated = await fetchApi<CustomerRow>(`/api/analysis/${id}/customer/${selectedCustomer.row_index}`);
                          setCustomerDetail(updated);
                        } catch {
                          setFeedbackSaved(false);
                        } finally {
                          setFeedbackSaving(false);
                        }
                      }}
                      disabled={feedbackSaving}
                      className="btn-primary disabled:opacity-50"
                    >
                      {feedbackSaving ? 'Salvataggio...' : 'Salva input e aggiorna %'}
                    </button>
                    {feedbackSaved && (
                      <span className="text-sm text-emerald-400">Salvato: segmento e percentuali aggiornati.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
