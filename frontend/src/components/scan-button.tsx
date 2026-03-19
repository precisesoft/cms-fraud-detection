"use client";

import { useState } from "react";
import { ScanLine, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskGauge } from "@/components/risk-gauge";
import { RiskBadge, SignalRow } from "@/components/signal-row";
import type { ScoreResult } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function ScanButton({ npi }: { npi: string }) {
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleScan() {
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
      setError(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Button onClick={handleScan} disabled={loading} variant="default">
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Scanning...
          </>
        ) : (
          <>
            <ScanLine className="h-4 w-4 mr-2" />
            Scan Provider
          </>
        )}
      </Button>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {result && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center justify-between">
              <span>Scan Result</span>
              <RiskBadge band={result.risk_band} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-6">
              <RiskGauge score={result.risk_score} size={90} />
              <div>
                <p className="text-xs text-muted-foreground">
                  Legitimacy Score
                </p>
                <p className="text-2xl font-bold font-mono text-green-600">
                  {result.legitimacy_score}
                </p>
              </div>
            </div>

            {result.narrative && (
              <div className="rounded-md bg-muted p-3 text-sm">
                {result.narrative}
              </div>
            )}

            {result.signals.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground font-medium">
                  Signals ({result.signals.length})
                </p>
                {result.signals.map((s) => (
                  <SignalRow key={`${s.name}-${s.direction}`} signal={s} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
