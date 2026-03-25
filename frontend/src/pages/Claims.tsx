import React from "react";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
} from "lucide-react";
import { Link } from "react-router-dom";
import { getClaims } from "../lib/api";
import type { Claim, PaginationMeta, RiskBand } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { cn } from "../lib/utils";
import { formatUSD, scoreColor, formatCaseId } from "../lib/helpers";
import { InfoButton } from "../components/InfoButton";

export function Claims() {
  const [claims, setClaims] = React.useState<Claim[]>([]);
  const [meta, setMeta] = React.useState<PaginationMeta>({
    page: 1,
    per_page: 25,
    total: 0,
    pages: 0,
  });
  const [page, setPage] = React.useState(1);
  const [search, setSearch] = React.useState("");
  const [label, setLabel] = React.useState("");
  const [riskMin, setRiskMin] = React.useState("");
  const [loading, setLoading] = React.useState(true);

  const fetchClaims = React.useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        page: String(page),
        per_page: "25",
      };
      if (search) params.npi = search;
      if (label) params.case_label = label;
      if (riskMin) params.risk_min = riskMin;
      const res = await getClaims(params);
      setClaims(res.data);
      setMeta(res.meta);
    } catch {
      setClaims([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, label, riskMin]);

  React.useEffect(() => {
    fetchClaims();
  }, [fetchClaims]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Claims</h1>
          <p className="mt-1 text-sm text-slate-500">
            Browse service-level claim records with risk annotations.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium bg-slate-100 px-3 py-1.5 rounded-lg">
          <FileText className="w-3.5 h-3.5" />
          {meta.total.toLocaleString()} total records
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by NPI..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all"
            />
          </div>
          <select
            value={label}
            onChange={(e) => {
              setLabel(e.target.value);
              setPage(1);
            }}
            className="min-w-[180px] px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          >
            <option value="">All Labels</option>
            <option value="high_risk">High Risk</option>
            <option value="review">Review</option>
            <option value="stable">Stable</option>
          </select>
          <input
            type="number"
            placeholder="Min score"
            value={riskMin}
            onChange={(e) => {
              setRiskMin(e.target.value);
              setPage(1);
            }}
            className="w-32 px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
          <h2 className="font-semibold text-slate-700 text-sm">Claims Table</h2>
          <InfoButton title="Claims Table">Service-level claim records where each row represents one provider–HCPCS code combination. Shows total services rendered, beneficiary count, average submitted charges, and the computed risk score from peer comparison. Use filters to narrow by NPI, risk label, or minimum score.</InfoButton>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50/80">
              <tr>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Case ID
                </th>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">
                  NPI
                </th>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">
                  HCPCS
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Services
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Benes
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Charges
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Risk
                </th>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Label
                </th>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td
                    colSpan={9}
                    className="text-center py-12 text-sm text-slate-400"
                  >
                    Loading...
                  </td>
                </tr>
              ) : claims.length === 0 ? (
                <tr>
                  <td
                    colSpan={9}
                    className="text-center py-12 text-sm text-slate-400"
                  >
                    No claims found.
                  </td>
                </tr>
              ) : (
                claims.map((claim) => (
                  <tr
                    key={claim.case_id}
                    className="hover:bg-slate-50/60 transition-colors"
                  >
                    <td className="px-5 py-3 text-xs font-mono font-bold text-indigo-600">
                      <Link
                        to={`/claims/${claim.case_id}`}
                        className="hover:underline"
                      >
                        {formatCaseId(claim.case_id)}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-xs font-mono text-slate-700">
                      <Link
                        to={`/providers/${claim.npi}`}
                        className="hover:text-indigo-600 hover:underline"
                      >
                        {claim.npi}
                      </Link>
                    </td>
                    <td className="px-5 py-3 text-xs font-mono text-slate-700">
                      {claim.hcpcs_cd}
                    </td>
                    <td className="px-5 py-3 text-xs text-right text-slate-700">
                      {claim.tot_srvcs?.toLocaleString() ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-xs text-right text-slate-700">
                      {claim.tot_benes?.toLocaleString() ?? "—"}
                    </td>
                    <td className="px-5 py-3 text-xs text-right text-slate-700">
                      {formatUSD(claim.avg_submitted_charge)}
                    </td>
                    <td
                      className={cn(
                        "px-5 py-3 text-xs text-right font-bold",
                        scoreColor(claim.seed_risk_score),
                      )}
                    >
                      {claim.seed_risk_score ?? "—"}
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge
                        band={claim.seed_case_label as RiskBand | null}
                        size="sm"
                      />
                    </td>
                    <td className="px-5 py-3">
                      <Link
                        to={`/claims/${claim.case_id}`}
                        className="text-slate-400 hover:text-indigo-600"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-slate-100 bg-slate-50/40">
          <p className="text-xs text-slate-500">
            Page {meta.page} of {meta.pages} ({meta.total.toLocaleString()}{" "}
            total)
          </p>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="p-2 rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              disabled={page >= meta.pages}
              onClick={() => setPage((p) => p + 1)}
              className="p-2 rounded-lg border border-slate-200 bg-white text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
