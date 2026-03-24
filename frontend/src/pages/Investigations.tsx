import React from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, AlertTriangle, ChevronRight } from 'lucide-react';
import { getPendingCases } from '../lib/api';
import type { PendingCase } from '../lib/api';
import { cn } from '../lib/utils';
import { scoreColor, formatUSD, formatCaseId } from '../lib/helpers';

export function Investigations() {
  const [cases, setCases] = React.useState<PendingCase[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    getPendingCases(100)
      .then((d) => { if (active) setCases(d); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Investigations</h1>
          <p className="mt-1 text-sm text-slate-500">Pending high-risk cases requiring analyst review and action.</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          {cases.length} cases pending review
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-dashed border-slate-200">
          <ClipboardList className="w-12 h-12 text-emerald-400 mb-4" />
          <h3 className="text-lg font-bold text-slate-800 mb-2">All Clear</h3>
          <p className="text-sm text-slate-500">No pending investigations at this time.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => (
            <Link key={c.case_id} to={`/investigations/${c.case_id}`} className="block bg-white rounded-xl border border-slate-200 shadow-sm hover:border-indigo-200 hover:shadow-md transition-all p-5 group">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm font-bold text-indigo-600 font-mono">{formatCaseId(c.case_id)}</span>
                    <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-bold uppercase', c.seed_case_label?.includes('high') ? 'bg-rose-100 text-rose-700' : c.seed_case_label?.includes('review') ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700')}>
                      {c.seed_case_label ?? '—'}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-500">
                    <span>NPI: <span className="font-mono font-medium text-slate-700">{c.npi}</span></span>
                    <span>{c.provider_last_org_name ?? '—'}</span>
                    <span>HCPCS: <span className="font-mono">{c.hcpcs_cd}</span></span>
                    {c.hcpcs_desc && <span className="text-slate-400">{c.hcpcs_desc}</span>}
                    <span>Services: {c.tot_srvcs ?? '—'}</span>
                    <span>Charge: {formatUSD(c.avg_submitted_charge)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Risk</p>
                    <p className={cn('text-2xl font-black', scoreColor(c.seed_risk_score))}>{c.seed_risk_score ?? '—'}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
