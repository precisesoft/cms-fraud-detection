import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { HeatmapEntry } from "@/types/api";
import Link from "next/link";

function riskColor(score: number): string {
  if (score >= 40) return "bg-red-500";
  if (score >= 35) return "bg-red-400";
  if (score >= 32) return "bg-amber-500";
  if (score >= 28) return "bg-amber-400";
  if (score >= 24) return "bg-yellow-400";
  return "bg-green-400";
}

function riskTextColor(score: number): string {
  if (score >= 32) return "text-white";
  return "text-gray-900";
}

export default async function HeatmapPage() {
  let entries: HeatmapEntry[] = [];
  let error: string | null = null;

  try {
    const res = await api.heatmap();
    entries = res.data;
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load heatmap data";
  }

  const totalFlagged = entries.reduce((sum, e) => sum + e.flagged_count, 0);
  const totalProviders = entries.reduce((sum, e) => sum + e.provider_count, 0);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Risk Map</h1>
        <p className="text-muted-foreground text-sm">
          Geographic distribution of provider risk by state
        </p>
      </div>

      {error ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            <p>Unable to connect to API</p>
            <p className="text-xs mt-1">{error}</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">
                  States Reporting
                </p>
                <p className="text-2xl font-bold">{entries.length}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">Total Providers</p>
                <p className="text-2xl font-bold">
                  {new Intl.NumberFormat("en-US").format(totalProviders)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-4">
                <p className="text-xs text-muted-foreground">
                  High-Risk Providers
                </p>
                <p className="text-2xl font-bold text-destructive">
                  {new Intl.NumberFormat("en-US").format(totalFlagged)}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">State Risk Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-5 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-13 gap-2">
                {entries.map((e) => (
                  <Link
                    key={e.state}
                    href={`/providers?state=${e.state}`}
                    className={`rounded-lg p-2 text-center transition-transform hover:scale-105 ${riskColor(e.avg_risk_score)} ${riskTextColor(e.avg_risk_score)}`}
                    title={`${e.state}: ${e.provider_count} providers, ${e.flagged_count} flagged, avg score ${e.avg_risk_score}`}
                  >
                    <span className="text-xs font-bold block">{e.state}</span>
                    <span className="text-[10px] opacity-80 block">
                      {e.avg_risk_score.toFixed(0)}
                    </span>
                  </Link>
                ))}
              </div>
              <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
                <span>Low risk</span>
                <div className="flex gap-0.5">
                  <div className="w-6 h-3 rounded bg-green-400" />
                  <div className="w-6 h-3 rounded bg-yellow-400" />
                  <div className="w-6 h-3 rounded bg-amber-400" />
                  <div className="w-6 h-3 rounded bg-amber-500" />
                  <div className="w-6 h-3 rounded bg-red-400" />
                  <div className="w-6 h-3 rounded bg-red-500" />
                </div>
                <span>High risk</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">State Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {entries.map((e) => {
                  const pct =
                    e.provider_count > 0
                      ? (e.flagged_count / e.provider_count) * 100
                      : 0;
                  return (
                    <div key={e.state} className="flex items-center gap-3">
                      <span className="w-8 text-sm font-mono font-bold">
                        {e.state}
                      </span>
                      <div className="flex-1 h-4 rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full ${riskColor(e.avg_risk_score)}`}
                          style={{
                            width: `${Math.min((e.avg_risk_score / 50) * 100, 100)}%`,
                          }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-28 text-right">
                        {e.provider_count} providers
                      </span>
                      <span className="text-xs font-mono w-16 text-right">
                        {e.flagged_count} flagged
                      </span>
                      <span className="text-xs text-muted-foreground w-12 text-right">
                        {pct.toFixed(1)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
