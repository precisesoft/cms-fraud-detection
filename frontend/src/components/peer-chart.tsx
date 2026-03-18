"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PeerLine } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ChartRow {
  code: string;
  provider: number;
  peer: number;
  zScore: number;
}

function buildChartData(lines: PeerLine[]): ChartRow[] {
  return lines.slice(0, 10).map((l) => ({
    code: l.hcpcs_cd,
    provider: l.tot_srvcs ?? 0,
    peer: l.peer_avg_tot_srvcs ?? 0,
    zScore: l.service_volume_peer_z ?? 0,
  }));
}

export function PeerChart({ npi }: { npi: string }) {
  const [data, setData] = useState<ChartRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/providers/${npi}/peers`);
        if (!res.ok) return;
        const json = await res.json();
        setData(buildChartData(json.lines));
      } catch {
        // silently fail — chart is supplementary
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [npi]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Peer Comparison</CardTitle>
        </CardHeader>
        <CardContent className="h-64 flex items-center justify-center text-sm text-muted-foreground">
          Loading chart...
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Peer Comparison — Service Volume (Top 10 Codes)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={data}
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="code"
              tick={{ fontSize: 11 }}
              className="fill-muted-foreground"
            />
            <YAxis tick={{ fontSize: 11 }} className="fill-muted-foreground" />
            <Tooltip
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid hsl(var(--border))",
                fontSize: "12px",
              }}
              formatter={(value, name) => [
                new Intl.NumberFormat("en-US").format(Number(value)),
                String(name) === "provider" ? "Provider" : "Peer Avg",
              ]}
            />
            <Legend
              formatter={(value: string) =>
                value === "provider" ? "Provider" : "Peer Average"
              }
            />
            <Bar dataKey="provider" name="provider" radius={[4, 4, 0, 0]}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={
                    entry.zScore > 2 ? "hsl(0 72% 51%)" : "hsl(221 83% 53%)"
                  }
                />
              ))}
            </Bar>
            <Bar
              dataKey="peer"
              name="peer"
              fill="hsl(215 16% 70%)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-xs text-muted-foreground mt-2">
          Red bars indicate z-score &gt; 2 (statistical outlier vs peers)
        </p>
      </CardContent>
    </Card>
  );
}
