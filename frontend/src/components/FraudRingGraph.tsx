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

  const width = 720;
  const height = 400;
  const cx = width / 2;
  const cy = height / 2;

  // Layout: seed at center, members in concentric rings by hop distance
  const maxHop = Math.max(...members.map((m) => m.hops));
  const ringSpacing = Math.min(width, height) / 2 / (maxHop + 1) - 20;

  const positions = new Map<string, { x: number; y: number }>();
  positions.set(seed, { x: cx, y: cy });

  for (let hop = 1; hop <= maxHop; hop++) {
    const ring = members.filter((m) => m.hops === hop);
    const radius = ringSpacing * hop + 40;
    ring.forEach((m, i) => {
      const angle = (2 * Math.PI * i) / Math.max(ring.length, 1) - Math.PI / 2;
      positions.set(m.npi, {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
      });
    });
  }

  // Build edges: each member links to seed (hop=1) or to any member in hop-1 sharing zip/org
  const edges: { from: string; to: string; type: string }[] = [];
  for (const m of members) {
    if (m.hops === 1) {
      edges.push({ from: seed, to: m.npi, type: m.link_type });
    } else {
      // Connect to first member in previous hop with shared zip or org
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

  const nodeRadius = (score: number | null) => {
    if (!score) return 14;
    if (score >= 51) return 18;
    if (score >= 31) return 16;
    return 14;
  };

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto min-h-[300px]"
    >
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
              strokeWidth={1.5}
              strokeOpacity={0.5}
              strokeDasharray={e.type === "SAME_ORG" ? "4 3" : "none"}
            />
            <rect
              x={mx - 16}
              y={my - 7}
              width={32}
              height={14}
              rx={4}
              fill="white"
              fillOpacity={0.9}
              stroke="#e2e8f0"
            />
            <text
              x={mx}
              y={my + 3}
              textAnchor="middle"
              fontSize={8}
              fontWeight={600}
              fill="#64748b"
            >
              {e.type === "SAME_ZIP" ? "ZIP" : "ORG"}
            </text>
          </g>
        );
      })}

      {/* Seed node */}
      <g className="cursor-pointer">
        <circle cx={cx} cy={cy} r={22} fill="#4f46e5" opacity={0.9} />
        <circle
          cx={cx}
          cy={cy}
          r={22}
          fill="none"
          stroke="#4f46e5"
          strokeWidth={3}
          strokeOpacity={0.3}
        />
        <text
          x={cx}
          y={cy + 4}
          textAnchor="middle"
          fontSize={9}
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
        const r = nodeRadius(m.risk_score);
        const color = BAND_COLORS[m.risk_band ?? ""] ?? "#94a3b8";
        const label = m.provider_name
          ? m.provider_name.length > 14
            ? `${m.provider_name.slice(0, 12)}…`
            : m.provider_name
          : m.npi;
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
            <circle cx={pos.x} cy={pos.y} r={r} fill={color} opacity={0.85} />
            {m.revoked && (
              <text
                x={pos.x}
                y={pos.y + 4}
                textAnchor="middle"
                fontSize={10}
                fontWeight={700}
                fill="white"
              >
                !
              </text>
            )}
            <rect
              x={pos.x - 46}
              y={pos.y + r + 4}
              width={92}
              height={16}
              rx={6}
              fill="white"
              fillOpacity={0.92}
              stroke="#e2e8f0"
            />
            <text
              x={pos.x}
              y={pos.y + r + 15}
              textAnchor="middle"
              fontSize={8}
              fontWeight={600}
              fill="#475569"
            >
              {label}
            </text>
            <text
              x={pos.x}
              y={pos.y + r + 30}
              textAnchor="middle"
              fontSize={8}
              fill="#94a3b8"
            >
              {m.risk_score ?? "?"}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
