import { Link } from "react-router-dom";
import { cn } from "../lib/utils";
import { formatUSD } from "../lib/helpers";
import { CaseDetailShell } from "../components/CaseDetailShell";
import type { Claim } from "../lib/api";

export function InvestigationDetail() {
  return (
    <CaseDetailShell
      backPath="/investigations"
      backLabel="Back to Investigations"
      entityType="investigation"
      notFoundLabel="Investigation not found."
      chatButtonLabel="Ask about this case"
      renderHeader={(data: Claim, caseId: string) => (
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">
              Investigation: {caseId}
            </h1>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-xs font-bold uppercase",
                data.seed_case_label?.includes("high")
                  ? "bg-rose-100 text-rose-700"
                  : "bg-amber-100 text-amber-700",
              )}
            >
              {data.seed_case_label ?? "—"}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-2 text-sm text-slate-500">
            <span>
              NPI:{" "}
              <Link
                to={`/providers/${data.npi}`}
                className="text-indigo-600 hover:underline font-medium font-mono"
              >
                {data.npi}
              </Link>
            </span>
            <span>{data.provider_last_org_name}</span>
            <span>
              HCPCS: <span className="font-mono">{data.hcpcs_cd}</span>
            </span>
          </div>
        </div>
      )}
      renderDetails={(data: Claim) => (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="font-bold text-slate-800 mb-6">Case Details</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            {(
              [
                ["HCPCS Code", data.hcpcs_cd],
                ["Description", data.hcpcs_desc ?? "—"],
                ["Services", data.tot_srvcs?.toLocaleString() ?? "—"],
                ["Avg Charge", formatUSD(data.avg_submitted_charge)],
                ["Case Label", data.seed_case_label ?? "—"],
              ] as [string, string][]
            ).map(([name, value]) => (
              <div key={name}>
                <p className="text-xs font-bold text-slate-600 uppercase tracking-widest mb-1">
                  {name}
                </p>
                <p className="text-sm font-semibold text-slate-800">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    />
  );
}
