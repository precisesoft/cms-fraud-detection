"use client";

import { useEffect, useState } from "react";
import { Clock, CheckCircle, Flag, XCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { CaseAction, CaseActionRecord } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const MAX_TIMELINE_CASES = 20;

const ACTION_STYLES: Record<
  CaseAction,
  { icon: typeof CheckCircle; color: string; badge: string }
> = {
  APPROVED: {
    icon: CheckCircle,
    color: "text-green-600",
    badge: "bg-green-100 text-green-800 border-green-200",
  },
  FLAGGED: {
    icon: Flag,
    color: "text-yellow-600",
    badge: "bg-yellow-100 text-yellow-800 border-yellow-200",
  },
  DENIED: {
    icon: XCircle,
    color: "text-red-600",
    badge: "bg-red-100 text-red-800 border-red-200",
  },
  ESCALATED: {
    icon: AlertTriangle,
    color: "text-orange-600",
    badge: "bg-orange-100 text-orange-800 border-orange-200",
  },
};

interface TimelineEntry extends CaseActionRecord {
  case_id: string;
}

interface CaseTimelineProps {
  caseIds: string[];
}

export function CaseTimeline({ caseIds }: CaseTimelineProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(caseIds.length > 0);

  useEffect(() => {
    if (caseIds.length === 0) return;

    let cancelled = false;

    (async () => {
      const results: TimelineEntry[] = [];
      await Promise.all(
        caseIds.slice(0, MAX_TIMELINE_CASES).map(async (caseId) => {
          try {
            const res = await fetch(`${API_BASE}/api/cases/${caseId}/actions`);
            if (!res.ok) return;
            const data = await res.json();
            for (const action of data.actions ?? []) {
              results.push({ ...action, case_id: caseId });
            }
          } catch {
            // silently skip failed case fetches
          }
        }),
      );

      if (cancelled) return;

      results.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
      setEntries(results);
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [caseIds]);

  if (caseIds.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          Case Action History
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            Loading action history...
          </p>
        ) : entries.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            No actions recorded for this provider&apos;s cases
          </p>
        ) : (
          <ol className="relative border-l border-border ml-3 space-y-4">
            {entries.map((entry) => {
              const cfg = ACTION_STYLES[entry.action];
              const Icon = cfg.icon;
              return (
                <li key={entry.id} className="ml-6">
                  <span className="absolute -left-3 flex h-6 w-6 items-center justify-center rounded-full border bg-background">
                    <Icon className={`h-3 w-3 ${cfg.color}`} />
                  </span>
                  <div className="flex flex-wrap items-center gap-2 mb-0.5">
                    <Badge variant="outline" className={cfg.badge}>
                      {entry.action}
                    </Badge>
                    <span className="text-xs font-mono text-muted-foreground">
                      {entry.case_id}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      by {entry.analyst_id}
                    </span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      {new Date(entry.created_at).toLocaleString()}
                    </span>
                  </div>
                  {entry.notes && (
                    <p className="text-sm text-muted-foreground mt-0.5">
                      {entry.notes}
                    </p>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
