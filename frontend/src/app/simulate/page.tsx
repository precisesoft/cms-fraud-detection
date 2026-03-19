"use client";

import { useState } from "react";
import { SimulateForm } from "@/components/simulate-form";
import { SimulateResult } from "@/components/simulate-result";
import type { ClaimSimulationResult } from "@/types/api";

export default function SimulatePage() {
  const [result, setResult] = useState<ClaimSimulationResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Claim Simulation</h1>
        <p className="text-muted-foreground">
          Submit a claim for real-time risk scoring against peer baselines
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <SimulateForm
            onResult={(r) => setResult(r as ClaimSimulationResult)}
            onError={setError}
            onLoading={setLoading}
          />
        </div>

        <div>
          {error && (
            <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3 text-sm">
              {error}
            </div>
          )}

          {loading && !result && (
            <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
              Scoring claim against peer baselines...
            </div>
          )}

          {result && <SimulateResult result={result} />}

          {!result && !loading && !error && (
            <div className="flex items-center justify-center h-64 border border-dashed rounded-lg text-muted-foreground text-sm">
              Submit a claim to see the risk assessment
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
