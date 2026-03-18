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
      return <Badge variant="destructive">High Risk</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200 border-amber-200">
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
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground text-sm">
            Medicare provider fraud detection overview
          </p>
        </div>
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <p>Unable to connect to API</p>
            <p className="text-xs mt-1">{error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { total_providers, total_cases, risk_distribution, top_providers } =
    data;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          Medicare provider fraud detection overview
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              Total Providers
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(total_providers)}
            </div>
            <p className="text-xs text-muted-foreground">
              Medicare Part B providers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">High Risk</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {formatNumber(risk_distribution.high_risk)}
            </div>
            <p className="text-xs text-muted-foreground">Score above 51</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Under Review</CardTitle>
            <Eye className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-500">
              {formatNumber(risk_distribution.review)}
            </div>
            <p className="text-xs text-muted-foreground">
              Score 31{"\u2013"}50
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Cases</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(total_cases)}
            </div>
            <p className="text-xs text-muted-foreground">
              Service line cases analyzed
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              Top 10 Highest-Risk Providers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
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
                        className="font-medium hover:underline"
                      >
                        {p.provider_name ?? p.npi}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {p.provider_type}
                      </div>
                    </TableCell>
                    <TableCell>{p.state ?? "\u2014"}</TableCell>
                    <TableCell className="text-right font-mono">
                      {p.max_seed_risk_score ?? "\u2014"}
                    </TableCell>
                    <TableCell className="text-right">
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
            <CardTitle className="text-base">Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <RiskBar
              label="High Risk"
              count={risk_distribution.high_risk}
              total={total_providers}
              color="bg-red-500"
              icon={<AlertTriangle className="h-4 w-4 text-red-500" />}
            />
            <RiskBar
              label="Review"
              count={risk_distribution.review}
              total={total_providers}
              color="bg-amber-500"
              icon={<Eye className="h-4 w-4 text-amber-500" />}
            />
            <RiskBar
              label="Stable"
              count={risk_distribution.stable}
              total={total_providers}
              color="bg-green-500"
              icon={<ShieldCheck className="h-4 w-4 text-green-500" />}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function RiskBar({
  label,
  count,
  total,
  color,
  icon,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
  icon: React.ReactNode;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5">
          {icon}
          {label}
        </span>
        <span className="font-mono text-muted-foreground">
          {formatNumber(count)} ({pct.toFixed(1)}%)
        </span>
      </div>
      <div className="h-2 rounded-full bg-muted">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
