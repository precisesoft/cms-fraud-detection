import React from "react";
import { Link } from "react-router-dom";
import {
  ClipboardList,
  AlertTriangle,
  ChevronRight,
  ArrowUpDown,
} from "lucide-react";
import { getPendingCases } from "../lib/api";
import type { PendingCase, RiskBand } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { cn } from "../lib/utils";
import { scoreColor, formatUSD, formatCaseId } from "../lib/helpers";

type SortDir = "desc" | "asc";

function cardBorderClass(label: string | null | undefined): string {
  switch (label) {
    case "high_risk":
      return "border-rose-300 shadow-rose-100 bg-rose-50/20";
    case "review":
      return "border-amber-200 shadow-amber-50";
    default:
      return "border-slate-200";
  }
}

function scoreTextSize(label: string | null | undefined): string {
  switch (label) {
    case "high_risk":
      return "text-3xl";
    case "review":
      return "text-2xl";
    default:
      return "text-xl";
  }
}

export function Investigations() {
  const [cases, setCases] = React.useState<PendingCase[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [filterBand, setFilterBand] = React.useState("");
  const [minScore, setMinScore] = React.useState("");
  const [sortDir, setSortDir] = React.useState<SortDir>("desc");

  React.useEffect(() => {
    let active = true;
    getPendingCases(100)
      .then((d) => {
        if (active) setCases(d);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const displayed = React.useMemo(() => {
    let result = [...cases];
    if (filterBand)
      result = result.filter((c) => c.seed_case_label === filterBand);
    const min = minScore !== "" ? Number(minScore) : null;
    if (min !== null && !isNaN(min))
      result = result.filter((c) => (c.seed_risk_score ?? 0) >= min);
    result.sort((a, b) => {
      const aScore = a.seed_risk_score ?? -1;
      const bScore = b.seed_risk_score ?? -1;
      return sortDir === "desc" ? bScore - aScore : aScore - bScore;
    });
    return result;
  }, [cases, filterBand, minScore, sortDir]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Investigations</h1>
          <p className="mt-1 text-sm text-slate-500">
            Pending high-risk cases requiring analyst review and action.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-lg">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          {displayed.length === cases.length
            ? `${cases.length} cases pending review`
            : `${displayed.length} of ${cases.length} cases`}
        </div>
      </div>

      {/* Filters & Sort */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div className="flex flex-col sm:flex-row gap-4">
          <select
            value={filterBand}
            onChange={(e) => setFilterBand(e.target.value)}
            className="min-w-[180px] px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          >
            <option value="">All Risk Bands</option>
            <option value="high_risk">High Risk</option>
            <option value="review">Review</option>
            <option value="stable">Stable</option>
          </select>
          <input
            type="number"
            placeholder="Min score"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            min={0}
            max={100}
            className="w-36 px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          />
          <button
            onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
            className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-slate-50 hover:bg-indigo-50 hover:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all text-slate-600"
          >
            <ArrowUpDown className="w-4 h-4" />
            Score: {sortDir === "desc" ? "Highest First" : "Lowest First"}
          </button>
        </div>
      </div>

      {loading ? (
        <div role="status" aria-label="Loading investigations" className="flex items-center justify-center py-16">
          <span aria-hidden="true" className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-dashed border-slate-200">
          <ClipboardList className="w-12 h-12 text-emerald-400 mb-4" />
          <h3 className="text-lg font-bold text-slate-800 mb-2">All Clear</h3>
          <p className="text-sm text-slate-500">
            No pending investigations at this time.
          </p>
        </div>
      ) : displayed.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 bg-white rounded-2xl border border-dashed border-slate-200">
          <ClipboardList className="w-12 h-12 text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-800 mb-2">No Matches</h3>
          <p className="text-sm text-slate-500">
            No cases match the current filters.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {displayed.map((c) => (
            <Link
              key={c.case_id}
              to={`/investigations/${c.case_id}`}
              className={cn(
                "block bg-white rounded-xl border shadow-sm hover:border-indigo-200 hover:shadow-md transition-all p-5 group",
                cardBorderClass(c.seed_case_label),
              )}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-sm font-bold text-indigo-600 font-mono">
                      {formatCaseId(c.case_id)}
                    </span>
                    <StatusBadge
                      band={c.seed_case_label as RiskBand | null}
                      size="sm"
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-500">
                    <span>
                      NPI:{" "}
                      <span className="font-mono font-medium text-slate-700">
                        {c.npi}
                      </span>
                    </span>
                    <span>{c.provider_last_org_name ?? "—"}</span>
                    <span>
                      HCPCS: <span className="font-mono">{c.hcpcs_cd}</span>
                    </span>
                    {c.hcpcs_desc && (
                      <span className="text-slate-400">{c.hcpcs_desc}</span>
                    )}
                    <span>Services: {c.tot_srvcs ?? "—"}</span>
                    <span>Charge: {formatUSD(c.avg_submitted_charge)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                      Risk
                    </p>
                    <p
                      className={cn(
                        "font-black",
                        scoreTextSize(c.seed_case_label),
                        scoreColor(c.seed_risk_score),
                      )}
                    >
                      {c.seed_risk_score ?? "—"}
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-indigo-400 transition-colors" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
