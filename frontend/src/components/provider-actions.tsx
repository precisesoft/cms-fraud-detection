"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CaseActions, CaseStatusBadge } from "@/components/case-actions";
import type { CaseAction } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ProviderActionsProps {
  npi: string;
  caseIds: string[];
}

export function ProviderActions({ caseIds }: ProviderActionsProps) {
  const [actioned, setActioned] = useState<Record<string, CaseAction>>({});

  const fetchStatuses = useCallback(async () => {
    const statuses: Record<string, CaseAction> = {};
    await Promise.all(
      caseIds.slice(0, 10).map(async (caseId) => {
        try {
          const res = await fetch(`${API_BASE}/api/cases/${caseId}/actions`);
          if (!res.ok) return;
          const data = await res.json();
          if (data.current_status) {
            statuses[caseId] = data.current_status;
          }
        } catch {
          // ignore
        }
      }),
    );
    return statuses;
  }, [caseIds]);

  useEffect(() => {
    if (caseIds.length === 0) return;
    let cancelled = false;
    fetchStatuses().then((statuses) => {
      if (!cancelled) setActioned(statuses);
    });
    return () => {
      cancelled = true;
    };
  }, [caseIds, fetchStatuses]);

  if (caseIds.length === 0) return null;

  // Show action buttons for first unactioned case, or last case
  const targetCase = caseIds.find((id) => !actioned[id]) ?? caseIds[0];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Investigation Actions</CardTitle>
        <p className="text-xs text-muted-foreground">
          Take action on this provider&apos;s flagged cases
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-sm text-muted-foreground">
          Case: <span className="font-mono">{targetCase}</span>
          {actioned[targetCase] && (
            <span className="ml-2">
              <CaseStatusBadge status={actioned[targetCase]} />
            </span>
          )}
        </div>
        <CaseActions
          caseId={targetCase}
          currentStatus={actioned[targetCase] ?? null}
          onActionComplete={(action) =>
            setActioned((prev) => ({ ...prev, [targetCase]: action }))
          }
        />
        {Object.keys(actioned).length > 0 && (
          <p className="text-xs text-muted-foreground">
            {Object.keys(actioned).length} of {caseIds.length} cases actioned
          </p>
        )}
      </CardContent>
    </Card>
  );
}
