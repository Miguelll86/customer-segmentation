'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, TrendingUp, Users, Euro, PieChart } from 'lucide-react';
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
  Premium: '#8b5cf6',
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
  const perPage = 20;

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
                    <th className="p-3">Giorno</th>
                    <th className="p-3">Storico</th>
                    <th className="p-3">Spesa media</th>
                    <th className="p-3">Revenue</th>
                    <th className="p-3">Score (B/L/C/F/P)</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((c) => (
                    <tr key={c.row_index} className="border-b border-[var(--border)]/50 hover:bg-white/5">
                      <td className="p-3">{c.row_index + 1}</td>
                      <td className="p-3 font-medium">
                        {c.nome_cliente || c.cliente_id || '-'}
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
                      <td className="p-3">{c.giorno_arrivo ?? '-'}</td>
                      <td className="p-3">{c.storico_soggiorni ?? '-'}</td>
                      <td className="p-3">{c.spesa_media != null ? `€ ${c.spesa_media.toFixed(0)}` : '-'}</td>
                      <td className="p-3">{c.revenue != null ? `€ ${c.revenue.toFixed(0)}` : '-'}</td>
                      <td className="p-3 font-mono text-xs">
                        {c.scores?.business ?? 0}/{c.scores?.leisure ?? 0}/{c.scores?.coppia ?? 0}/{c.scores?.famiglia ?? 0}/{c.scores?.premium ?? 0}
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

        {/* Marketing Intelligence */}
        {marketing && (
          <section className="mb-8">
            <h2 className="mb-4 text-lg font-medium">Marketing Intelligence</h2>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {marketing.segmenti.map((seg) => (
                <div key={seg.segment} className="card">
                  <h3
                    className="mb-3 rounded-lg px-3 py-2 text-sm font-medium"
                    style={{ backgroundColor: `${SEGMENT_COLORS[seg.segment] || '#64748b'}25`, color: SEGMENT_COLORS[seg.segment] }}
                  >
                    {seg.segment}
                  </h3>
                  <ul className="mb-3 space-y-1 text-xs text-[var(--muted)]">
                    <li>Revenue attuale: € {seg.revenue_attuale.toLocaleString('it-IT')}</li>
                    <li>Revenue potenziale: € {seg.revenue_potenziale_stimata.toLocaleString('it-IT')}</li>
                    <li>Conversion rate: {(seg.conversion_rate_storico * 100).toFixed(1)}%</li>
                    <li>ROI stimato: {seg.roi_stimato}x</li>
                  </ul>
                  <p className="mb-2 text-xs font-medium text-[var(--text)]">Campagne suggerite</p>
                  <ul className="space-y-2">
                    {seg.campagne.map((camp) => (
                      <li key={camp.titolo} className="rounded border border-[var(--border)] p-2 text-xs">
                        <span className="font-medium text-[var(--text)]">{camp.titolo}</span>
                        <p className="mt-1 text-[var(--muted)]">{camp.descrizione}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
