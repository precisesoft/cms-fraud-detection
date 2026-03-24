import { useNavigate } from "react-router-dom";
import type { ClusterMember } from "../lib/api";

const BAND_COLORS: Record<string, string> = {
  high_risk: "#e11d48",
  review: "#d97706",
  stable: "#059669",
};

interface FraudRingGraphProps {
  seed: string;
  members: ClusterMember[];
}

export function FraudRingGraph({ seed, members }: FraudRingGraphProps) {
  const navigate = useNavigate();

  if (!members.length) {
    return (
      <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        No fraud ring detected for this provider.
      </div>
    );
  }

  // Scale canvas to cluster size
  const n = members.length;
  const width = 500;
  const height = Math.max(280, Math.min(500, 140 + n * 70));
  const cx = width / 2;
  const cy = height / 2;

  const maxHop = Math.max(...members.map((m) => m.hops));
  const outerRadius = Math.min(cx, cy) - 60;

  const positions = new Map<string, { x: number; y: number }>();
  positions.set(seed, { x: cx, y: cy });

  for (let hop = 1; hop <= maxHop; hop++) {
    const ring = members.filter((m) => m.hops === hop);
    const radius = (outerRadius * hop) / maxHop;
    // Offset angle per ring to avoid overlap
    const baseAngle = hop % 2 === 0 ? Math.PI / ring.length : 0;
    ring.forEach((m, i) => {
      const angle =
        baseAngle + (2 * Math.PI * i) / Math.max(ring.length, 1) - Math.PI / 2;
      positions.set(m.npi, {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      });
    });
  }

  // Build edges
  const edges: { from: string; to: string; type: string }[] = [];
  for (const m of members) {
    if (m.hops === 1) {
      edges.push({ from: seed, to: m.npi, type: m.link_type });
    } else {
      const prev = members.find(
        (p) =>
          p.hops === m.hops - 1 &&
          ((m.link_type === "SAME_ZIP" && p.zip5 === m.zip5) ||
            (m.link_type === "SAME_ORG" &&
              p.provider_name === m.provider_name)),
      );
      edges.push({ from: prev?.npi ?? seed, to: m.npi, type: m.link_type });
    }
  }

  const nodeR = (score: number | null) => {
    if (!score) return 20;
    if (score >= 51) return 24;
    if (score >= 31) return 22;
    return 20;
  };

  const trimLabel = (name: string | null, npi: string) => {
    const raw = name ?? npi;
    return raw.length > 20 ? `${raw.slice(0, 18)}…` : raw;
  };

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* Edges */}
      {edges.map((e, i) => {
        const from = positions.get(e.from);
        const to = positions.get(e.to);
        if (!from || !to) return null;
        const mx = (from.x + to.x) / 2;
        const my = (from.y + to.y) / 2;
        return (
          <g key={`edge-${i}`}>
            <line
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={e.type === "SAME_ZIP" ? "#6366f1" : "#3b82f6"}
              strokeWidth={2}
              strokeOpacity={0.4}
              strokeDasharray={e.type === "SAME_ORG" ? "6 4" : "none"}
            />
            <rect
              x={mx - 20}
              y={my - 10}
              width={40}
              height={20}
              rx={6}
              fill="white"
              stroke="#e2e8f0"
            />
            <text
              x={mx}
              y={my + 4}
              textAnchor="middle"
              fontSize={11}
              fontWeight={700}
              fill="#64748b"
            >
              {e.type === "SAME_ZIP" ? "ZIP" : "ORG"}
            </text>
          </g>
        );
      })}

      {/* Seed node */}
      <g>
        <circle cx={cx} cy={cy} r={28} fill="#4f46e5" opacity={0.9} />
        <circle
          cx={cx}
          cy={cy}
          r={28}
          fill="none"
          stroke="#4f46e5"
          strokeWidth={4}
          strokeOpacity={0.25}
        />
        <text
          x={cx}
          y={cy + 5}
          textAnchor="middle"
          fontSize={12}
          fontWeight={700}
          fill="white"
        >
          SEED
        </text>
      </g>

      {/* Member nodes */}
      {members.map((m) => {
        const pos = positions.get(m.npi);
        if (!pos) return null;
        const r = nodeR(m.risk_score);
        const color = BAND_COLORS[m.risk_band ?? ""] ?? "#94a3b8";
        const label = trimLabel(m.provider_name, m.npi);
        return (
          <g
            key={m.npi}
            className="cursor-pointer"
            onClick={() => navigate(`/providers/${m.npi}`)}
          >
            <title>
              {m.provider_name ?? m.npi} — Risk: {m.risk_score ?? "?"} (
              {m.risk_band ?? "unknown"})
            </title>
            {/* Glow ring */}
            <circle
              cx={pos.x}
              cy={pos.y}
              r={r + 4}
              fill="none"
              stroke={color}
              strokeWidth={3}
              strokeOpacity={0.25}
            />
            <circle cx={pos.x} cy={pos.y} r={r} fill={color} opacity={0.9} />
            {/* Score inside node */}
            <text
              x={pos.x}
              y={pos.y + (m.revoked ? -2 : 5)}
              textAnchor="middle"
              fontSize={12}
              fontWeight={800}
              fill="white"
            >
              {m.risk_score ?? "?"}
            </text>
            {m.revoked && (
              <text
                x={pos.x}
                y={pos.y + 12}
                textAnchor="middle"
                fontSize={8}
                fontWeight={700}
                fill="white"
                opacity={0.8}
              >
                REVOKED
              </text>
            )}
            {/* Label below node */}
            <text
              x={pos.x}
              y={pos.y + r + 18}
              textAnchor="middle"
              fontSize={11}
              fontWeight={600}
              fill="#334155"
            >
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
