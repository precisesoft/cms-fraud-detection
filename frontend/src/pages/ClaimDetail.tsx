import { Stethoscope, FileText } from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "../lib/utils";
import { formatUSD } from "../lib/helpers";
import { CaseDetailShell } from "../components/CaseDetailShell";
import type { Claim } from "../lib/api";

export function ClaimDetail() {
  return (
    <CaseDetailShell
      backPath="/claims"
      backLabel="Back to Claims"
      entityType="claim"
      notFoundLabel="Claim not found."
      chatButtonLabel="Ask about this claim"
      renderHeader={(claim: Claim, caseId: string) => (
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">Case {caseId}</h1>
            <span
              className={cn(
                "px-2.5 py-0.5 rounded-full text-xs font-bold uppercase",
                claim.seed_case_label?.includes("high")
                  ? "bg-rose-100 text-rose-700"
                  : claim.seed_case_label?.includes("review")
                    ? "bg-amber-100 text-amber-700"
                    : "bg-emerald-100 text-emerald-700",
              )}
            >
              {claim.seed_case_label ?? "Unknown"}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-2 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <Stethoscope className="w-4 h-4" />
              NPI:{" "}
              <Link
                to={`/providers/${claim.npi}`}
                className="text-indigo-600 hover:underline font-medium"
              >
                {claim.npi}
              </Link>
            </div>
            <div className="flex items-center gap-1.5">
              <FileText className="w-4 h-4" />
              HCPCS:{" "}
              <span className="font-mono font-medium">{claim.hcpcs_cd}</span>
            </div>
          </div>
        </div>
      )}
      renderDetails={(claim: Claim) => (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-800 mb-6">
            Service Line Details
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
            {(
              [
                ["HCPCS Code", claim.hcpcs_cd],
                ["Services", claim.tot_srvcs?.toLocaleString() ?? "—"],
                ["Beneficiaries", claim.tot_benes?.toLocaleString() ?? "—"],
                ["Submitted Charge", formatUSD(claim.avg_submitted_charge)],
                ["Est. Payment", formatUSD(claim.avg_medicare_payment_amt)],
                ["Provider Type", claim.provider_type ?? "—"],
                ["State", claim.state ?? "—"],
                ["Place of Service", claim.place_of_service ?? "—"],
              ] as [string, string][]
            ).map(([name, value]) => (
              <div key={name}>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                  {name}
                </p>
                <p className="text-sm font-semibold text-slate-800">{value}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      extraSections={(claim: Claim) => (
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-800 mb-4">Z-Score Metrics</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            {(
              [
                [
                  "Volume Peer Z",
                  claim["service_volume_peer_z"] as number | null,
                ],
                ["Charge Peer Z", claim["charge_peer_z"] as number | null],
                ["Bene Peer Z", claim["bene_peer_z"] as number | null],
                [
                  "Service/Bene Z",
                  claim["services_per_bene_peer_z"] as number | null,
                ],
              ] as [string, number | null][]
            ).map(([name, value]) => (
              <div key={name}>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                  {name}
                </p>
                <p
                  className={cn(
                    "text-lg font-bold",
                    (value ?? 0) > 2
                      ? "text-rose-600"
                      : (value ?? 0) > 1
                        ? "text-amber-600"
                        : "text-slate-800",
                  )}
                >
                  {value?.toFixed(2) ?? "—"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    />
  );
}
