"use client";

import { useState } from "react";
import { FileText, Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskGauge } from "@/components/risk-gauge";
import { RiskBadge, SignalRow } from "@/components/signal-row";
import type { ProviderDetail, ScoreResult, Signal } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface GenerateBriefProps {
  npi: string;
  provider: ProviderDetail;
  seedSignals: Signal[];
}

export function GenerateBrief({ npi, provider, seedSignals }: GenerateBriefProps) {
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ npi }),
      });
      if (!res.ok) throw new Error(`Scoring failed: ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Brief generation failed");
    } finally {
      setLoading(false);
    }
  }

  function handleExport() {
    const pkg = {
      exported_at: new Date().toISOString(),
      provider: {
        npi: provider.npi,
        name: provider.provider_name,
        type: provider.provider_type,
        city: provider.city,
        state: provider.state,
        enrolled_2025: provider.enrolled_2025,
        revoked_2026: provider.revoked_2026,
        revocation_reason: provider.revocation_reason,
        risk_band: provider.risk_band,
        max_seed_risk_score: provider.max_seed_risk_score,
        avg_seed_risk_score: provider.avg_seed_risk_score,
        n_high_risk_lines: provider.n_high_risk_lines,
        service_line_count: provider.service_line_count,
        total_benes: provider.total_benes,
        total_estimated_payment: provider.total_estimated_payment,
      },
      seed_signals: seedSignals,
      generated_brief: result
        ? {
            risk_score: result.risk_score,
            legitimacy_score: result.legitimacy_score,
            risk_band: result.risk_band,
            anomaly_score: result.anomaly_score,
            narrative: result.narrative,
            signals: result.signals,
          }
        : null,
    };
    const blob = new Blob([JSON.stringify(pkg, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `evidence-${npi}-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const riskSignals = result?.signals.filter((s) => s.direction === "risk") ?? [];
  const legSignals = result?.signals.filter((s) => s.direction === "legitimacy") ?? [];

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <Button onClick={handleGenerate} disabled={loading}>
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <FileText className="h-4 w-4 mr-2" />
              Generate Brief
            </>
          )}
        </Button>
        <Button variant="outline" onClick={handleExport}>
          <Download className="h-4 w-4 mr-2" />
          Export Evidence
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* Brief result */}
      {result && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center justify-between">
              <span>Investigation Brief</span>
              <RiskBadge band={result.risk_band} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Score summary */}
            <div className="flex items-center gap-6">
              <RiskGauge score={result.risk_score} size={90} />
              <div className="space-y-1">
                <div>
                  <p className="text-xs text-muted-foreground">Risk Score</p>
                  <p className="text-2xl font-bold font-mono">
                    {result.risk_score}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">
                    Legitimacy Score
                  </p>
                  <p className="text-lg font-semibold font-mono text-green-600">
                    {result.legitimacy_score}
                  </p>
                </div>
                {result.anomaly_score != null && (
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Anomaly Score
                    </p>
                    <p className="text-lg font-semibold font-mono text-amber-600">
                      {result.anomaly_score.toFixed(3)}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* AI Narrative */}
            {result.narrative && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">
                  AI Narrative
                </p>
                <div className="rounded-md border bg-muted/40 p-4 text-sm leading-relaxed whitespace-pre-wrap">
                  {result.narrative}
                </div>
              </div>
            )}

            {/* Signals from brief */}
            {result.signals.length > 0 && (
              <div className="grid gap-3 sm:grid-cols-2">
                {riskSignals.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">
                      Risk Signals ({riskSignals.length})
                    </p>
                    <div className="space-y-1.5">
                      {riskSignals.map((s) => (
                        <SignalRow key={`${s.name}-${s.direction}`} signal={s} />
                      ))}
                    </div>
                  </div>
                )}
                {legSignals.length > 0 && (
                  <div>
                    <p className="text-xs font-medium text-muted-foreground mb-1.5">
                      Legitimacy Signals ({legSignals.length})
                    </p>
                    <div className="space-y-1.5">
                      {legSignals.map((s) => (
                        <SignalRow key={`${s.name}-${s.direction}`} signal={s} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
