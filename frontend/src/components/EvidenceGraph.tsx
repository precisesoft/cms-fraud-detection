import type { GraphNode, GraphEdge } from '../lib/api';

const TYPE_COLORS: Record<string, string> = {
  provider: '#6366f1',
  hcpcs: '#f59e0b',
  signal: '#f43f5e',
  location: '#22c55e',
  organization: '#3b82f6',
};

export function EvidenceGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  if (!nodes.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        No graph data available.
      </div>
    );
  }

  const width = 500;
  const height = 300;
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) / 2 - 40;

  const positions = nodes.map((_, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });

  const nodeMap = new Map(nodes.map((n, i) => [n.id, i]));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {edges.map((edge, i) => {
        const si = nodeMap.get(edge.source);
        const ti = nodeMap.get(edge.target);
        if (si === undefined || ti === undefined) return null;
        return (
          <line
            key={i}
            x1={positions[si].x}
            y1={positions[si].y}
            x2={positions[ti].x}
            y2={positions[ti].y}
            stroke="#cbd5e1"
            strokeWidth={1.5}
          />
        );
      })}
      {nodes.map((node, i) => (
        <g key={node.id}>
          <circle
            cx={positions[i].x}
            cy={positions[i].y}
            r={12}
            fill={TYPE_COLORS[node.type] ?? '#94a3b8'}
            opacity={0.85}
          />
          <text
            x={positions[i].x}
            y={positions[i].y + 22}
            textAnchor="middle"
            fontSize={9}
            fontWeight={600}
            fill="#475569"
          >
            {node.label.length > 18 ? node.label.slice(0, 16) + '…' : node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
