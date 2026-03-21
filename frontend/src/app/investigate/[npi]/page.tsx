import { notFound } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  MapPin,
  AlertTriangle,
  ShieldCheck,
  Search,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import { EvidenceGraph } from "@/components/evidence-graph";
import { PeerChart } from "@/components/peer-chart";
import { ProviderActions } from "@/components/provider-actions";
import { RiskGauge } from "@/components/risk-gauge";
import { GenerateBrief } from "@/components/generate-brief";
import { CaseTimeline } from "@/components/case-timeline";
import { RiskRadar } from "@/components/risk-radar";
import type { ProviderDetail, Signal } from "@/types/api";

const MAX_CLAIMS_FOR_CASES = 20;

function riskBadge(
  band: ProviderDetail["risk_band"],
  size: "sm" | "lg" = "sm",
) {
  const cls = size === "lg" ? "text-sm px-3 py-1" : "";
  switch (band) {
    case "high_risk":
      return (
        <Badge variant="destructive" className={cls}>
          High Risk
        </Badge>
      );
    case "review":
      return (
        <Badge
          className={`bg-amber-100 text-amber-800 border-amber-200 ${cls}`}
        >
          Review
        </Badge>
      );
    default:
      return (
        <Badge
          variant="outline"
          className={`text-green-700 border-green-200 ${cls}`}
        >
          Stable
        </Badge>
      );
  }
}

function fmt(v: number | null | undefined, decimals = 0) {
  if (v == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: decimals,
  }).format(v);
}

function fmtCurrency(v: number | null | undefined) {
  if (v == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-base font-semibold">{value}</p>
    </div>
  );
}

function SignalCard({ signal }: { signal: Signal }) {
  const isRisk = signal.direction === "risk";
  return (
    <div
      className={`rounded-lg border p-3 ${
        isRisk ? "border-red-200 bg-red-50" : "border-green-200 bg-green-50"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p
            className={`text-sm font-medium ${isRisk ? "text-red-800" : "text-green-800"}`}
          >
            {signal.name}
          </p>
          <p
            className={`text-xs mt-0.5 ${isRisk ? "text-red-600" : "text-green-600"}`}
          >
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
    </div>
  );
}

export default async function InvestigatePage({
  params,
}: {
  params: Promise<{ npi: string }>;
}) {
  const { npi } = await params;

  let provider: ProviderDetail | null = null;
  let signals: Signal[] = [];
  let caseIds: string[] = [];

  try {
    [provider, signals] = await Promise.all([
      api.provider(npi),
      api.signals(npi).catch(() => [] as Signal[]),
    ]);
    const claims = await api
      .claims({ npi, per_page: MAX_CLAIMS_FOR_CASES })
      .catch(() => null);
    caseIds = claims?.data.map((c) => c.case_id) ?? [];
  } catch {
    notFound();
  }

  if (!provider) notFound();

  const riskSignals = signals.filter((s) => s.direction === "risk");
  const legSignals = signals.filter((s) => s.direction === "legitimacy");

  return (
    <div className="p-6 space-y-6 max-w-screen-xl">
      {/* Breadcrumb */}
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <Link
          href="/providers"
          className="inline-flex items-center gap-1 hover:text-foreground"
        >
          <Search className="h-3 w-3" />
          Providers
        </Link>
        <span>/</span>
        <Link
          href={`/providers/${npi}`}
          className="inline-flex items-center gap-1 hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          {provider.provider_name ?? npi}
        </Link>
        <span>/</span>
        <span className="text-foreground font-medium">Investigation</span>
      </div>

      {/* Page header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Investigation View
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-1 text-sm text-muted-foreground">
            <span className="font-bold text-foreground">
              {provider.provider_name ?? "Unknown Provider"}
            </span>
            <Separator orientation="vertical" className="h-4" />
            <span className="font-mono">{provider.npi}</span>
            <Separator orientation="vertical" className="h-4" />
            <span>{provider.provider_type}</span>
            {provider.city && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {provider.city}, {provider.state}
                </span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <RiskGauge score={provider.max_seed_risk_score} size={100} />
          {riskBadge(provider.risk_band, "lg")}
        </div>
      </div>

      {/* Two-column investigation layout */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Left column ─────────────────────────────────────────── */}
        <div className="space-y-6">
          {/* Risk summary stats */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Risk Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
                <StatItem
                  label="Max Risk Score"
                  value={fmt(provider.max_seed_risk_score, 1)}
                />
                <StatItem
                  label="Avg Risk Score"
                  value={fmt(provider.avg_seed_risk_score, 1)}
                />
                <StatItem
                  label="High Risk Lines"
                  value={`${fmt(provider.n_high_risk_lines)} / ${fmt(provider.service_line_count)}`}
                />
                <StatItem
                  label="Service Lines"
                  value={fmt(provider.service_line_count)}
                />
                <StatItem
                  label="Total Beneficiaries"
                  value={fmt(provider.total_benes)}
                />
                <StatItem
                  label="Est. Payment"
                  value={fmtCurrency(provider.total_estimated_payment)}
                />
                <StatItem
                  label="Enrolled 2025"
                  value={provider.enrolled_2025 ? "Yes" : "No"}
                />
                <StatItem
                  label="Revoked 2026"
                  value={
                    provider.revoked_2026
                      ? `Yes${provider.revocation_reason ? ` — ${provider.revocation_reason}` : ""}`
                      : "No"
                  }
                />
              </div>
            </CardContent>
          </Card>

          {/* Risk signals */}
          {riskSignals.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-red-500" />
                  Risk Signals ({riskSignals.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {riskSignals.map((s) => (
                  <SignalCard key={s.name} signal={s} />
                ))}
              </CardContent>
            </Card>
          )}

          {/* Legitimacy signals */}
          {legSignals.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-green-500" />
                  Legitimacy Signals ({legSignals.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {legSignals.map((s) => (
                  <SignalCard key={s.name} signal={s} />
                ))}
              </CardContent>
            </Card>
          )}

          {/* Peer comparison */}
          <PeerChart npi={npi} />

          {/* Investigation actions */}
          <ProviderActions npi={npi} caseIds={caseIds} />
        </div>

        {/* ── Right column ─────────────────────────────────────────── */}
        <div className="space-y-6">
          {/* Generate Brief + Export Evidence */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                AI Investigation Brief
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Generate a fresh risk assessment with AI narrative, or export
                all evidence as a JSON package.
              </p>
            </CardHeader>
            <CardContent>
              <GenerateBrief
                npi={npi}
                provider={provider}
                seedSignals={signals}
              />
            </CardContent>
          </Card>

          {/* Risk radar — spider chart of risk dimensions */}
          <RiskRadar npi={npi} />

          {/* Evidence graph */}
          <EvidenceGraph npi={npi} />
        </div>
      </div>

      {/* Case action history timeline — full width at bottom */}
      <CaseTimeline caseIds={caseIds} />
    </div>
  );
}
