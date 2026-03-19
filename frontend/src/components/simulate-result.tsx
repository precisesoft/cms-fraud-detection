"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RiskGauge } from "@/components/risk-gauge";
import type {
  ClaimSimulationResult,
  PeerComparisonStats,
  Signal,
  Recommendation,
} from "@/types/api";

function recommendationBadge(rec: Recommendation) {
  switch (rec) {
    case "deny":
      return <Badge variant="destructive">Deny</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 border-amber-200">
          Review
        </Badge>
      );
    default:
      return (
        <Badge className="bg-green-100 text-green-800 border-green-200">
          Approve
        </Badge>
      );
  }
}

function riskBadge(band: string) {
  switch (band) {
    case "high_risk":
      return <Badge variant="destructive">High Risk</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 border-amber-200">
          Review
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-green-700 border-green-200">
          Stable
        </Badge>
      );
  }
}

function SignalRow({ signal }: { signal: Signal }) {
  const isRisk = signal.direction === "risk";
  return (
    <div
      className={`flex items-start justify-between gap-2 rounded-md px-3 py-2 text-sm ${
        isRisk ? "bg-red-50" : "bg-green-50"
      }`}
    >
      <div>
        <span
          className={`font-medium ${isRisk ? "text-red-800" : "text-green-800"}`}
        >
          {signal.name}
        </span>
        <p className={`text-xs ${isRisk ? "text-red-600" : "text-green-600"}`}>
          {signal.description}
        </p>
      </div>
      {signal.value != null && (
        <span
          className={`text-xs font-mono shrink-0 ${isRisk ? "text-red-700" : "text-green-700"}`}
        >
          {signal.value.toFixed(1)}
        </span>
      )}
    </div>
  );
}

function PeerRow({ stat }: { stat: PeerComparisonStats }) {
  const isOutlier = Math.abs(stat.z_score) >= 2;
  const isHigh = stat.z_score >= 2;
  return (
    <div className="grid grid-cols-4 gap-2 text-sm py-1.5 border-b last:border-0">
      <span className="font-medium text-muted-foreground">
        {stat.metric.replace(/_/g, " ")}
      </span>
      <span className="font-mono text-right">
        {stat.provider_value.toLocaleString()}
      </span>
      <span className="font-mono text-right text-muted-foreground">
        {stat.peer_mean.toLocaleString()}
      </span>
      <span
        className={`font-mono text-right ${
          isOutlier
            ? isHigh
              ? "text-red-600 font-semibold"
              : "text-blue-600"
            : "text-green-600"
        }`}
      >
        {stat.z_score > 0 ? "+" : ""}
        {stat.z_score.toFixed(1)}z
      </span>
    </div>
  );
}

export function SimulateResult({ result }: { result: ClaimSimulationResult }) {
  const riskSignals = result.signals.filter((s) => s.direction === "risk");
  const legitSignals = result.signals.filter(
    (s) => s.direction === "legitimacy",
  );

  return (
    <div className="space-y-4">
      {/* Header card with recommendation */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Scoring Result</CardTitle>
            <div className="flex items-center gap-2">
              {riskBadge(result.risk_band)}
              {recommendationBadge(result.recommendation)}
            </div>
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

      {/* Peer comparisons */}
      {result.peer_comparisons.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Peer Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground font-medium pb-1 border-b">
              <span>Metric</span>
              <span className="text-right">Yours</span>
              <span className="text-right">Peer Avg</span>
              <span className="text-right">Z-Score</span>
            </div>
            {result.peer_comparisons.map((p) => (
              <PeerRow key={p.metric} stat={p} />
            ))}
            <p className="text-xs text-muted-foreground mt-2">
              Peers: {result.peer_comparisons[0]?.peer_count ?? 0} providers
              with same specialty + procedure
            </p>
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
    </div>
  );
}
