"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Claim, PaginationMeta } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    case "legitimate":
      return (
        <Badge variant="outline" className="text-green-700 border-green-200">
          Legitimate
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-muted-foreground">
          {label ?? "\u2014"}
        </Badge>
      );
  }
}

function fmtCurrency(v: number | null) {
  if (v == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(v);
}

export default function ClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchClaims = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", "25");

      const res = await fetch(`${API_BASE}/api/claims?${params}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setClaims(json.data);
      setMeta(json.meta);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load claims");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Claims</h1>
        <p className="text-muted-foreground text-sm">
          Service line cases sorted by risk score
        </p>
      </div>

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <p>Unable to connect to API</p>
            <p className="text-xs mt-1">{error}</p>
          </CardContent>
        </Card>
      )}

      {!error && (
        <Card>
          <CardContent className="p-0">
            <Table className="min-w-[900px]">
              <TableHeader>
                <TableRow>
                  <TableHead>NPI</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>HCPCS</TableHead>
                  <TableHead className="text-right">Risk Score</TableHead>
                  <TableHead>Label</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead className="text-right">Services</TableHead>
                  <TableHead className="text-right">Avg Charge</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 8 }).map((_, j) => (
                          <TableCell key={j}>
                            <Skeleton className="h-4 w-20" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  : claims.map((c) => (
                      <TableRow key={c.case_id}>
                        <TableCell className="font-mono text-sm">
                          <Link
                            href={`/providers/${c.npi}`}
                            className="hover:underline"
                          >
                            {c.npi}
                          </Link>
                        </TableCell>
                        <TableCell className="max-w-[200px] truncate">
                          {c.provider_last_org_name ?? "\u2014"}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm">
                            {c.hcpcs_cd}
                          </span>
                          {c.hcpcs_desc && (
                            <div className="text-xs text-muted-foreground truncate max-w-[180px]">
                              {c.hcpcs_desc}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {c.seed_risk_score ?? "\u2014"}
                        </TableCell>
                        <TableCell>{riskBadge(c.seed_case_label)}</TableCell>
                        <TableCell>{c.provider_state ?? "\u2014"}</TableCell>
                        <TableCell className="text-right">
                          {c.tot_srvcs != null
                            ? new Intl.NumberFormat("en-US").format(c.tot_srvcs)
                            : "\u2014"}
                        </TableCell>
                        <TableCell className="text-right">
                          {fmtCurrency(c.avg_submitted_charge)}
                        </TableCell>
                      </TableRow>
                    ))}
                {!loading && claims.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={8}
                      className="text-center py-8 text-muted-foreground"
                    >
                      No claims found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {meta && meta.pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {claims.length} of{" "}
            {new Intl.NumberFormat("en-US").format(meta.total)} cases
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <span className="flex items-center text-sm text-muted-foreground px-2">
              {page} / {meta.pages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= meta.pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
