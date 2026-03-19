"use client";

import { useState } from "react";
import { Loader2, SendHorizonal, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ClaimSimulationRequest } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ExampleClaim extends ClaimSimulationRequest {
  label: string;
}

const EXAMPLES: ExampleClaim[] = [
  {
    label: "High-risk: excessive volume",
    npi: "1003000126",
    hcpcs_cd: "99213",
    submitted_charge: 450,
    num_services: 800,
    num_benes: 50,
  },
  {
    label: "Stable: normal billing",
    npi: "1003000126",
    hcpcs_cd: "99213",
    submitted_charge: 75,
    num_services: 30,
    num_benes: 25,
  },
];

interface SimulateFormProps {
  onResult: (result: unknown) => void;
  onError: (error: string) => void;
  onLoading: (loading: boolean) => void;
}

export function SimulateForm({
  onResult,
  onError,
  onLoading,
}: SimulateFormProps) {
  const [npi, setNpi] = useState("");
  const [hcpcsCd, setHcpcsCd] = useState("");
  const [submittedCharge, setSubmittedCharge] = useState("");
  const [numServices, setNumServices] = useState("");
  const [numBenes, setNumBenes] = useState("");
  const [loading, setLoading] = useState(false);

  function fillExample(ex: ExampleClaim) {
    setNpi(ex.npi);
    setHcpcsCd(ex.hcpcs_cd);
    setSubmittedCharge(String(ex.submitted_charge));
    setNumServices(String(ex.num_services));
    setNumBenes(String(ex.num_benes));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    onLoading(true);
    onError("");

    try {
      const body: ClaimSimulationRequest = {
        npi,
        hcpcs_cd: hcpcsCd,
        submitted_charge: Number(submittedCharge),
        num_services: Number(numServices),
        num_benes: Number(numBenes),
      };

      const res = await fetch(`${API_BASE}/api/claims/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `Scoring failed: ${res.status}`);
      }

      onResult(await res.json());
    } catch (e) {
      onError(e instanceof Error ? e.message : "Scoring failed");
    } finally {
      setLoading(false);
      onLoading(false);
    }
  }

  const isValid =
    npi.length > 0 &&
    hcpcsCd.length > 0 &&
    Number(submittedCharge) > 0 &&
    Number(numServices) > 0 &&
    Number(numBenes) > 0;

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">Submit a Claim</CardTitle>
        <p className="text-sm text-muted-foreground">
          Enter claim details to get a real-time risk assessment
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="npi" className="text-sm font-medium">
              Provider NPI
            </label>
            <Input
              id="npi"
              placeholder="e.g. 1003000126"
              value={npi}
              onChange={(e) => setNpi(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="hcpcs" className="text-sm font-medium">
              HCPCS Code
            </label>
            <Input
              id="hcpcs"
              placeholder="e.g. 99213"
              value={hcpcsCd}
              onChange={(e) => setHcpcsCd(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="charge" className="text-sm font-medium">
              Submitted Charge ($)
            </label>
            <Input
              id="charge"
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 150.00"
              value={submittedCharge}
              onChange={(e) => setSubmittedCharge(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <label htmlFor="services" className="text-sm font-medium">
                # Services
              </label>
              <Input
                id="services"
                type="number"
                min="1"
                step="1"
                placeholder="e.g. 50"
                value={numServices}
                onChange={(e) => setNumServices(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="benes" className="text-sm font-medium">
                # Beneficiaries
              </label>
              <Input
                id="benes"
                type="number"
                min="1"
                step="1"
                placeholder="e.g. 30"
                value={numBenes}
                onChange={(e) => setNumBenes(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <Button
              type="submit"
              disabled={loading || !isValid}
              className="flex-1"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Scoring...
                </>
              ) : (
                <>
                  <SendHorizonal className="h-4 w-4 mr-2" />
                  Score Claim
                </>
              )}
            </Button>
          </div>

          <div className="border-t pt-3 space-y-2">
            <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
              <FlaskConical className="h-3 w-3" />
              Try an example
            </p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <Button
                  key={ex.label}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="text-xs"
                  onClick={() => fillExample(ex)}
                >
                  {ex.label}
                </Button>
              ))}
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
