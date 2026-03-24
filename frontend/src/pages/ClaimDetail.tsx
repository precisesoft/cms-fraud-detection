import React from 'react';
import { ArrowLeft, ClipboardCheck, ClipboardX, AlertTriangle, ArrowUpRight, FileText, Stethoscope, MessageSquareMore } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { getClaim, getCaseActions, caseAction, getClaimScoreDetails } from '../lib/api';
import type { Claim, CaseActionRecord, ClaimScoreDetails } from '../lib/api';
import { cn } from '../lib/utils';
import { formatUSD, scoreColor } from '../lib/helpers';
import { Timeline } from '../components/Timeline';

import { AssistantDrawer } from '../components/AssistantDrawer';

export function ClaimDetail() {
  const { caseId } = useParams();
  const [claim, setClaim] = React.useState<Claim | null>(null);
  const [actions, setActions] = React.useState<CaseActionRecord[]>([]);
  const [scoreDetails, setScoreDetails] = React.useState<ClaimScoreDetails | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [actionLoading, setActionLoading] = React.useState<string | null>(null);
  const [chatOpen, setChatOpen] = React.useState(false);

  React.useEffect(() => {
    if (!caseId) return;
    let active = true;
    setLoading(true);
    Promise.all([
      getClaim(caseId).then((c) => { if (active) setClaim(c); }).catch(() => {}),
      getCaseActions(caseId).then((r) => { if (active) setActions(r.actions); }).catch(() => {}),
      getClaimScoreDetails(caseId).then((d) => { if (active) setScoreDetails(d); }).catch(() => {}),
    ]).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [caseId]);

  const actionMap = { approve: 'APPROVED', flag: 'FLAGGED', deny: 'DENIED', escalate: 'ESCALATED' } as const;
  const handleAction = async (action: 'approve' | 'flag' | 'deny' | 'escalate') => {
    if (!caseId) return;
    setActionLoading(action);
    try {
      await caseAction(caseId, actionMap[action], `Analyst action: ${action}`);
      const updated = await getCaseActions(caseId);
      setActions(updated.actions);
    } catch {
      /* swallow */
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Link to="/claims" className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 text-sm font-medium"><ArrowLeft className="w-4 h-4" />Back to Claims</Link>
        <p className="text-sm text-slate-400">Loading...</p>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="space-y-4">
        <Link to="/claims" className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 text-sm font-medium"><ArrowLeft className="w-4 h-4" />Back to Claims</Link>
        <p className="text-sm text-slate-400">Claim not found.</p>
      </div>
    );
  }

  const actionButtons: { action: 'approve' | 'flag' | 'deny' | 'escalate'; label: string; icon: React.ReactNode; colors: string }[] = [
    { action: 'approve', label: 'Approve', icon: <ClipboardCheck className="w-4 h-4" />, colors: 'bg-emerald-600 hover:bg-emerald-700 text-white' },
    { action: 'flag', label: 'Flag', icon: <AlertTriangle className="w-4 h-4" />, colors: 'bg-amber-500 hover:bg-amber-600 text-white' },
    { action: 'deny', label: 'Deny', icon: <ClipboardX className="w-4 h-4" />, colors: 'bg-rose-600 hover:bg-rose-700 text-white' },
    { action: 'escalate', label: 'Escalate', icon: <ArrowUpRight className="w-4 h-4" />, colors: 'bg-indigo-600 hover:bg-indigo-700 text-white' },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <Link to="/claims" className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors text-sm font-medium w-fit">
        <ArrowLeft className="w-4 h-4" /> Back to Claims
      </Link>

      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900">Case {caseId}</h1>
              <span className={cn('px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase', claim.seed_case_label?.includes('high') ? 'bg-rose-100 text-rose-700' : claim.seed_case_label?.includes('review') ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700')}>
                {claim.seed_case_label ?? 'Unknown'}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-2 text-sm text-slate-500">
              <div className="flex items-center gap-1.5"><Stethoscope className="w-4 h-4" />NPI: <Link to={`/providers/${claim.npi}`} className="text-indigo-600 hover:underline font-medium">{claim.npi}</Link></div>
              <div className="flex items-center gap-1.5"><FileText className="w-4 h-4" />HCPCS: <span className="font-mono font-medium">{claim.hcpcs_cd}</span></div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={() => setChatOpen(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition-colors">
              <MessageSquareMore className="w-4 h-4" /> Ask about this claim
            </button>
            <div className="flex items-center gap-6 px-6 py-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Risk Score</p>
                <p className={cn('text-4xl font-black leading-none', scoreColor(claim.seed_risk_score))}>{claim.seed_risk_score ?? '—'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {[
              {
                name: 'Explainable Risk',
                value: scoreDetails?.explainable_risk_score ?? claim.seed_risk_score,
                sub: 'Primary transparent score',
              },
              {
                name: 'Claim Anomaly',
                value: scoreDetails?.anomaly_score,
                sub: 'Case-level anomaly signal',
              },
              {
                name: 'ML Suspicion',
                value: scoreDetails?.ml_predicted_probability,
                sub: 'Weakly supervised probability',
              },
              {
                name: 'Hybrid Composite',
                value: scoreDetails?.hybrid_composite_score,
                sub: scoreDetails?.hybrid_risk_label ? `Assistive layer · ${scoreDetails.hybrid_risk_label}` : 'Assistive hybrid layer',
              },
            ].map((card) => (
              <div key={card.name} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{card.name}</p>
                <p className={cn('text-3xl font-black leading-none', scoreColor(typeof card.value === 'number' ? card.value : null))}>
                  {typeof card.value === 'number' ? card.value.toFixed(1).replace(/\.0$/, '') : '—'}
                </p>
                <p className="text-[10px] text-slate-500 mt-2 font-medium">{card.sub}</p>
              </div>
            ))}
          </div>

          {/* Claim Details */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-6">Service Line Details</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
              {[
                ['HCPCS Code', claim.hcpcs_cd],
                ['Services', claim.tot_srvcs?.toLocaleString() ?? '—'],
                ['Beneficiaries', claim.tot_benes?.toLocaleString() ?? '—'],
                ['Submitted Charge', formatUSD(claim.avg_submitted_charge)],
                ['Est. Payment', formatUSD(claim.avg_medicare_payment_amt)],
                ['Provider Type', claim.provider_type ?? '—'],
                ['State', claim.state ?? '—'],
                ['Place of Service', claim.place_of_service ?? '—'],
              ].map(([name, value]: [string, string]) => (
                <div key={name}>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{name}</p>
                  <p className="text-sm font-semibold text-slate-800">{value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Peer Comparison Context */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <h3 className="font-bold text-slate-800">Z-Score Metrics</h3>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
              {[
                ['Volume Peer Z', claim['service_volume_peer_z'] as number | null],
                ['Charge Peer Z', claim['charge_peer_z'] as number | null],
                ['Bene Peer Z', claim['bene_peer_z'] as number | null],
                ['Service/Bene Z', claim['services_per_bene_peer_z'] as number | null],
              ].map(([name, value]) => (
                <div key={name as string}>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">{name}</p>
                  <p className={cn('text-lg font-bold', (value as number ?? 0) > 2 ? 'text-rose-600' : (value as number ?? 0) > 1 ? 'text-amber-600' : 'text-slate-800')}>
                    {(value as number)?.toFixed(2) ?? '—'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-4">Take Action</h3>
            <div className="flex flex-wrap gap-3">
              {actionButtons.map((btn) => (
                <button key={btn.action} disabled={actionLoading !== null} onClick={() => handleAction(btn.action)} className={cn('inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all shadow-sm hover:shadow-md disabled:opacity-50', btn.colors)}>
                  {actionLoading === btn.action ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : btn.icon}
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Timeline */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-4">Action History</h3>
            {actions.length > 0 ? (
              <Timeline events={actions} />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">No actions yet.</div>
            )}
          </div>
        </div>
      </div>

      <AssistantDrawer isOpen={chatOpen} onClose={() => setChatOpen(false)} context={{ type: 'claim', entityId: caseId ?? '', label: `Case ${caseId}` }} />
    </div>
  );
}
