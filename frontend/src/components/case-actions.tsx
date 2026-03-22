"use client";

import { useState } from "react";
import {
  CheckCircle,
  Flag,
  XCircle,
  AlertTriangle,
  Loader2,
  MoreHorizontal,
} from "lucide-react";
import { Menu } from "@base-ui/react/menu";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { CaseAction } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ACTION_CONFIG: Record<
  CaseAction,
  {
    label: string;
    icon: typeof CheckCircle;
    variant: "default" | "outline" | "destructive" | "secondary";
    color: string;
  }
> = {
  APPROVED: {
    label: "Approve",
    icon: CheckCircle,
    variant: "outline",
    color: "text-green-600",
  },
  FLAGGED: {
    label: "Flag",
    icon: Flag,
    variant: "outline",
    color: "text-yellow-600",
  },
  DENIED: {
    label: "Deny",
    icon: XCircle,
    variant: "destructive",
    color: "text-red-600",
  },
  ESCALATED: {
    label: "Escalate",
    icon: AlertTriangle,
    variant: "outline",
    color: "text-orange-600",
  },
};

interface CaseActionsProps {
  caseId: string;
  currentStatus?: CaseAction | null;
  onActionComplete?: (action: CaseAction) => void;
  compact?: boolean;
}

export function CaseActions({
  caseId,
  currentStatus,
  onActionComplete,
  compact = false,
}: CaseActionsProps) {
  const [loading, setLoading] = useState<CaseAction | null>(null);
  const [notes, setNotes] = useState("");
  const [showNotes, setShowNotes] = useState(false);
  const [pendingAction, setPendingAction] = useState<CaseAction | null>(null);
  const [status, setStatus] = useState<CaseAction | null>(
    currentStatus ?? null,
  );

  async function submitAction(action: CaseAction) {
    setLoading(action);
    try {
      const res = await fetch(`${API_BASE}/api/cases/${caseId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes: notes || undefined }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail ?? `Failed: ${res.status}`);
      }
      setStatus(action);
      setShowNotes(false);
      setNotes("");
      setPendingAction(null);
      onActionComplete?.(action);
    } catch {
      // silently fail for demo
    } finally {
      setLoading(null);
    }
  }

  function handleClick(action: CaseAction) {
    if (action === "FLAGGED" || action === "ESCALATED") {
      setPendingAction(action);
      setShowNotes(true);
    } else {
      submitAction(action);
    }
  }

  const actionButtons = (Object.entries(ACTION_CONFIG) as [
    CaseAction,
    (typeof ACTION_CONFIG)[CaseAction],
  ][]).map(([action, config]) => {
    const Icon = config.icon;
    const isActive = status === action;
    return (
      <Button
        key={action}
        variant={isActive ? "default" : config.variant}
        size={compact ? "xs" : "sm"}
        disabled={loading !== null}
        onClick={() => handleClick(action)}
        className={isActive ? "" : config.color}
      >
        {loading === action ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Icon className="h-3 w-3" />
        )}
        {!compact && config.label}
      </Button>
    );
  });

  return (
    <div className="space-y-2">
      {status && <CaseStatusBadge status={status} />}

      {compact ? (
        <>
          {/* Mobile: overflow "…" menu — hidden on sm+ */}
          <div className="sm:hidden">
            <Menu.Root>
              <Menu.Trigger
                aria-label="Case actions"
                disabled={loading !== null}
                className={cn(
                  "flex h-11 w-11 items-center justify-center rounded-lg border border-border/50 bg-card text-foreground",
                  "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50",
                  "disabled:pointer-events-none disabled:opacity-50",
                )}
              >
                <MoreHorizontal className="h-4 w-4" />
              </Menu.Trigger>
              <Menu.Portal>
                <Menu.Positioner sideOffset={4} align="end">
                  <Menu.Popup className="z-50 min-w-[160px] rounded-lg border border-border/50 bg-card py-1 shadow-md">
                    {(
                      Object.entries(ACTION_CONFIG) as [
                        CaseAction,
                        (typeof ACTION_CONFIG)[CaseAction],
                      ][]
                    ).map(([action, config]) => {
                      const Icon = config.icon;
                      const isActive = status === action;
                      return (
                        <Menu.Item
                          key={action}
                          disabled={loading !== null}
                          onClick={() => handleClick(action)}
                          className={cn(
                            "flex min-h-[44px] w-full cursor-default items-center gap-2 px-3 py-2 text-sm font-medium outline-none hover:bg-muted focus-visible:bg-muted",
                            isActive ? "text-foreground" : config.color,
                          )}
                        >
                          {loading === action ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Icon className="h-4 w-4" />
                          )}
                          {config.label}
                        </Menu.Item>
                      );
                    })}
                  </Menu.Popup>
                </Menu.Positioner>
              </Menu.Portal>
            </Menu.Root>
          </div>

          {/* Desktop: inline icon buttons — hidden below sm */}
          <div className="hidden sm:flex sm:flex-wrap sm:gap-1">
            {actionButtons}
          </div>
        </>
      ) : (
        <div className="flex flex-wrap gap-2">{actionButtons}</div>
      )}

      {showNotes && pendingAction && (
        <div className="flex gap-2">
          <Input
            placeholder="Add notes (optional)..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="flex-1 text-sm"
            onKeyDown={(e) => {
              if (e.key === "Enter") submitAction(pendingAction);
            }}
          />
          <Button size="sm" onClick={() => submitAction(pendingAction)}>
            Submit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setShowNotes(false);
              setPendingAction(null);
            }}
          >
            Cancel
          </Button>
        </div>
      )}
    </div>
  );
}

export function CaseStatusBadge({ status }: { status: CaseAction | null }) {
  if (!status) return null;

  const styles: Record<CaseAction, string> = {
    APPROVED: "bg-green-100 text-green-800 border-green-200",
    FLAGGED: "bg-yellow-100 text-yellow-800 border-yellow-200",
    DENIED: "bg-red-100 text-red-800 border-red-200",
    ESCALATED: "bg-orange-100 text-orange-800 border-orange-200",
  };

  return (
    <Badge variant="outline" className={styles[status]}>
      {status}
    </Badge>
  );
}
