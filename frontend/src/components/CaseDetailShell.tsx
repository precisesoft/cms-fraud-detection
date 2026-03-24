import React from "react";
import {
  ArrowLeft,
  ClipboardCheck,
  ClipboardX,
  AlertTriangle,
  ArrowUpRight,
  MessageSquareMore,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import type { Claim } from "../lib/api";
import { cn } from "../lib/utils";
import { scoreColor } from "../lib/helpers";
import { Timeline } from "./Timeline";
import { AssistantDrawer } from "./AssistantDrawer";
import { useCaseDetail } from "../hooks/useCaseDetail";

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
        <p className="text-sm text-slate-400">Loading...</p>
      </div>
    );
  }

  if (!ctx.data) {
    return (
      <div className="space-y-4">
        {backLink}
        <p className="text-sm text-slate-400">{notFoundLabel}</p>
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
      colors: "bg-emerald-600 hover:bg-emerald-700 text-white",
    },
    {
      action: "flag",
      label: "Flag",
      icon: <AlertTriangle className="w-4 h-4" />,
      colors: "bg-amber-500 hover:bg-amber-600 text-white",
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
      sub: "Primary transparent score",
    },
    {
      name: "Claim Anomaly",
      value: ctx.scoreDetails?.anomaly_score,
      sub: "Case-level anomaly signal",
    },
    {
      name: "ML Suspicion",
      value: ctx.scoreDetails?.ml_predicted_probability,
      sub: "Weakly supervised probability",
    },
    {
      name: "Hybrid Composite",
      value: ctx.scoreDetails?.hybrid_composite_score,
      sub: ctx.scoreDetails?.hybrid_risk_label
        ? `Assistive layer · ${ctx.scoreDetails.hybrid_risk_label}`
        : "Assistive hybrid layer",
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
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
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
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                  {card.name}
                </p>
                <p
                  className={cn(
                    "text-3xl font-black leading-none",
                    scoreColor(
                      typeof card.value === "number" ? card.value : null,
                    ),
                  )}
                >
                  {typeof card.value === "number"
                    ? card.value.toFixed(1).replace(/\.0$/, "")
                    : "—"}
                </p>
                <p className="text-xs text-slate-500 mt-2 font-medium">
                  {card.sub}
                </p>
              </div>
            ))}
          </div>

          {/* Entity-specific details */}
          {renderDetails(ctx.data)}

          {/* Extra sections (e.g. Z-Score) */}
          {extraSections?.(ctx.data)}

          {/* Actions */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-4">Take Action</h3>
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
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
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
            <h3 className="font-bold text-slate-800 mb-4">Action History</h3>
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
