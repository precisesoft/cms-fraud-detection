import { Badge } from "@/components/ui/badge";
import type { Signal, RiskBand } from "@/types/api";

export function SignalRow({ signal }: { signal: Signal }) {
  const isRisk = signal.direction === "risk";
  return (
    <div
      className={`flex items-start justify-between gap-2 rounded-md px-3 py-2 text-sm ${
        isRisk ? "bg-red-50" : "bg-green-50"
      }`}
    >
      <div>
        <span
          className={`font-medium ${isRisk ? "text-red-800" : "text-green-800"}`}
        >
          {signal.name}
        </span>
        <p className={`text-xs ${isRisk ? "text-red-600" : "text-green-600"}`}>
          {signal.description}
        </p>
      </div>
      {signal.value != null && (
        <span
          className={`text-xs font-mono shrink-0 ${isRisk ? "text-red-700" : "text-green-700"}`}
        >
          {signal.value.toFixed(1)}
        </span>
      )}
    </div>
  );
}

export function RiskBadge({ band }: { band: RiskBand | string }) {
  switch (band) {
    case "high_risk":
      return <Badge variant="destructive">High Risk</Badge>;
    case "review":
      return (
        <Badge className="bg-amber-100 text-amber-800 border-amber-200">
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
