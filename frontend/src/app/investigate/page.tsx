"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Inbox,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CaseActions } from "@/components/case-actions";
import type { CaseAction, PendingCase } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SortKey = "seed_risk_score" | "seed_case_label" | "provider_last_org_name";
type SortDir = "asc" | "desc";

function riskBadge(label: string | null) {
  switch (label) {
    case "high_risk":
      return <Badge variant="destructive">High Risk</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200 border-amber-200">
          Review
        </Badge>
      );
    case "stable":
      return (
        <Badge variant="outline" className="text-green-700 border-green-200">
          Stable
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-muted-foreground">
          {label ?? "—"}
        </Badge>
      );
  }
}

function fmtCurrency(v: number | null) {
  if (v == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

const ACTION_BADGE_CLASS: Record<CaseAction, string> = {
  APPROVED: "text-green-700 border-green-200",
  ESCALATED: "bg-orange-100 text-orange-800 border-orange-200",
  FLAGGED: "bg-yellow-100 text-yellow-800 border-yellow-200",
  DENIED: "bg-red-100 text-red-800 border-red-200",
};

function SortIcon({
  col,
  sortKey,
  sortDir,
}: {
  col: SortKey;
  sortKey: SortKey;
  sortDir: SortDir;
}) {
  if (col !== sortKey)
    return <ArrowUpDown className="h-3 w-3 ml-1 opacity-40" />;
  return sortDir === "asc" ? (
    <ArrowUp className="h-3 w-3 ml-1" />
  ) : (
    <ArrowDown className="h-3 w-3 ml-1" />
  );
}

export default function InvestigatePage() {
  const router = useRouter();
  const [cases, setCases] = useState<PendingCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("seed_risk_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [actioned, setActioned] = useState<Record<string, CaseAction>>({});

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/cases/pending?limit=100`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data: PendingCase[] = await res.json();
      setCases(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load pending cases");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "seed_risk_score" ? "desc" : "asc");
    }
  }

  const sorted = [...cases].sort((a, b) => {
    let av: string | number | null;
    let bv: string | number | null;
    if (sortKey === "seed_risk_score") {
      av = a.seed_risk_score ?? Number.NEGATIVE_INFINITY;
      bv = b.seed_risk_score ?? Number.NEGATIVE_INFINITY;
    } else if (sortKey === "seed_case_label") {
      av = a.seed_case_label ?? "";
      bv = b.seed_case_label ?? "";
    } else {
      av = a.provider_last_org_name ?? "";
      bv = b.provider_last_org_name ?? "";
    }
    if (av < bv) return sortDir === "asc" ? -1 : 1;
    if (av > bv) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  const highRiskCount = cases.filter((c) => c.seed_case_label === "high_risk").length;
  const reviewCount = cases.filter((c) => c.seed_case_label === "review").length;

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Investigation Queue
        </h1>
        <p className="text-muted-foreground text-sm">
          High-risk cases pending analyst review
        </p>
      </div>

      {/* Stats bar */}
      {!error && (
        <div className="grid grid-cols-3 gap-3">
          <Card>
            <CardContent className="py-3 px-4">
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <>
                  <p className="text-2xl font-bold">{cases.length}</p>
                  <p className="text-xs text-muted-foreground">Total Pending</p>
                </>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-3 px-4">
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <>
                  <p className="text-2xl font-bold text-red-600">
                    {highRiskCount}
                  </p>
                  <p className="text-xs text-muted-foreground">High Risk</p>
                </>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-3 px-4">
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <>
                  <p className="text-2xl font-bold text-amber-600">
                    {reviewCount}
                  </p>
                  <p className="text-xs text-muted-foreground">Review</p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <AlertTriangle className="h-6 w-6 mx-auto mb-2 text-destructive" />
            <p>Unable to connect to API</p>
            <p className="text-xs mt-1">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {!error && (
        <Card>
          <CardContent className="p-0">
            <Table className="min-w-[900px]">
              <TableHeader>
                <TableRow>
                  <TableHead>NPI</TableHead>
                  <TableHead>
                    <button
                      type="button"
                      className="flex items-center hover:text-foreground"
                      onClick={() => handleSort("provider_last_org_name")}
                    >
                      Provider
                      <SortIcon
                        col="provider_last_org_name"
                        sortKey={sortKey}
                        sortDir={sortDir}
                      />
                    </button>
                  </TableHead>
                  <TableHead className="text-right">
                    <button
                      type="button"
                      className="flex items-center ml-auto hover:text-foreground"
                      onClick={() => handleSort("seed_risk_score")}
                    >
                      Risk Score
                      <SortIcon
                        col="seed_risk_score"
                        sortKey={sortKey}
                        sortDir={sortDir}
                      />
                    </button>
                  </TableHead>
                  <TableHead>
                    <button
                      type="button"
                      className="flex items-center hover:text-foreground"
                      onClick={() => handleSort("seed_case_label")}
                    >
                      Label
                      <SortIcon
                        col="seed_case_label"
                        sortKey={sortKey}
                        sortDir={sortDir}
                      />
                    </button>
                  </TableHead>
                  <TableHead>Top Signal</TableHead>
                  <TableHead className="text-right">Avg Charge</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 7 }).map((_, j) => (
                          <TableCell key={j}>
                            <Skeleton className="h-4 w-20" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  : sorted.map((c) => (
                      <TableRow
                        key={c.case_id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => router.push(`/providers/${c.npi}`)}
                      >
                        <TableCell
                          className="font-mono text-sm"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <span
                            className="hover:underline cursor-pointer text-accent"
                            onClick={() => router.push(`/providers/${c.npi}`)}
                          >
                            {c.npi}
                          </span>
                        </TableCell>
                        <TableCell className="max-w-[180px] truncate">
                          {c.provider_last_org_name ?? "—"}
                        </TableCell>
                        <TableCell className="text-right font-mono font-semibold">
                          {c.seed_risk_score ?? "—"}
                        </TableCell>
                        <TableCell>
                          {actioned[c.case_id] ? (
                            <Badge
                              variant="outline"
                              className={ACTION_BADGE_CLASS[actioned[c.case_id]]}
                            >
                              {actioned[c.case_id]}
                            </Badge>
                          ) : (
                            riskBadge(c.seed_case_label)
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[160px] truncate">
                          {c.hcpcs_desc ?? c.hcpcs_cd ?? "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          {fmtCurrency(c.avg_submitted_charge)}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <CaseActions
                            caseId={c.case_id}
                            compact
                            onActionComplete={(action) =>
                              setActioned((prev) => ({
                                ...prev,
                                [c.case_id]: action,
                              }))
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                {!loading && cases.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={7}
                      className="text-center py-12 text-muted-foreground"
                    >
                      <Inbox className="h-8 w-8 mx-auto mb-3 opacity-30" />
                      <p className="font-medium">No pending cases</p>
                      <p className="text-xs mt-1">
                        All high-risk cases have been reviewed
                      </p>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
