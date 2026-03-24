import type { GraphNode, GraphEdge } from "../lib/api";

const TYPE_COLORS: Record<string, string> = {
  provider: "#6366f1",
  case: "#f59e0b",
  signal: "#f43f5e",
  peergroup: "#22c55e",
  source: "#3b82f6",
};

export function EvidenceGraph({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  if (!nodes.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        No graph data available.
      </div>
    );
  }

  const width = 720;
  const height = 360;
  const cx = width / 2;
  const cy = height / 2;

  const providerIndex = Math.max(
    nodes.findIndex((node) => node.type.toLowerCase() === "provider"),
    0,
  );
  const providerNode = nodes[providerIndex];
  const outerNodes = nodes.filter((_, index) => index !== providerIndex);
  const outerRadius = Math.min(width, height) / 2 - 64;

  const positions = new Map<string, { x: number; y: number }>();
  positions.set(providerNode.id, { x: cx, y: cy });

  outerNodes.forEach((node, index) => {
    const angle =
      (2 * Math.PI * index) / Math.max(outerNodes.length, 1) - Math.PI / 2;
    positions.set(node.id, {
      x: cx + outerRadius * Math.cos(angle),
      y: cy + outerRadius * Math.sin(angle),
    });
  });

  const wrapLabel = (label: string) => {
    const words = label.split(/\s+/);
    const lines: string[] = [];
    let current = "";

    for (const word of words) {
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length <= 16) {
        current = candidate;
      } else {
        if (current) {
          lines.push(current);
        }
        current = word;
      }
    }

    if (current) {
      lines.push(current);
    }

    if (!lines.length) {
      return [label.length > 16 ? `${label.slice(0, 14)}…` : label];
    }

    return lines.slice(0, 2).map((line, index, array) => {
      if (index === array.length - 1 && line.length > 16) {
        return `${line.slice(0, 14)}…`;
      }
      return line;
    });
  };

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto min-h-[320px]"
    >
      {edges.map((edge, i) => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) return null;
        return (
          <line
            key={i}
            x1={source.x}
            y1={source.y}
            x2={target.x}
            y2={target.y}
            stroke="#cbd5e1"
            strokeOpacity={0.85}
            strokeWidth={1.5}
          />
        );
      })}
      {nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) {
          return null;
        }

        const labelLines = wrapLabel(node.label);
        const isProvider = node.id === providerNode.id;

        return (
          <g key={node.id}>
            <title>{node.label}</title>
            <circle
              cx={position.x}
              cy={position.y}
              r={isProvider ? 16 : 12}
              fill={TYPE_COLORS[node.type.toLowerCase()] ?? "#94a3b8"}
              opacity={0.9}
            />
            <rect
              x={position.x - 46}
              y={position.y + (isProvider ? 22 : 20)}
              width={92}
              height={labelLines.length > 1 ? 26 : 16}
              rx={6}
              fill="white"
              fillOpacity={0.92}
              stroke="#e2e8f0"
            />
            {labelLines.map((line, index) => (
              <text
                key={`${node.id}-${index}`}
                x={position.x}
                y={position.y + (isProvider ? 33 : 31) + index * 10}
                textAnchor="middle"
                fontSize={9}
                fontWeight={600}
                fill="#475569"
              >
                {line}
              </text>
            ))}
          </g>
        );
      })}
    </svg>
  );
}
