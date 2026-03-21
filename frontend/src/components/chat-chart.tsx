"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { ChartSpec } from "@/types/api";

const COLORS = [
  "hsl(221, 83%, 53%)",
  "hsl(262, 83%, 58%)",
  "hsl(332, 78%, 51%)",
  "hsl(173, 58%, 39%)",
  "hsl(43, 96%, 56%)",
  "hsl(200, 95%, 45%)",
  "hsl(142, 71%, 45%)",
  "hsl(25, 95%, 53%)",
];

function formatLabel(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bNpi\b/, "NPI")
    .replace(/\bHcpcs\b/, "HCPCS")
    .replace(/\bAmt\b/, "Amount")
    .replace(/\bAvg\b/, "Avg.");
}

function formatTick(val: unknown): string {
  if (typeof val === "number") {
    if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
    if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(0)}K`;
    if (Number.isInteger(val)) return val.toString();
    return val.toFixed(1);
  }
  const s = String(val ?? "");
  return s.length > 12 ? s.slice(0, 11) + "\u2026" : s;
}

export function ChatChart({ spec }: { spec: ChartSpec }) {
  const { type, title, data } = spec;

  if (!data?.length) return null;

  return (
    <div className="my-2 rounded-lg border bg-card p-3">
      <p className="text-xs font-medium text-muted-foreground mb-2">{title}</p>
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart
              data={data}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey={spec.xKey}
                tick={{ fontSize: 10 }}
                tickFormatter={formatTick}
                interval={0}
                angle={data.length > 5 ? -35 : 0}
                textAnchor={data.length > 5 ? "end" : "middle"}
                height={data.length > 5 ? 60 : 30}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={formatTick}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid hsl(var(--border))",
                }}
                labelFormatter={(v) =>
                  formatLabel(spec.xKey ?? "") + ": " + String(v)
                }
              />
              <Bar
                dataKey={spec.yKey!}
                fill={COLORS[0]}
                radius={[4, 4, 0, 0]}
                name={formatLabel(spec.yKey ?? "")}
              />
            </BarChart>
          ) : type === "line" ? (
            <LineChart
              data={data}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis
                dataKey={spec.xKey}
                tick={{ fontSize: 10 }}
                tickFormatter={formatTick}
              />
              <YAxis
                tick={{ fontSize: 10 }}
                tickFormatter={formatTick}
                width={50}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid hsl(var(--border))",
                }}
              />
              <Line
                type="monotone"
                dataKey={spec.yKey!}
                stroke={COLORS[0]}
                strokeWidth={2}
                dot={{ r: 3, fill: COLORS[0] }}
                name={formatLabel(spec.yKey ?? "")}
              />
            </LineChart>
          ) : (
            <PieChart>
              <Pie
                data={data}
                dataKey={spec.valueKey!}
                nameKey={spec.nameKey!}
                cx="50%"
                cy="50%"
                outerRadius={75}
                label={({ name, percent }) =>
                  `${formatTick(name)} ${(Number(percent) * 100).toFixed(0)}%`
                }
                labelLine={{ strokeWidth: 1 }}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid hsl(var(--border))",
                }}
              />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
