"use client";

import { useEffect, useState } from "react";

const ZONES = [
  { max: 30, color: "hsl(142 71% 45%)", label: "Stable" },
  { max: 50, color: "hsl(45 93% 47%)", label: "Review" },
  { max: 100, color: "hsl(0 72% 51%)", label: "High Risk" },
] as const;

function scoreColor(score: number) {
  for (const z of ZONES) {
    if (score <= z.max) return z.color;
  }
  return ZONES[ZONES.length - 1].color;
}

export function RiskGauge({
  score,
  size = 120,
}: {
  score: number | null | undefined;
  size?: number;
}) {
  const [animated, setAnimated] = useState(0);

  useEffect(() => {
    const target = score ?? 0;
    const timer = setTimeout(() => setAnimated(target), 50);
    return () => clearTimeout(timer);
  }, [score]);

  if (score == null) {
    return (
      <div
        className="flex items-center justify-center rounded-full border-4 border-muted"
        style={{ width: size, height: size }}
      >
        <span className="text-muted-foreground text-sm">N/A</span>
      </div>
    );
  }

  const pct = Math.min(Math.max(animated, 0), 100);
  const angle = (pct / 100) * 360;
  const color = scoreColor(pct);

  return (
    <div
      className="relative flex items-center justify-center rounded-full"
      style={{
        width: size,
        height: size,
        background: `conic-gradient(${color} ${angle}deg, hsl(var(--muted)) ${angle}deg)`,
        transition: "background 0.8s ease-out",
      }}
    >
      <div
        className="absolute rounded-full bg-background flex flex-col items-center justify-center"
        style={{ width: size - 16, height: size - 16 }}
      >
        <span className="text-2xl font-bold font-mono leading-none">
          {score}
        </span>
        <span className="text-[10px] text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}
