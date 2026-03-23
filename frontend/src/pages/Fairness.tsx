import React from 'react';
import { AlertTriangle, CheckCircle, BarChart3, Info } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { getFairness } from '../lib/api';
import type { FairnessReport } from '../lib/api';
import { cn } from '../lib/utils';

export function Fairness() {
  const [report, setReport] = React.useState<FairnessReport | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [tab, setTab] = React.useState<'state' | 'specialty'>('state');
  const [threshold, setThreshold] = React.useState(51);
  const [blind, setBlind] = React.useState(false);

  const fetchReport = React.useCallback(() => {
    setLoading(true);
    getFairness({ threshold, blind })
      .then((r) => setReport(r))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [threshold, blind]);

  React.useEffect(() => { fetchReport(); }, [fetchReport]);

  const cohorts = tab === 'state' ? report?.by_state ?? [] : report?.by_specialty ?? [];
  const chartData = [...cohorts].sort((a, b) => b.flagging_rate - a.flagging_rate).slice(0, 25).map((c) => ({
    name: c.cohort,
    rate: +(c.flagging_rate * 100).toFixed(1),
    count: c.provider_count,
    flagged: c.flagged_count,
    isOutlier: c.is_outlier,
  }));

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Fairness Analysis</h1>
          <p className="mt-1 text-sm text-slate-500">Evaluate flagging rate parity across provider cohorts.</p>
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col md:flex-row items-start md:items-center gap-4">
        <div className="flex items-center gap-3">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Threshold</label>
          <input type="number" value={threshold} onChange={(e) => setThreshold(Number(e.target.value))} className="w-20 px-3 py-2 text-sm rounded-lg border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <input type="checkbox" checked={blind} onChange={(e) => setBlind(e.target.checked)} className="rounded border-slate-300" />
          Revocation-blind mode
        </label>
        <div className="flex bg-slate-100 rounded-lg p-1 ml-auto">
          <button onClick={() => setTab('state')} className={cn('px-4 py-1.5 text-xs font-bold rounded-md transition-all', tab === 'state' ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700')}>By State</button>
          <button onClick={() => setTab('specialty')} className={cn('px-4 py-1.5 text-xs font-bold rounded-md transition-all', tab === 'specialty' ? 'bg-white shadow text-slate-900' : 'text-slate-500 hover:text-slate-700')}>By Specialty</button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
      ) : report ? (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Overall Flagging Rate</p>
              <p className="text-3xl font-black text-slate-900">{(report.overall_flagging_rate * 100).toFixed(1)}%</p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Statistical Parity Diff</p>
              <p className={cn('text-3xl font-black', report.statistical_parity_diff != null && Math.abs(report.statistical_parity_diff) > 0.1 ? 'text-rose-600' : 'text-emerald-600')}>
                {report.statistical_parity_diff != null ? report.statistical_parity_diff.toFixed(3) : '—'}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Disparate Impact Ratio</p>
              <p className={cn('text-3xl font-black', report.disparate_impact_ratio != null && report.disparate_impact_ratio < 0.8 ? 'text-rose-600' : 'text-emerald-600')}>
                {report.disparate_impact_ratio != null ? report.disparate_impact_ratio.toFixed(3) : '—'}
              </p>
            </div>
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Outlier Cohorts</p>
              <p className="text-3xl font-black text-amber-600">{cohorts.filter((c) => c.is_outlier).length}</p>
            </div>
          </div>

          {/* Chart */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-indigo-500" /> Flagging Rate by {tab === 'state' ? 'State' : 'Specialty'}</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fontWeight: 600, fill: '#64748b' }} angle={-45} textAnchor="end" />
                  <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v: number) => `${v}%`} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} formatter={(value: number) => [`${value}%`, 'Flagging Rate']} />
                  <ReferenceLine y={report.overall_flagging_rate * 100} stroke="#94a3b8" strokeDasharray="4 4" label={{ value: 'Overall', position: 'right', fontSize: 10 }} />
                  <Bar dataKey="rate" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revocation Impact */}
          {report.revocation_impact && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><Info className="w-4 h-4 text-sky-500" /> Revocation Impact Analysis</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">With Revocation</p>
                  <p className="text-lg font-bold text-slate-900">{(report.revocation_impact.overall_flagging_rate_with * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Without Revocation</p>
                  <p className="text-lg font-bold text-slate-900">{(report.revocation_impact.overall_flagging_rate_without * 100).toFixed(1)}%</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Rate Delta</p>
                  <p className="text-lg font-bold text-amber-600">{(report.revocation_impact.flagging_rate_delta * 100).toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">DI Ratio (With)</p>
                  <p className="text-lg font-bold text-slate-900">{report.revocation_impact.disparate_impact_with?.toFixed(3) ?? '—'}</p>
                </div>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50/80">
                  <tr>
                    <th className="px-5 py-3.5 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Cohort</th>
                    <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Providers</th>
                    <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Flagged</th>
                    <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Rate</th>
                    <th className="px-5 py-3.5 text-center text-[10px] font-bold text-slate-500 uppercase tracking-widest">Outlier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {cohorts.map((c) => (
                    <tr key={c.cohort} className={cn('hover:bg-slate-50/60 transition-colors', c.is_outlier && 'bg-amber-50/40')}>
                      <td className="px-5 py-3 text-xs font-semibold text-slate-800">{c.cohort}</td>
                      <td className="px-5 py-3 text-xs text-right text-slate-700">{c.provider_count.toLocaleString()}</td>
                      <td className="px-5 py-3 text-xs text-right text-slate-700">{c.flagged_count}</td>
                      <td className="px-5 py-3 text-xs text-right font-bold text-slate-900">{(c.flagging_rate * 100).toFixed(1)}%</td>
                      <td className="px-5 py-3 text-center">
                        {c.is_outlier ? <AlertTriangle className="w-4 h-4 text-amber-500 mx-auto" /> : <CheckCircle className="w-4 h-4 text-emerald-400 mx-auto" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="text-sm text-slate-400 p-8 text-center">Unable to load fairness report.</div>
      )}
    </div>
  );
}
