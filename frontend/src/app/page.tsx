import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Activity, AlertTriangle, Eye, ShieldCheck, Users } from "lucide-react";
import { api } from "@/lib/api";
import type { DashboardStats, ProviderSummary } from "@/types/api";
import Link from "next/link";

function riskBadge(band: ProviderSummary["risk_band"]) {
  switch (band) {
    case "high_risk":
      return <Badge variant="destructive">HIGH RISK</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-500/15 text-amber-700 border border-amber-500/20 font-extrabold">
          REVIEW
        </Badge>
      );
    default:
      return (
        <Badge className="bg-green-500/15 text-green-700 border border-green-500/20 font-extrabold">
          STABLE
        </Badge>
      );
  }
}

function formatCurrency(value: number | null) {
  if (value == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatNumber(value: number | null) {
  if (value == null) return "\u2014";
  return new Intl.NumberFormat("en-US").format(value);
}

export default async function DashboardPage() {
  let data: DashboardStats | null = null;
  let error: string | null = null;

  try {
    data = await api.dashboard();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load dashboard";
  }

  if (error || !data) {
    return (
      <div className="p-6 space-y-6">
        <PageHeader />
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-full neu-recessed mb-3">
              <Activity className="h-5 w-5 text-muted-foreground" />
            </div>
            <p className="font-semibold">Unable to connect to API</p>
            <p className="text-xs mt-1 font-mono">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { total_providers, total_cases, risk_distribution, top_providers } =
    data;

  return (
    <div className="p-6 space-y-6">
      <PageHeader />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Providers"
          value={formatNumber(total_providers)}
          subtitle="Medicare Part B providers"
          icon={<Users className="h-4 w-4 text-foreground" />}
        />
        <StatCard
          label="High Risk"
          value={formatNumber(risk_distribution.high_risk)}
          subtitle="Score above 51"
          icon={<AlertTriangle className="h-4 w-4 text-destructive" />}
          valueClass="text-destructive"
          led="red"
        />
        <StatCard
          label="Under Review"
          value={formatNumber(risk_distribution.review)}
          subtitle="Score 31–50"
          icon={<Eye className="h-4 w-4 text-amber-500" />}
          valueClass="text-amber-500"
          led="amber"
        />
        <StatCard
          label="Total Cases"
          value={formatNumber(total_cases)}
          subtitle="Service line cases analyzed"
          icon={<Activity className="h-4 w-4 text-foreground" />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full neu-float">
                <AlertTriangle className="h-3 w-3 text-destructive" />
              </div>
              Top 10 Highest-Risk Providers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table className="min-w-[600px]">
              <TableHeader>
                <TableRow>
                  <TableHead>Provider</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">Est. Payment</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top_providers.map((p) => (
                  <TableRow key={p.npi}>
                    <TableCell>
                      <Link
                        href={`/providers/${p.npi}`}
                        className="font-semibold text-foreground hover:text-accent transition-colors"
                      >
                        {p.provider_name ?? p.npi}
                      </Link>
                      <div className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider mt-0.5">
                        {p.provider_type}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono">
                      {p.state ?? "\u2014"}
                    </TableCell>
                    <TableCell className="text-right font-mono font-bold">
                      {p.max_seed_risk_score ?? "\u2014"}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatCurrency(p.total_estimated_payment)}
                    </TableCell>
                    <TableCell>{riskBadge(p.risk_band)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full neu-float">
                <ShieldCheck className="h-3 w-3 text-accent" />
              </div>
              Risk Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <RiskBar
              label="High Risk"
              count={risk_distribution.high_risk}
              total={total_providers}
              color="bg-red-500"
              icon={<AlertTriangle className="h-3.5 w-3.5 text-red-500" />}
              led="red"
            />
            <RiskBar
              label="Review"
              count={risk_distribution.review}
              total={total_providers}
              color="bg-amber-500"
              icon={<Eye className="h-3.5 w-3.5 text-amber-500" />}
              led="amber"
            />
            <RiskBar
              label="Stable"
              count={risk_distribution.stable}
              total={total_providers}
              color="bg-green-500"
              icon={<ShieldCheck className="h-3.5 w-3.5 text-green-500" />}
              led="green"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function PageHeader() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-10 w-10 items-center justify-center rounded-full neu-float">
        <Activity className="h-5 w-5 text-accent" />
      </div>
      <div>
        <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
        <span className="label-stamped text-[9px]">
          MEDICARE FRAUD DETECTION OVERVIEW
        </span>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  subtitle,
  icon,
  valueClass,
  led,
}: {
  label: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  valueClass?: string;
  led?: "red" | "amber" | "green";
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <span className="label-stamped text-[10px]">{label}</span>
        <div className="flex h-7 w-7 items-center justify-center rounded-full neu-float">
          {icon}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          {led && <div className={`led-${led}`} />}
          <div
            className={`text-2xl font-extrabold font-mono tracking-tight ${valueClass ?? ""}`}
          >
            {value}
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1 font-mono uppercase tracking-wider">
          {subtitle}
        </p>
      </CardContent>
    </Card>
  );
}

function RiskBar({
  label,
  count,
  total,
  color,
  icon,
  led,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
  icon: React.ReactNode;
  led: "red" | "amber" | "green";
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2 font-semibold">
          {icon}
          {label}
        </span>
        <span className="font-mono text-xs text-muted-foreground">
          {formatNumber(count)} ({pct.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2.5 rounded-full neu-recessed overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
