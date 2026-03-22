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
import { cn } from "@/lib/utils";
import type { ProviderSummary, PaginationMeta } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const US_STATES = [
  "AK","AL","AR","AZ","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL",
  "IN","KS","KY","LA","MA","MD","ME","MI","MN","MO","MS","MT","NC","ND","NE",
  "NH","NJ","NM","NV","NY","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
  "VA","VT","WA","WI","WV","WY",
];

const PROVIDER_TYPES = [
  "Internal Medicine",
  "Family Practice",
  "Cardiology",
  "Orthopedic Surgery",
  "Ophthalmology",
  "Dermatology",
  "Psychiatry",
  "Neurology",
  "Gastroenterology",
  "General Surgery",
  "Urology",
  "Pulmonary Disease",
  "Nephrology",
  "Hematology/Oncology",
  "Anesthesiology",
];

const RISK_BAND_OPTIONS = [
  { value: "high_risk", label: "High Risk" },
  { value: "review", label: "Review" },
  { value: "stable", label: "Stable" },
];

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
  className,
  "aria-label": ariaLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  options: { value: string; label: string }[];
  className?: string;
  "aria-label"?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={ariaLabel ?? placeholder}
      className={cn(
        "h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm",
        "focus:outline-none focus:ring-1 focus:ring-ring",
        "text-foreground disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

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
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize from URL params
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [debouncedQuery, setDebouncedQuery] = useState(searchParams.get("q") ?? "");
  const [stateFilter, setStateFilter] = useState(searchParams.get("state") ?? "");
  const [riskBandFilter, setRiskBandFilter] = useState(searchParams.get("risk_band") ?? "");
  const [providerTypeFilter, setProviderTypeFilter] = useState(
    searchParams.get("provider_type") ?? "",
  );
  const [page, setPage] = useState(Number(searchParams.get("page") ?? "1"));

  const [providers, setProviders] = useState<ProviderSummary[]>([]);
  const [meta, setMeta] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const hasActiveFilters =
    !!debouncedQuery || !!stateFilter || !!riskBandFilter || !!providerTypeFilter;

  // Sync URL when filter/page state changes
  useEffect(() => {
    const params = new URLSearchParams();
    if (debouncedQuery) params.set("q", debouncedQuery);
    if (stateFilter) params.set("state", stateFilter);
    if (riskBandFilter) params.set("risk_band", riskBandFilter);
    if (providerTypeFilter) params.set("provider_type", providerTypeFilter);
    if (page > 1) params.set("page", String(page));
    const qs = params.toString();
    router.replace(qs ? `/providers?${qs}` : "/providers", { scroll: false });
  }, [debouncedQuery, stateFilter, riskBandFilter, providerTypeFilter, page, router]);

  // Debounce text search; reset page on new query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Reset page when dropdown filters change
  const makeFilterHandler =
    (setFilter: (v: string) => void) => (v: string) => {
      setFilter(v);
      setPage(1);
    };
  const handleStateChange = makeFilterHandler(setStateFilter);
  const handleRiskBandChange = makeFilterHandler(setRiskBandFilter);
  const handleProviderTypeChange = makeFilterHandler(setProviderTypeFilter);

  const clearAll = () => {
    setQuery("");
    setDebouncedQuery("");
    setStateFilter("");
    setRiskBandFilter("");
    setProviderTypeFilter("");
    setPage(1);
  };

  const fetchProviders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", "20");
      if (debouncedQuery) params.set("q", debouncedQuery);
      if (stateFilter) params.set("state", stateFilter);
      if (riskBandFilter) params.set("risk_band", riskBandFilter);
      if (providerTypeFilter) params.set("provider_type", providerTypeFilter);

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
  }, [page, debouncedQuery, stateFilter, riskBandFilter, providerTypeFilter]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Providers</h1>
        <p className="text-muted-foreground text-sm">
          Search and explore Medicare providers
        </p>
      </div>

      {/* Search + filters row */}
      <div className="flex flex-wrap gap-2 items-center">
        <div className="relative w-full sm:w-64">
          <Search
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
          />
          <Input
            aria-label="Search providers"
            placeholder="Search by NPI or provider name..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9 w-full"
          />
        </div>

        <FilterSelect
          value={stateFilter}
          onChange={handleStateChange}
          placeholder="All states"
          aria-label="Filter by state"
          options={US_STATES.map((s) => ({ value: s, label: s }))}
          className="w-32"
        />

        <FilterSelect
          value={riskBandFilter}
          onChange={handleRiskBandChange}
          placeholder="All risk bands"
          aria-label="Filter by risk band"
          options={RISK_BAND_OPTIONS}
          className="w-40"
        />

        <FilterSelect
          value={providerTypeFilter}
          onChange={handleProviderTypeChange}
          placeholder="All provider types"
          aria-label="Filter by provider type"
          options={PROVIDER_TYPES.map((t) => ({ value: t, label: t }))}
          className="w-52"
        />

        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearAll} className="gap-1">
            <X className="h-3.5 w-3.5" />
            Clear all
          </Button>
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
            {hasActiveFilters && (
              <span className="text-muted-foreground"> (filtered)</span>
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
