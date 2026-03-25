import { ArrowRight, ShieldAlert, Users, FileText, AlertTriangle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { cn } from '../lib/utils';
import { useDashboard, usePendingCases } from '../lib/hooks';
import { StatusBadge } from '../components/StatusBadge';
import { formatCompactUSD, scoreColor, providerDisplayName } from '../lib/helpers';
import { FreshnessBanner } from '../components/FreshnessBanner';
import { InfoButton } from '../components/InfoButton';

export function Dashboard() {
  const navigate = useNavigate();
  const { data: stats, error } = useDashboard();
  const { data: pending = [] } = usePendingCases(10);

  if (error) {
    return <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">{error.message}</div>;
  }

  const kpis = [
    { name: 'Total Providers', value: stats?.total_providers ?? 0, icon: Users, color: 'text-blue-600', bg: 'bg-blue-50', href: '/providers' },
    { name: 'Total Cases', value: stats?.total_cases ?? 0, icon: FileText, color: 'text-amber-600', bg: 'bg-amber-50', href: '/claims' },
    { name: 'High Risk', value: stats?.risk_distribution?.high_risk ?? 0, icon: ShieldAlert, color: 'text-rose-600', bg: 'bg-rose-50', href: '/providers?risk_band=high_risk', info: "Providers whose maximum service-line risk score is 51 or above. These are flagged for priority investigation based on peer-comparison z-scores, billing anomalies, and enrollment signals." },
    { name: 'Pending Review', value: pending.length, icon: AlertTriangle, color: 'text-indigo-600', bg: 'bg-indigo-50', href: '/investigations', info: "Cases that scored above the review threshold but have not yet been investigated by an analyst. Each case represents a provider–service code combination with elevated risk signals." },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">Overview of provider risk landscape and pending actions.</p>
        </div>
      </div>

      {/* Freshness Banner */}
      <FreshnessBanner />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <button
            key={kpi.name}
            onClick={() => navigate(kpi.href)}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow text-left"
          >
            <div className="flex items-start justify-between">
              <div className={cn('p-2 rounded-lg', kpi.bg)}>
                <kpi.icon className={cn('w-5 h-5', kpi.color)} />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-300" />
            </div>
            <div className="mt-4">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-slate-500">{kpi.name}</span>
                {kpi.info && (
                  <span onClick={(e) => e.stopPropagation()}>
                    <InfoButton title={kpi.name}>{kpi.info}</InfoButton>
                  </span>
                )}
              </div>
              <p className="text-2xl font-bold text-slate-900 mt-1">{kpi.value.toLocaleString()}</p>
            </div>
          </button>
        ))}
      </div>

      {/* Risk Distribution */}
      {stats?.risk_distribution && (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <h2 className="font-bold text-slate-900">Risk Distribution</h2>
            <InfoButton title="Risk Distribution">Shows how all scored providers fall into three risk bands. High Risk (score ≥ 51): priority investigation. Review (31–50): warrants closer look. Stable (≤ 30): normal billing patterns. Scores come from deterministic rules applied to peer-comparison z-scores.</InfoButton>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'High Risk', value: stats.risk_distribution.high_risk, color: 'bg-rose-500' },
              { label: 'Review', value: stats.risk_distribution.review, color: 'bg-amber-500' },
              { label: 'Stable', value: stats.risk_distribution.stable, color: 'bg-emerald-500' },
            ].map((band) => {
              const total = stats.risk_distribution.high_risk + stats.risk_distribution.review + stats.risk_distribution.stable;
              const pct = total > 0 ? ((band.value / total) * 100).toFixed(1) : '0';
              return (
                <div key={band.label}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-600">{band.label}</span>
                    <span className="text-sm font-bold text-slate-900">{band.value.toLocaleString()}</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className={cn('h-full rounded-full', band.color)} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{pct}%</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Top Providers */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-900">Top Flagged Providers</h2>
              <InfoButton title="Top Flagged Providers">Providers ranked by their highest service-line risk score. Shows specialty, state, total estimated Medicare payment, and risk band. Click any provider to view their full risk profile and scoring breakdown.</InfoButton>
            </div>
            <Link to="/providers" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
              View All
            </Link>
          </div>
          <div className="space-y-3">
            {(stats?.top_providers ?? []).slice(0, 8).map((p) => (
              <Link
                key={p.npi}
                to={`/providers/${p.npi}`}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-200 bg-slate-50 hover:border-indigo-200 hover:bg-indigo-50/40 transition-colors"
              >
                <div>
                  <p className="font-semibold text-slate-900">{providerDisplayName(p)}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {p.provider_type ?? 'Unknown'} · {p.state ?? '—'} · {formatCompactUSD(p.total_estimated_payment)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge band={p.risk_band} size="sm" />
                  <span className={cn('font-bold text-sm', scoreColor(p.max_seed_risk_score))}>
                    {p.max_seed_risk_score ?? '—'}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Pending Cases */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-900">Pending Review Cases</h2>
              <InfoButton title="Pending Review Cases">Cases awaiting analyst review, ordered by risk score. Each entry shows the HCPCS service code, description, average submitted charge, and computed risk score. Click to open the full investigation view.</InfoButton>
            </div>
            <Link to="/investigations" className="text-xs font-semibold text-indigo-600 hover:text-indigo-700">
              View All
            </Link>
          </div>
          <div className="space-y-3">
            {pending.length ? pending.map((c) => (
              <Link
                key={c.case_id}
                to={`/investigations/${c.case_id}`}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-200 bg-slate-50 hover:border-indigo-200 hover:bg-indigo-50/40 transition-colors"
              >
                <div>
                  <p className="font-semibold text-slate-900">{c.provider_last_org_name ?? c.npi}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {c.hcpcs_cd} · {c.hcpcs_desc ?? ''} · {formatCompactUSD(c.avg_submitted_charge)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn('font-bold text-sm', scoreColor(c.seed_risk_score))}>
                    {c.seed_risk_score ?? '—'}
                  </span>
                </div>
              </Link>
            )) : (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
                No cases are currently pending review.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
