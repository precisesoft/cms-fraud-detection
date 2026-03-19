"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import type { GraphResponse } from "@/types/api";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const NODE_COLORS: Record<string, string> = {
  Provider: "hsl(221 83% 53%)",
  Case: "hsl(45 93% 47%)",
  Signal: "hsl(0 72% 51%)",
  Source: "hsl(142 71% 45%)",
};

interface SelectedNode {
  id: string;
  type: string;
  label: string;
  properties: Record<string, unknown>;
}

export function EvidenceGraph({ npi }: { npi: string }) {
  const [data, setData] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SelectedNode | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/graph/${npi}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        setData(await res.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load graph");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [npi]);

  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      const { width } = entries[0].contentRect;
      setDimensions({ width, height: 400 });
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const handleNodeClick = useCallback(
    (node: { id: string; [key: string]: unknown }) => {
      const original = data?.nodes.find((n) => n.id === node.id);
      if (original) {
        setSelected({
          id: original.id,
          type: original.type,
          label: original.label,
          properties: original.properties,
        });
      }
    },
    [data],
  );

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence Graph</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Evidence Graph</CardTitle>
        </CardHeader>
        <CardContent className="py-10 text-center text-muted-foreground">
          {error ? (
            <p className="text-sm">{error}</p>
          ) : (
            <p className="text-sm">No graph data available for this provider</p>
          )}
        </CardContent>
      </Card>
    );
  }

  const graphData = {
    nodes: data.nodes.map((n) => ({
      id: n.id,
      label: n.label,
      type: n.type,
    })),
    links: data.edges.map((e) => ({
      source: e.source,
      target: e.target,
      label: e.type,
    })),
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Evidence Graph</CardTitle>
          <div className="flex gap-2">
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1 text-xs">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {type}
              </div>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          ref={containerRef}
          className="rounded-lg border bg-muted/30 overflow-hidden"
        >
          <ForceGraph2D
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            nodeLabel={(node) => String(node.label ?? node.id)}
            nodeColor={(node) =>
              NODE_COLORS[String(node.type)] ?? "hsl(215 16% 47%)"
            }
            nodeVal={6}
            linkColor={() => "hsl(215 16% 70%)"}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkLabel={(link) => String(link.label ?? "")}
            onNodeClick={handleNodeClick}
            cooldownTicks={80}
            backgroundColor="transparent"
          />
        </div>

        {selected && (
          <div className="mt-3 rounded-md border p-3 text-sm space-y-1">
            <div className="flex items-center gap-2">
              <Badge
                style={{
                  backgroundColor:
                    NODE_COLORS[selected.type] ?? "hsl(215 16% 47%)",
                  color: "white",
                }}
              >
                {selected.type}
              </Badge>
              <span className="font-medium">{selected.label}</span>
            </div>
            {Object.keys(selected.properties).length > 0 && (
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-xs">
                {Object.entries(selected.properties).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-muted-foreground">{k}:</span>{" "}
                    <span className="font-mono">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
