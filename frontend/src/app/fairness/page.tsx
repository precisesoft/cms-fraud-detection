"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { FairnessReport, CohortFairness } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function ParityBadge({
  label,
  value,
  pass,
}: {
  label: string;
  value: string;
  pass: boolean;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm">{value}</span>
        <Badge
          variant={pass ? "outline" : "destructive"}
          className={pass ? "text-green-700 border-green-200" : ""}
        >
          {pass ? "Pass" : "Fail"}
        </Badge>
      </div>
    </div>
  );
}

function CohortChart({
  title,
  data,
  overallRate,
}: {
  title: string;
  data: CohortFairness[];
  overallRate: number;
}) {
  const sorted = [...data]
    .sort((a, b) => b.flagging_rate - a.flagging_rate)
    .slice(0, 15);

  const chartData = sorted.map((c) => ({
    name: c.cohort,
    rate: +(c.flagging_rate * 100).toFixed(2),
    isOutlier: c.is_outlier,
    count: c.provider_count,
    flagged: c.flagged_count,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 20, left: 0, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10 }}
              angle={-45}
              textAnchor="end"
              className="fill-muted-foreground"
            />
            <YAxis
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                fontSize: "12px",
              }}
              formatter={(value, name) => [
                `${Number(value).toFixed(2)}%`,
                String(name) === "rate" ? "Flagging Rate" : String(name),
              ]}
              labelFormatter={(label) => {
                const item = chartData.find((d) => d.name === label);
                return item
                  ? `${label} (${item.count} providers, ${item.flagged} flagged)`
                  : String(label);
              }}
            />
            <ReferenceLine
              y={overallRate * 100}
              stroke="hsl(215 16% 47%)"
              strokeDasharray="5 5"
              label={{
                value: `Avg ${(overallRate * 100).toFixed(1)}%`,
                position: "right",
                fontSize: 10,
                fill: "hsl(215 16% 47%)",
              }}
            />
            <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.isOutlier ? "hsl(0 72% 51%)" : "hsl(221 83% 53%)"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-1">
          Red bars indicate outlier cohorts (&gt;2 sigma above mean flagging
          rate)
        </p>
      </CardContent>
    </Card>
  );
}

export default function FairnessPage() {
  const [report, setReport] = useState<FairnessReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/fairness`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        setReport(await res.json());
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Failed to load fairness data",
        );
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Fairness</h1>
        <p className="text-muted-foreground text-sm">
          Algorithmic fairness analysis across geography and specialty
        </p>
      </div>

      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-80 w-full" />
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <p>Unable to connect to API</p>
            <p className="text-xs mt-1">{error}</p>
          </CardContent>
        </Card>
      )}

      {report && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="pt-4 space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">
                    Overall Flagging Rate
                  </p>
                  <p className="text-2xl font-bold">
                    {(report.overall_flagging_rate * 100).toFixed(2)}%
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <ParityBadge
                  label="Statistical Parity Diff"
                  value={
                    report.statistical_parity_diff != null
                      ? (report.statistical_parity_diff * 100).toFixed(2) + "%"
                      : "\u2014"
                  }
                  pass={
                    report.statistical_parity_diff != null &&
                    report.statistical_parity_diff < 0.1
                  }
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Max minus min flagging rate across cohorts. Below 10% is
                  generally acceptable.
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <ParityBadge
                  label="Disparate Impact Ratio"
                  value={
                    report.disparate_impact_ratio != null
                      ? report.disparate_impact_ratio.toFixed(3)
                      : "\u2014"
                  }
                  pass={
                    report.disparate_impact_ratio != null &&
                    report.disparate_impact_ratio >= 0.8
                  }
                />
                <p className="text-xs text-muted-foreground mt-2">
                  Min / max flagging rate. Above 0.8 passes the four-fifths
                  rule.
                </p>
              </CardContent>
            </Card>
          </div>

          <CohortChart
            title="Flagging Rate by Specialty (Top 15)"
            data={report.by_specialty}
            overallRate={report.overall_flagging_rate}
          />

          <CohortChart
            title="Flagging Rate by State"
            data={report.by_state}
            overallRate={report.overall_flagging_rate}
          />
        </>
      )}
    </div>
  );
}
