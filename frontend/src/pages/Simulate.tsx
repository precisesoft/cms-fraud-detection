import React from 'react';
import { Zap, AlertTriangle, DollarSign, Stethoscope, Hash, MapPin, Users, Brain, Activity } from 'lucide-react';
import { simulateClaim } from '../lib/api';
import type { ClaimSimulationResult, ClaimSimulationRequest } from '../lib/api';
import { cn } from '../lib/utils';
import { scoreColor, riskBandLabel, riskBandColor } from '../lib/helpers';
import { InfoButton } from '../components/InfoButton';

export function Simulate() {
  const [form, setForm] = React.useState<ClaimSimulationRequest>({
    npi: '',
    hcpcs_cd: '',
    submitted_charge: 100,
    num_services: 10,
    num_benes: 5,
    place_of_service: '11',
  });
  const [result, setResult] = React.useState<ClaimSimulationResult | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await simulateClaim(form);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const setField = <K extends keyof ClaimSimulationRequest>(key: K, value: ClaimSimulationRequest[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Claim Simulation</h1>
        <p className="mt-1 text-sm text-slate-500">Test how a hypothetical claim would be scored by the risk engine.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Input Form */}
        <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-6">
            <Zap className="w-5 h-5 text-indigo-500" /> Claim Parameters
            <InfoButton title="Claim Parameters">
              Enter hypothetical claim parameters to test how the risk engine
              scores them. NPI identifies the provider; HCPCS is the procedure
              code. Charges, service counts, and beneficiary counts are compared
              against peer baselines for same-specialty, same-state providers.
            </InfoButton>
          </h3>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="simulate-npi" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">NPI</label>
                <div className="relative">
                  <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input id="simulate-npi" type="text" value={form.npi} onChange={(e) => setField('npi', e.target.value)} required className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all font-mono" placeholder="1234567890" />
                </div>
              </div>
              <div>
                <label htmlFor="simulate-hcpcs" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">HCPCS Code</label>
                <div className="relative">
                  <Stethoscope className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input id="simulate-hcpcs" type="text" value={form.hcpcs_cd} onChange={(e) => setField('hcpcs_cd', e.target.value)} required className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all font-mono" placeholder="99213" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label htmlFor="simulate-charge" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Submitted Charge ($)</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input id="simulate-charge" type="number" value={form.submitted_charge} onChange={(e) => setField('submitted_charge', Number(e.target.value))} required className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all" />
                </div>
              </div>
              <div>
                <label htmlFor="simulate-services" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Services</label>
                <div className="relative">
                  <Hash className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input id="simulate-services" type="number" value={form.num_services} onChange={(e) => setField('num_services', Number(e.target.value))} required className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all" />
                </div>
              </div>
              <div>
                <label htmlFor="simulate-beneficiaries" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Beneficiaries</label>
                <div className="relative">
                  <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input id="simulate-beneficiaries" type="number" value={form.num_benes} onChange={(e) => setField('num_benes', Number(e.target.value))} required className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all" />
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="simulate-place-of-service" className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Place of Service</label>
              <div className="relative">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input id="simulate-place-of-service" type="text" value={form.place_of_service ?? ''} onChange={(e) => setField('place_of_service', e.target.value)} className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all" placeholder="11" />
              </div>
            </div>

            <button type="submit" disabled={loading} className="w-full py-3 bg-indigo-600 text-white font-bold text-sm rounded-xl hover:bg-indigo-700 transition-all shadow-sm hover:shadow-md disabled:opacity-50 flex items-center justify-center gap-2">
              {loading ? <span aria-hidden="true" className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <Zap aria-hidden="true" className="w-4 h-4" />}
              {loading ? 'Scoring...' : 'Run Simulation'}
            </button>
          </form>

          {error && (
            <div role="alert" className="mt-4 p-4 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-700 flex items-start gap-2">
              <AlertTriangle aria-hidden="true" className="w-4 h-4 mt-0.5 flex-shrink-0" /> {error}
            </div>
          )}
        </div>

        {/* Results */}
        <div className="space-y-6">
          {result ? (
            <>
              {/* Score Header */}
              <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Risk Score</p>
                  <InfoButton title="Risk Score">
                    Computed risk score from 0 to 100 combining deterministic rules and peer-comparison z-scores. Stable (≤ 30): normal billing patterns. Review (31–50): warrants closer look. High Risk (≥ 51): priority investigation. This is the primary, fully explainable score.
                  </InfoButton>
                </div>
                <p className={cn('text-6xl font-black leading-none', scoreColor(result.risk_score))}>{result.risk_score}</p>
                <div className="mt-3 flex items-center justify-center gap-3">
                  <span className={cn('px-3 py-1 rounded-full text-xs font-bold uppercase', riskBandColor(result.risk_band))}>
                    {riskBandLabel(result.risk_band)}
                  </span>
                  <span className="text-xs text-slate-500">Recommendation: <span className="font-bold text-slate-700 capitalize">{result.recommendation}</span></span>
                </div>
                {result.provider_name && <p className="mt-3 text-sm text-slate-600">{result.provider_name} · {result.provider_type ?? '—'} · {result.state ?? '—'}</p>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider">
                    <Activity className="w-4 h-4 text-amber-500" />
                    Anomaly Score
                    <InfoButton title="Anomaly Score">
                      Isolation Forest unsupervised machine learning score measuring how unusual this provider&apos;s billing patterns are relative to all providers in the dataset. Computed independently from the rule-based score. Higher values indicate more anomalous billing.
                    </InfoButton>
                  </div>
                  <p className="mt-3 text-3xl font-black text-slate-900">
                    {result.anomaly_score != null ? result.anomaly_score.toFixed(1) : '—'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Isolation-forest outlier score</p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase tracking-wider">
                    <Brain className="w-4 h-4 text-indigo-500" />
                    ML Suspicion
                    <InfoButton title="ML Suspicion Probability">
                      Weakly supervised model probability that this claim exhibits fraud-like patterns. Trained on Isolation Forest anomaly labels, not human labels. Used as an assistive signal to complement the primary rule-based score — never used alone for classification.
                    </InfoButton>
                  </div>
                  <p className="mt-3 text-3xl font-black text-slate-900">
                    {result.ml_predicted_probability != null ? `${result.ml_predicted_probability.toFixed(1)}%` : '—'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">Weakly supervised fraud probability</p>
                </div>
              </div>

              {/* Narrative */}
              {result.narrative && (
                <div className="bg-slate-900 text-white p-6 rounded-xl shadow-xl">
                  <div className="flex items-center gap-2 mb-3">
                    <p className="text-indigo-300 text-xs font-bold uppercase tracking-widest">AI Narrative</p>
                    <InfoButton title="AI-Generated Narrative">
                      Natural language explanation generated by Claude (AWS Bedrock) describing why this claim received its risk score. Written for analysts to quickly understand key risk factors, peer deviations, and relevant context without reading raw data.
                    </InfoButton>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-200">{result.narrative}</p>
                </div>
              )}

              {/* Signals */}
              {result.signals.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" /> Signals
                    <InfoButton title="Risk & Legitimacy Signals">
                      Individual signals from the scoring taxonomy that
                      contributed to the final score. Risk signals (red)
                      increase the score — e.g., billing volume 3x peer
                      average. Legitimacy signals (green) reduce it — e.g.,
                      consistent Medicare participation. Each signal has a
                      category, description, and measured value.
                    </InfoButton>
                  </h3>
                  <div className="space-y-2">
                    {result.signals.map((s) => (
                      <div key={s.name} className={cn('p-3 rounded-lg border', s.direction === 'risk' ? 'bg-rose-50/50 border-rose-100' : 'bg-emerald-50/50 border-emerald-100')}>
                        <div className="flex items-center justify-between">
                          <span className={cn('text-xs font-bold', s.direction === 'risk' ? 'text-rose-900' : 'text-emerald-900')}>{s.name}</span>
                          <span className="text-[9px] font-black uppercase px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">{s.category}</span>
                        </div>
                        <p className="text-[11px] text-slate-600 mt-1">{s.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Peer Comparisons */}
              {result.peer_comparisons.length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                  <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                    Peer Comparisons
                    <InfoButton title="Peer Comparison">
                      How this provider&apos;s metrics compare to peers billing
                      the same HCPCS code in the same specialty and state.
                      Z-scores measure standard deviations from the peer mean.
                      Z &gt; 2 indicates the provider is a statistical outlier
                      for that metric.
                    </InfoButton>
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-slate-200 text-xs">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">Metric</th>
                          <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">Provider</th>
                          <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">Peer Mean</th>
                          <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">Z-Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {result.peer_comparisons.map((pc) => (
                          <tr key={pc.metric}>
                            <td className="px-4 py-3 font-medium text-slate-700">{pc.metric}</td>
                            <td className="px-4 py-3 text-right text-slate-700">{pc.provider_value.toFixed(1)}</td>
                            <td className="px-4 py-3 text-right text-slate-700">{pc.peer_mean.toFixed(1)}</td>
                            <td className={cn('px-4 py-3 text-right font-bold', Math.abs(pc.z_score) > 2 ? 'text-rose-600' : 'text-slate-700')}>{pc.z_score.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] bg-white rounded-2xl border border-dashed border-slate-200 p-12">
              <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
                <Zap className="w-8 h-8 text-indigo-400" />
              </div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">Ready to Simulate</h3>
              <p className="text-sm text-slate-500 text-center max-w-sm">Fill in the claim parameters on the left and run the simulation to see how the risk engine would score this claim.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
