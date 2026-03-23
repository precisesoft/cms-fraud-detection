import React from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, FileText, Target, Activity } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { getValidation } from '../lib/api';
import type { ValidationReport } from '../lib/api';
import { cn } from '../lib/utils';

export function Validation() {
  const [report, setReport] = React.useState<ValidationReport | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    getValidation()
      .then((r) => { if (active) setReport(r); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20"><span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" /></div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4 animate-in fade-in duration-500">
        <h1 className="text-2xl font-bold text-slate-900">Validation</h1>
        <p className="text-sm text-slate-400">Unable to load validation report.</p>
      </div>
    );
  }

  const chartData = report.detection_by_reason.map((d) => ({
    reason: d.reason,
    rate: +(d.rate * 100).toFixed(1),
    count: d.count,
    detected: d.detected,
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Validation</h1>
        <p className="mt-1 text-sm text-slate-500">Retrospective validation of risk scoring against known revocation outcomes.</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-500"><Target className="w-5 h-5" /></div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Detection Rate</span>
          </div>
          <p className={cn('text-4xl font-black', report.overall_detection_rate >= 0.7 ? 'text-emerald-600' : report.overall_detection_rate >= 0.5 ? 'text-amber-600' : 'text-rose-600')}>
            {(report.overall_detection_rate * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-slate-400 mt-1 font-medium">Overall revocation detection</p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-rose-50 rounded-lg text-rose-500"><AlertTriangle className="w-5 h-5" /></div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Revoked Providers</span>
          </div>
          <p className="text-4xl font-black text-slate-900">{report.total_revoked_providers}</p>
          <p className="text-[10px] text-slate-400 mt-1 font-medium">Total in evaluation set</p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-500"><FileText className="w-5 h-5" /></div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Revoked Cases</span>
          </div>
          <p className="text-4xl font-black text-slate-900">{report.total_revoked_cases}</p>
          <p className="text-[10px] text-slate-400 mt-1 font-medium">Service-level cases flagged</p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-sky-50 rounded-lg text-sky-500"><Activity className="w-5 h-5" /></div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Baseline Rate</span>
          </div>
          <p className="text-4xl font-black text-slate-900">{(report.baseline_flagging_rate * 100).toFixed(1)}%</p>
          <p className="text-[10px] text-slate-400 mt-1 font-medium">Overall flagging rate for context</p>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-500" /> Detection Rate by Revocation Reason</h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 60, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="reason" tick={{ fontSize: 10, fontWeight: 600, fill: '#64748b' }} angle={-45} textAnchor="end" />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} formatter={(value: number) => [`${value}%`, 'Detection Rate']} />
              <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.rate >= 70 ? '#22c55e' : entry.rate >= 50 ? '#eab308' : '#f43f5e'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50/80">
              <tr>
                <th className="px-5 py-3.5 text-left text-[10px] font-bold text-slate-500 uppercase tracking-widest">Revocation Reason</th>
                <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Total</th>
                <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Detected</th>
                <th className="px-5 py-3.5 text-right text-[10px] font-bold text-slate-500 uppercase tracking-widest">Rate</th>
                <th className="px-5 py-3.5 text-center text-[10px] font-bold text-slate-500 uppercase tracking-widest">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.detection_by_reason.map((d) => (
                <tr key={d.reason} className="hover:bg-slate-50/60 transition-colors">
                  <td className="px-5 py-3 text-xs font-semibold text-slate-800">{d.reason}</td>
                  <td className="px-5 py-3 text-xs text-right text-slate-700">{d.count}</td>
                  <td className="px-5 py-3 text-xs text-right text-slate-700">{d.detected}</td>
                  <td className={cn('px-5 py-3 text-xs text-right font-bold', d.rate >= 0.7 ? 'text-emerald-600' : d.rate >= 0.5 ? 'text-amber-600' : 'text-rose-600')}>
                    {(d.rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-5 py-3 text-center">
                    {d.rate >= 0.7 ? <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" /> : d.rate >= 0.5 ? <AlertTriangle className="w-4 h-4 text-amber-500 mx-auto" /> : <AlertTriangle className="w-4 h-4 text-rose-500 mx-auto" />}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology */}
      <div className="bg-slate-900 text-white p-6 rounded-xl shadow-xl">
        <p className="text-indigo-300 text-xs font-bold uppercase tracking-widest mb-3">Methodology</p>
        <p className="text-sm leading-relaxed text-slate-200">{report.methodology}</p>
      </div>
    </div>
  );
}
