"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ProviderSummary, PaginationMeta } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function riskBadge(band: ProviderSummary["risk_band"]) {
  switch (band) {
    case "high_risk":
      return <Badge variant="destructive">High Risk</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200 border-amber-200">
          Review
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-green-700 border-green-200">
          Stable
        </Badge>
      );
  }
}

function formatCurrency(value: number | null) {
  if (value == null) return "\u2014";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function ProvidersPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const stateFilter = searchParams.get("state") ?? "";

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Reset to page 1 when state filter changes
  useEffect(() => {
    setPage(1);
  }, [stateFilter]);

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", "20");
      if (debouncedQuery) params.set("q", debouncedQuery);
      if (stateFilter) params.set("state", stateFilter);

      const res = await fetch(`${API_BASE}/api/providers?${params}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const json = await res.json();
      setProviders(json.data);
      setMeta(json.meta);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load providers");
    } finally {
      setLoading(false);
    }
  }, [page, debouncedQuery, stateFilter]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  function clearStateFilter() {
    router.push("/providers");
  }

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Providers</h1>
        <p className="text-muted-foreground text-sm">
          Search and explore Medicare providers
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by NPI or provider name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        {stateFilter && (
          <Badge
            variant="secondary"
            className="flex items-center gap-1 px-3 py-1.5 text-sm"
          >
            Filtered: {stateFilter}
            <button
              onClick={clearStateFilter}
              aria-label="Clear state filter"
              className="ml-1 hover:text-destructive"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        )}
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
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Provider</TableHead>
                  <TableHead>NPI</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">Est. Payment</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        {Array.from({ length: 6 }).map((_, j) => (
                          <TableCell key={j}>
                            <Skeleton className="h-4 w-24" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  : providers.map((p) => (
                      <TableRow key={p.npi}>
                        <TableCell>
                          <Link
                            href={`/providers/${p.npi}`}
                            className="font-medium hover:underline"
                          >
                            {p.provider_name ?? "Unknown"}
                          </Link>
                          <div className="text-xs text-muted-foreground">
                            {p.provider_type}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {p.npi}
                        </TableCell>
                        <TableCell>
                          {[p.city, p.state].filter(Boolean).join(", ") ||
                            "\u2014"}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {p.max_seed_risk_score ?? "\u2014"}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(p.total_estimated_payment)}
                        </TableCell>
                        <TableCell>{riskBadge(p.risk_band)}</TableCell>
                      </TableRow>
                    ))}
                {!loading && providers.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="text-center py-8 text-muted-foreground"
                    >
                      No providers found
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
            Showing {providers.length} of{" "}
            {new Intl.NumberFormat("en-US").format(meta.total)} providers
            {debouncedQuery && (
              <>
                {" "}
                matching <span className="font-medium">{debouncedQuery}</span>
              </>
            )}
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

export default function ProvidersPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 space-y-4">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
          <Skeleton className="h-10 w-full max-w-md" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <ProvidersPageInner />
    </Suspense>
  );
}
