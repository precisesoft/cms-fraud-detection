"use client";

import Link from "next/link";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CaseActions } from "@/components/case-actions";
import { RiskGauge } from "@/components/risk-gauge";
import { RiskBadge, SignalRow } from "@/components/signal-row";
import type {
  ClaimSimulationResult,
  PeerComparisonStats,
  Recommendation,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Verdict banner config
// ---------------------------------------------------------------------------

const VERDICT_CONFIG: Record<
  Recommendation,
  {
    label: string;
    className: string;
    icon: typeof CheckCircle2;
    description: string;
  }
> = {
  approve: {
    label: "APPROVE",
    className: "bg-green-50 border-green-200 text-green-800",
    icon: CheckCircle2,
    description:
      "This claim falls within normal billing patterns for this provider and procedure.",
  },
  review: {
    label: "REVIEW",
    className: "bg-amber-50 border-amber-200 text-amber-800",
    icon: AlertTriangle,
    description:
      "Some indicators warrant further review before processing this claim.",
  },
  deny: {
    label: "DENY",
    className: "bg-red-50 border-red-200 text-red-800",
    icon: XCircle,
    description:
      "Multiple risk signals suggest this claim should be denied and escalated.",
  },
};

// ---------------------------------------------------------------------------
// Peer comparison bar
// ---------------------------------------------------------------------------

function PeerBar({ stat }: { stat: PeerComparisonStats }) {
  const maxVal = Math.max(stat.provider_value, stat.peer_mean) || 1;
  const providerPct = (stat.provider_value / maxVal) * 100;
  const peerPct = (stat.peer_mean / maxVal) * 100;
  const isOutlier = stat.z_score >= 2;
  const ratio =
    stat.peer_mean > 0
      ? (stat.provider_value / stat.peer_mean).toFixed(1)
      : "N/A";

  return (
    <div className="space-y-1.5 py-2 border-b last:border-0">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium capitalize">
          {stat.metric.replace(/_/g, " ")}
        </span>
        <span
          className={`text-xs font-mono ${isOutlier ? "text-red-600 font-semibold" : "text-muted-foreground"}`}
        >
          {ratio}x peers
          {isOutlier && " ⚠"}
        </span>
      </div>
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-12 shrink-0">
            Yours
          </span>
          <div className="flex-1 bg-muted rounded-full h-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                isOutlier ? "bg-red-500" : "bg-blue-500"
              }`}
              style={{ width: `${providerPct}%` }}
            />
          </div>
          <span className="text-xs font-mono w-16 text-right">
            {stat.provider_value.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground w-12 shrink-0">
            Peers
          </span>
          <div className="flex-1 bg-muted rounded-full h-3 overflow-hidden">
            <div
              className="h-full rounded-full bg-gray-400"
              style={{ width: `${peerPct}%` }}
            />
          </div>
          <span className="text-xs font-mono w-16 text-right text-muted-foreground">
            {stat.peer_mean.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function SimulateResult({ result }: { result: ClaimSimulationResult }) {
  const verdict = VERDICT_CONFIG[result.recommendation];
  const VerdictIcon = verdict.icon;
  const riskSignals = result.signals.filter((s) => s.direction === "risk");
  const legitSignals = result.signals.filter(
    (s) => s.direction === "legitimacy",
  );

  return (
    <div className="space-y-4">
      {/* Verdict banner — big, bold, unmissable */}
      <div
        className={`rounded-lg border-2 p-6 text-center ${verdict.className}`}
      >
        <VerdictIcon className="h-10 w-10 mx-auto mb-2" />
        <p className="text-3xl font-black tracking-wide">{verdict.label}</p>
        <p className="text-sm mt-1 opacity-80">{verdict.description}</p>
      </div>

      {/* Risk gauge + provider context */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Risk Assessment</CardTitle>
            <RiskBadge band={result.risk_band} />
          </div>
          {result.provider_name && (
            <p className="text-sm text-muted-foreground">
              {result.provider_name}
              {result.provider_type && ` \u00b7 ${result.provider_type}`}
              {result.state && ` \u00b7 ${result.state}`}
            </p>
          )}
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center">
            <RiskGauge score={result.risk_score} size={140} />
          </div>
        </CardContent>
      </Card>

      {/* Peer comparison bars */}
      {result.peer_comparisons.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Peer Comparison</CardTitle>
            <p className="text-xs text-muted-foreground">
              {result.peer_comparisons[0]?.peer_count ?? 0} peers with same
              specialty + procedure
            </p>
          </CardHeader>
          <CardContent>
            {result.peer_comparisons.map((p) => (
              <PeerBar key={p.metric} stat={p} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Signals */}
      {result.signals.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              Signals ({result.signals.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {riskSignals.map((s) => (
              <SignalRow key={`${s.name}-risk`} signal={s} />
            ))}
            {legitSignals.map((s) => (
              <SignalRow key={`${s.name}-legit`} signal={s} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Narrative */}
      {result.narrative && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">AI Narrative</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{result.narrative}</p>
          </CardContent>
        </Card>
      )}

      {/* Action buttons */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Analyst Decision</CardTitle>
        </CardHeader>
        <CardContent>
          <CaseActions caseId={`${result.npi}_${result.hcpcs_cd}`} />
          <div className="mt-4 pt-3 border-t">
            <Link
              href={`/providers/${result.npi}`}
              className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              View full provider investigation
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
