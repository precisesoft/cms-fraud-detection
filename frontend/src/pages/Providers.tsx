import React from 'react';
import { cn } from '../lib/utils';
import { Search, Download, MapPin, Stethoscope, ExternalLink, MoreHorizontal } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { getProviders } from '../lib/api';
import type { ProviderSummary, PaginationMeta } from '../lib/api';
import { StatusBadge } from '../components/StatusBadge';
import { formatCompactUSD, scoreColor, providerDisplayName } from '../lib/helpers';

export function Providers() {
  const [searchParams] = useSearchParams();
  const initialState = searchParams.get('state') || '';
  const initialRiskBand = searchParams.get('risk_band') || '';

  const [searchTerm, setSearchTerm] = React.useState('');
  const [stateFilter, setStateFilter] = React.useState(initialState);
  const [riskBandFilter, setRiskBandFilter] = React.useState(initialRiskBand);
  const [providers, setProviders] = React.useState<ProviderSummary[]>([]);
  const [meta, setMeta] = React.useState<PaginationMeta>({ total: 0, page: 1, per_page: 50, pages: 1 });

  React.useEffect(() => {
    let active = true;
    getProviders({
      page: meta.page,
      per_page: 50,
      q: searchTerm || undefined,
      state: stateFilter || undefined,
      risk_band: riskBandFilter || undefined,
    })
      .then((data) => {
        if (active) {
          setProviders(data.data);
          setMeta(data.meta);
        }
      })
      .catch(() => {
        if (active) {
          setProviders([]);
          setMeta({ total: 0, page: 1, per_page: 50, pages: 1 });
        }
      });
    return () => { active = false; };
  }, [meta.page, searchTerm, stateFilter, riskBandFilter]);

  React.useEffect(() => {
    setMeta((c) => ({ ...c, page: 1 }));
  }, [searchTerm, stateFilter, riskBandFilter]);

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Providers</h1>
          <p className="text-slate-500 text-sm mt-1">Manage and investigate healthcare provider risk profiles.</p>
        </div>
        <button className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-md text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors shadow-sm">
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Summary */}
      <div className="bg-indigo-900 text-white rounded-xl p-4 flex flex-wrap items-center gap-8 shadow-lg shadow-indigo-200">
        <div>
          <p className="text-indigo-300 text-[10px] font-bold uppercase tracking-wider">Total Results</p>
          <p className="text-xl font-bold">{meta.total.toLocaleString()}</p>
        </div>
        <div className="w-px h-8 bg-indigo-800 hidden sm:block" />
        <div>
          <p className="text-indigo-300 text-[10px] font-bold uppercase tracking-wider">Page</p>
          <p className="text-xl font-bold">{meta.page} / {meta.pages}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by name, NPI..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <input
          type="text"
          placeholder="State (e.g. FL)"
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500 w-32"
          value={stateFilter}
          onChange={(e) => setStateFilter(e.target.value.toUpperCase().slice(0, 2))}
        />
        <select
          value={riskBandFilter}
          onChange={(e) => setRiskBandFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">All Risk Bands</option>
          <option value="high_risk">High Risk</option>
          <option value="review">Review</option>
          <option value="stable">Stable</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">Provider</th>
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">Type</th>
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">Location</th>
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">Est. Payment</th>
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider">Risk Band</th>
                <th className="px-6 py-4 font-semibold text-slate-600 uppercase text-[10px] tracking-wider text-right">Score</th>
                <th className="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {providers.map((p) => (
                <tr key={p.npi} className="group hover:bg-slate-50 transition-colors cursor-pointer">
                  <td className="px-6 py-4">
                    <Link to={`/providers/${p.npi}`} className="block">
                      <div className="font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">{providerDisplayName(p)}</div>
                      <div className="text-xs text-slate-400 font-mono">NPI: {p.npi}</div>
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <Stethoscope className="w-3.5 h-3.5 text-slate-400" />
                      {p.provider_type ?? '—'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      {p.city ?? '—'}, {p.state ?? '—'}
                    </div>
                  </td>
                  <td className="px-6 py-4 font-medium text-slate-700">{formatCompactUSD(p.total_estimated_payment)}</td>
                  <td className="px-6 py-4"><StatusBadge band={p.risk_band} size="sm" /></td>
                  <td className="px-6 py-4 text-right">
                    <span className={cn('font-bold text-sm', scoreColor(p.max_seed_risk_score))}>
                      {p.max_seed_risk_score ?? '—'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Link to={`/providers/${p.npi}`} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded transition-colors">
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-slate-50 px-6 py-4 border-t border-slate-200 flex items-center justify-between">
          <p className="text-xs text-slate-500">Page {meta.page} of {meta.pages} · {meta.total} provider(s)</p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setMeta((c) => ({ ...c, page: Math.max(1, c.page - 1) }))}
              disabled={meta.page <= 1}
              className={cn('px-3 py-1 bg-white border border-slate-200 rounded text-xs font-medium', meta.page <= 1 ? 'text-slate-400 cursor-not-allowed' : 'text-slate-600 hover:bg-slate-50')}
            >
              Previous
            </button>
            <button
              onClick={() => setMeta((c) => ({ ...c, page: Math.min(c.pages, c.page + 1) }))}
              disabled={meta.page >= meta.pages}
              className={cn('px-3 py-1 bg-white border border-slate-200 rounded text-xs font-medium', meta.page >= meta.pages ? 'text-slate-400 cursor-not-allowed' : 'text-slate-600 hover:bg-slate-50')}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
