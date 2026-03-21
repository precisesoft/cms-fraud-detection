"use client";

import { useCallback, useEffect, useState } from "react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { RadarDimension } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface RiskRadarProps {
  npi: string;
}

export function RiskRadar({ npi }: RiskRadarProps) {
  const [data, setData] = useState<RadarDimension[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRadar = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/providers/${npi}/radar`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setData(json.dimensions);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load radar data");
    } finally {
      setLoading(false);
    }
  }, [npi]);

  useEffect(() => {
    fetchRadar();
  }, [fetchRadar]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Risk Profile</CardTitle>
        <p className="text-xs text-muted-foreground">
          Provider (red) vs peer baseline (blue). Axes extending outward
          indicate anomalous dimensions.
        </p>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-[300px] w-full" />
        ) : error ? (
          <p className="text-sm text-destructive py-8 text-center">{error}</p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
              <PolarGrid stroke="#e2e8f0" />
              <PolarAngleAxis
                dataKey="dimension"
                tick={{ fontSize: 11, fill: "#64748b" }}
              />
              <Radar
                name="Peer Baseline"
                dataKey="peer"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.1}
                strokeWidth={1.5}
                strokeDasharray="4 4"
              />
              <Radar
                name="Provider"
                dataKey="provider"
                stroke="#ef4444"
                fill="#ef4444"
                fillOpacity={0.2}
                strokeWidth={2}
              />
              <Tooltip
                formatter={(value: number, name: string) => [
                  value.toFixed(0),
                  name,
                ]}
                contentStyle={{
                  fontSize: "12px",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                }}
              />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
