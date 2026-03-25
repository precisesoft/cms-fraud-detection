import type { RiskBand } from "./api";

export function riskBandLabel(band: RiskBand | null | undefined): string {
  if (!band) return "Unknown";
  switch (band) {
    case "high_risk":
      return "High Risk";
    case "review":
      return "Review";
    case "stable":
      return "Stable";
    default:
      return band;
  }
}

export function riskBandColor(band: RiskBand | null | undefined) {
  switch (band) {
    case "high_risk":
      return {
        bg: "bg-rose-100",
        text: "text-rose-700",
        border: "border-rose-200",
      };
    case "review":
      return {
        bg: "bg-amber-100",
        text: "text-amber-700",
        border: "border-amber-200",
      };
    case "stable":
      return {
        bg: "bg-emerald-100",
        text: "text-emerald-700",
        border: "border-emerald-200",
      };
    default:
      return {
        bg: "bg-slate-100",
        text: "text-slate-600",
        border: "border-slate-200",
      };
  }
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-slate-500";
  if (score >= 51) return "text-rose-700";
  if (score >= 31) return "text-amber-700";
  return "text-emerald-700";
}

export function caseLabelColor(label: string | null | undefined) {
  if (!label) return { bg: "bg-slate-100", text: "text-slate-600" };
  const l = label.toLowerCase();
  if (l.includes("high") || l.includes("critical"))
    return { bg: "bg-rose-100", text: "text-rose-700" };
  if (l.includes("review") || l.includes("medium"))
    return { bg: "bg-amber-100", text: "text-amber-700" };
  return { bg: "bg-emerald-100", text: "text-emerald-700" };
}

export function formatUSD(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
}

export function formatCompactUSD(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}

export function formatCaseId(caseId: string): string {
  const parts = caseId.split("|");
  if (parts.length >= 2) return `${parts[0]} — ${parts[1]}`;
  return caseId;
}

export function providerDisplayName(p: {
  provider_name?: string | null;
  provider_last_org_name?: string | null;
  provider_first_name?: string | null;
  npi?: string;
}): string {
  if (p.provider_name) return p.provider_name;
  const parts = [p.provider_last_org_name, p.provider_first_name].filter(
    Boolean,
  );
  return parts.length ? parts.join(", ") : (p.npi ?? "Unknown");
}
