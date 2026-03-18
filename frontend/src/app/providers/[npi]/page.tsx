import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, MapPin, AlertTriangle, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api";
import type { ProviderDetail, Signal } from "@/types/api";

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
      <p className="text-lg font-semibold">{value}</p>
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

export default async function ProviderDetailPage({
  params,
}: {
  params: Promise<{ npi: string }>;
}) {
  const { npi } = await params;

  let provider: ProviderDetail | null = null;
  let signals: Signal[] = [];

  try {
    [provider, signals] = await Promise.all([
      api.provider(npi),
      api.signals(npi).catch(() => [] as Signal[]),
    ]);
  } catch {
    notFound();
  }

  if (!provider) notFound();

  const riskSignals = signals.filter((s) => s.direction === "risk");
  const legSignals = signals.filter((s) => s.direction === "legitimacy");

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <Link
        href="/providers"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to providers
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {provider.provider_name ?? "Unknown Provider"}
          </h1>
          <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
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
          <div className="text-right">
            <p className="text-xs text-muted-foreground">Risk Score</p>
            <p className="text-3xl font-bold font-mono">
              {provider.max_seed_risk_score ?? "\u2014"}
            </p>
          </div>
          {riskBadge(provider.risk_band, "lg")}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <StatItem
              label="Service Lines"
              value={fmt(provider.service_line_count)}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatItem
              label="Total Beneficiaries"
              value={fmt(provider.total_benes)}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatItem
              label="Est. Payment"
              value={fmtCurrency(provider.total_estimated_payment)}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatItem
              label="High Risk Lines"
              value={`${fmt(provider.n_high_risk_lines)} / ${fmt(provider.service_line_count)}`}
            />
          </CardContent>
        </Card>
      </div>

      {/* More detail stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Provider Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <div>
              <span className="text-muted-foreground">Unique HCPCS Codes</span>
              <p className="font-medium">{fmt(provider.unique_hcpcs_codes)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">
                Avg Submitted Charge
              </span>
              <p className="font-medium">
                {fmtCurrency(provider.mean_submitted_charge)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Avg Payment</span>
              <p className="font-medium">
                {fmtCurrency(provider.mean_payment_amt)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Service HHI</span>
              <p className="font-medium">{fmt(provider.service_hhi, 2)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">Top Code Share</span>
              <p className="font-medium">
                {provider.top_code_share != null
                  ? `${(provider.top_code_share * 100).toFixed(1)}%`
                  : "\u2014"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Enrolled 2025</span>
              <p className="font-medium">
                {provider.enrolled_2025 ? "Yes" : "No"}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Revoked 2026</span>
              <p className="font-medium">
                {provider.revoked_2026 ? (
                  <span className="text-destructive">
                    Yes
                    {provider.revocation_reason
                      ? ` (${provider.revocation_reason})`
                      : ""}
                  </span>
                ) : (
                  "No"
                )}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Avg Risk Score</span>
              <p className="font-medium">
                {fmt(provider.avg_seed_risk_score, 1)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Signals */}
      {signals.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500" />
                Risk Signals ({riskSignals.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {riskSignals.length > 0 ? (
                riskSignals.map((s) => <SignalCard key={s.name} signal={s} />)
              ) : (
                <p className="text-sm text-muted-foreground">No risk signals</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-green-500" />
                Legitimacy Signals ({legSignals.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {legSignals.length > 0 ? (
                legSignals.map((s) => <SignalCard key={s.name} signal={s} />)
              ) : (
                <p className="text-sm text-muted-foreground">
                  No legitimacy signals
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
