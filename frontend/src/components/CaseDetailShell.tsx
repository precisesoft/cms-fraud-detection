import React from "react";
import {
  ArrowLeft,
  ClipboardCheck,
  ClipboardX,
  AlertTriangle,
  ArrowUpRight,
  Info,
  MessageSquareMore,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import type { Claim } from "../lib/api";
import { cn } from "../lib/utils";
import { scoreColor } from "../lib/helpers";
import { Timeline } from "./Timeline";
import { AssistantDrawer } from "./AssistantDrawer";
import { useCaseDetail } from "../hooks/useCaseDetail";
import { InfoButton } from "./InfoButton";

interface CaseDetailShellProps {
  backPath: string;
  backLabel: string;
  entityType: "claim" | "investigation";
  notFoundLabel: string;
  chatButtonLabel: string;
  renderHeader: (data: Claim, caseId: string) => React.ReactNode;
  renderDetails: (data: Claim) => React.ReactNode;
  extraSections?: (data: Claim) => React.ReactNode;
}

export function CaseDetailShell({
  backPath,
  backLabel,
  entityType,
  notFoundLabel,
  chatButtonLabel,
  renderHeader,
  renderDetails,
  extraSections,
}: CaseDetailShellProps) {
  const { caseId } = useParams();
  const ctx = useCaseDetail(caseId);

  const backLink = (
    <Link
      to={backPath}
      className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors text-sm font-medium w-fit"
    >
      <ArrowLeft className="w-4 h-4" /> {backLabel}
    </Link>
  );

  if (ctx.loading) {
    return (
      <div className="space-y-4">
        {backLink}
        <div role="status" aria-label="Loading case details" className="flex items-center gap-3 text-sm text-slate-400">
          <span aria-hidden="true" className="w-4 h-4 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  if (!ctx.data) {
    return (
      <div className="space-y-4">
        {backLink}
        <p className="text-sm text-slate-500">{notFoundLabel}</p>
      </div>
    );
  }

  const actionButtons: {
    action: "approve" | "flag" | "deny" | "escalate";
    label: string;
    icon: React.ReactNode;
    colors: string;
  }[] = [
    {
      action: "approve",
      label: "Approve",
      icon: <ClipboardCheck className="w-4 h-4" />,
      colors: "bg-emerald-700 hover:bg-emerald-800 text-white",
    },
    {
      action: "flag",
      label: "Flag",
      icon: <AlertTriangle className="w-4 h-4" />,
      colors: "bg-amber-700 hover:bg-amber-800 text-white",
    },
    {
      action: "deny",
      label: "Deny",
      icon: <ClipboardX className="w-4 h-4" />,
      colors: "bg-rose-600 hover:bg-rose-700 text-white",
    },
    {
      action: "escalate",
      label: "Escalate",
      icon: <ArrowUpRight className="w-4 h-4" />,
      colors: "bg-indigo-600 hover:bg-indigo-700 text-white",
    },
  ];

  const scoreCards = [
    {
      name: "Explainable Risk",
      value:
        ctx.scoreDetails?.explainable_risk_score ?? ctx.data.seed_risk_score,
      denominator: "/ 100",
      sub: ctx.scoreDetails?.explainable_risk_band
        ? `Rule-based · ${ctx.scoreDetails.explainable_risk_band.replace("_", " ")} band`
        : "Primary transparent score",
      infoTitle: "Explainable Risk Score",
      infoText:
        "Primary decision anchor — fully rule-based and auditable. Scale: 0–100. Bands: 0–30 Stable · 31–50 Review · 51+ High Risk. Built from peer z-scores, enrollment signals, and billing pattern rules. This score alone can justify escalation.",
    },
    {
      name: "Claim Anomaly",
      value: ctx.scoreDetails?.anomaly_score,
      denominator: "/ 65",
      sub: "Charge + intensity deviation",
      infoTitle: "Claim Anomaly Score",
      infoText:
        "Case-level anomaly signal. Scale: 0–65. Combines charge peer deviation (submitted vs. allowed, max 45 pts) and services-per-beneficiary intensity (max 20 pts). A score above 30 indicates strong billing pattern deviation. Independent from the rule-based score — use as corroboration.",
    },
    {
      name: "ML Suspicion",
      value: ctx.scoreDetails?.ml_predicted_probability,
      denominator: "/ 1.0",
      sub: "Fraud probability · 0 to 1 scale",
      infoTitle: "ML Suspicion Probability",
      infoText:
        "Weakly supervised model fraud probability for this service line. Scale: 0 to 1. Above 0.5 = suspicious · 0.75+ = strong signal · 0.9+ = very high confidence. Trained on Isolation Forest labels, not human-labeled fraud — always treat as an assistive corroboration signal.",
    },
    {
      name: "Hybrid Composite",
      value: ctx.scoreDetails?.hybrid_composite_score,
      denominator: "/ 100",
      sub: ctx.scoreDetails?.hybrid_risk_label
        ? `Score out of 100 · ${ctx.scoreDetails.hybrid_risk_label} band`
        : "Combined rule + ML signal",
      infoTitle: "Hybrid Composite Score",
      infoText:
        "Combined score for this service line (0–100). Blends rule-based signals (45%), Isolation Forest anomaly (30%), billing context (10%), and ML probability (15%). Bands: < 40 Low · 40–69 Medium · 70–89 High · 90+ Critical. When this converges with a high Explainable Risk score, the case is significantly stronger.",
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      {backLink}

      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          {renderHeader(ctx.data, caseId ?? "")}
          <div className="flex items-center gap-4">
            <button
              onClick={() => ctx.setChatOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition-colors"
            >
              <MessageSquareMore className="w-4 h-4" /> {chatButtonLabel}
            </button>
            <div className="flex items-center gap-6 px-6 py-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-center">
                <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-1">
                  Risk Score
                </p>
                <p
                  className={cn(
                    "text-4xl font-black leading-none",
                    scoreColor(ctx.data.seed_risk_score),
                  )}
                >
                  {ctx.data.seed_risk_score ?? "—"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Score Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {scoreCards.map((card) => (
              <div
                key={card.name}
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
              >
                <div className="flex items-center gap-1.5 mb-2">
                  <p className="text-xs font-bold text-slate-600 uppercase tracking-widest">
                    {card.name}
                  </p>
                  <InfoButton title={card.infoTitle}>{card.infoText}</InfoButton>
                </div>
                <div className="flex items-baseline gap-1.5">
                  <p
                    className={cn(
                      "text-3xl font-black leading-none",
                      scoreColor(
                        typeof card.value === "number" ? card.value : null,
                      ),
                    )}
                  >
                    {typeof card.value === "number"
                      ? card.value.toFixed(2).replace(/\.?0+$/, "") || card.value.toFixed(1)
                      : "—"}
                  </p>
                  {card.denominator && typeof card.value === "number" && (
                    <span className="text-sm font-bold text-slate-300">
                      {card.denominator}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-2 font-medium">
                  {card.sub}
                </p>
              </div>
            ))}
          </div>

          {/* Score hierarchy guide */}
          <div className="flex gap-3 items-start bg-indigo-50 border border-indigo-100 rounded-xl px-5 py-3">
            <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <p className="text-xs text-indigo-800 leading-relaxed">
              <span className="font-semibold">How to read these scores: </span>
              <strong>Explainable Risk (0–100)</strong> is the primary decision
              anchor — rule-based, auditable, and sufficient for escalation.{" "}
              <strong>Claim Anomaly (0–65)</strong> measures charge and
              intensity deviation from peers.{" "}
              <strong>ML Suspicion (0–1)</strong> is per-service-line fraud
              probability — above 0.5 is suspicious, 0.9+ is very high
              confidence.{" "}
              <strong>Hybrid Composite (0–100)</strong> blends all signals —
              convergence across multiple high scores significantly strengthens
              a case.
            </p>
          </div>

          {/* Entity-specific details */}
          {renderDetails(ctx.data)}

          {/* Extra sections (e.g. Z-Score) */}
          {extraSections?.(ctx.data)}

          {/* Actions */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h2 className="font-bold text-slate-800 mb-4">Take Action</h2>
            <div className="flex flex-wrap gap-3">
              {actionButtons.map((btn) => (
                <button
                  key={btn.action}
                  disabled={ctx.actionLoading !== null}
                  onClick={() => ctx.handleAction(btn.action)}
                  className={cn(
                    "inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all shadow-sm hover:shadow-md disabled:opacity-50",
                    btn.colors,
                  )}
                >
                  {ctx.actionLoading === btn.action ? (
                    <span aria-hidden="true" className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  ) : (
                    btn.icon
                  )}
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar - Timeline */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h2 className="font-bold text-slate-800 mb-4">Action History</h2>
            {ctx.actions.length > 0 ? (
              <Timeline events={ctx.actions} />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                No actions yet.
              </div>
            )}
          </div>
        </div>
      </div>

      <AssistantDrawer
        isOpen={ctx.chatOpen}
        onClose={() => ctx.setChatOpen(false)}
        context={{
          type: entityType,
          entityId: caseId ?? "",
          label: `${entityType === "claim" ? "Case" : "Investigation"} ${caseId}`,
        }}
      />
    </div>
  );
}
