import React from "react";
import {
  ArrowLeft,
  MapPin,
  Stethoscope,
  AlertCircle,
  CheckCircle2,
  Activity,
  DollarSign,
  Users as UsersIcon,
  ShieldAlert,
  MessageSquareMore,
  Network,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { cn } from "../lib/utils";
import {
  getProviderDetail,
  getProviderPeers,
  getProviderNetwork,
  getProviderSignals,
  getProviderRadar,
  getProviderGraph,
  getProviderExplain,
  getProviderScoreDetails,
} from "../lib/api";
import type {
  ProviderDetail as ProviderDetailType,
  PeerLine,
  RiskBand,
  Signal,
  RadarDimension,
  NetworkRiskResponse,
  GraphResponse,
  ExplainResponse,
  ProviderScoreDetails,
} from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { AssistantDrawer } from "../components/AssistantDrawer";
import { EvidenceGraph } from "../components/EvidenceGraph";
import { formatUSD, scoreColor, providerDisplayName } from "../lib/helpers";

export function ProviderDetail() {
  const { npi } = useParams();
  const [chatOpen, setChatOpen] = React.useState(false);
  const [detail, setDetail] = React.useState<ProviderDetailType | null>(null);
  const [peers, setPeers] = React.useState<PeerLine[]>([]);
  const [signals, setSignals] = React.useState<Signal[]>([]);
  const [radar, setRadar] = React.useState<RadarDimension[]>([]);
  const [network, setNetwork] = React.useState<NetworkRiskResponse | null>(
    null,
  );
  const [graph, setGraph] = React.useState<GraphResponse | null>(null);
  const [explain, setExplain] = React.useState<ExplainResponse | null>(null);
  const [scoreDetails, setScoreDetails] = React.useState<ProviderScoreDetails | null>(null);

  React.useEffect(() => {
    if (!npi) return;
    let active = true;
    getProviderDetail(npi)
      .then((d) => active && setDetail(d))
      .catch(() => {});
    getProviderPeers(npi)
      .then((d) => active && setPeers(d.lines))
      .catch(() => {});
    getProviderSignals(npi)
      .then((d) => active && setSignals(d))
      .catch(() => {});
    getProviderRadar(npi)
      .then((d) => active && setRadar(d.dimensions))
      .catch(() => {});
    getProviderNetwork(npi)
      .then((d) => active && setNetwork(d))
      .catch(() => {});
    getProviderGraph(npi)
      .then((d) => active && setGraph(d))
      .catch(() => {});
    getProviderExplain(npi)
      .then((d) => active && setExplain(d))
      .catch(() => {});
    getProviderScoreDetails(npi)
      .then((d) => active && setScoreDetails(d))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [npi]);

  if (!npi || !detail) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold text-slate-900">
          {detail === null && npi ? "Loading..." : "Provider Not Found"}
        </h1>
        <Link
          to="/providers"
          className="text-indigo-600 hover:text-indigo-700 font-medium text-sm"
        >
          Back to Providers
        </Link>
      </div>
    );
  }

  const riskSignals = signals.filter((s) => s.direction === "risk");
  const legitimacySignals = signals.filter((s) => s.direction === "legitimacy");
  const radarData = radar.map((d) => ({
    subject: d.dimension,
    A: d.provider,
    B: d.peer,
    fullMark: 100,
  }));

  return (
    <div className="space-y-8 animate-in fade-in duration-500 pb-12">
      <div className="flex flex-col gap-6">
        <Link
          to="/providers"
          className="flex items-center gap-2 text-slate-500 hover:text-indigo-600 transition-colors text-sm font-medium w-fit"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Providers
        </Link>

        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex items-start gap-5">
            <div className="w-16 h-16 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400">
              <UsersIcon className="w-8 h-8" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  {providerDisplayName(detail)}
                </h1>
                <StatusBadge band={detail.risk_band} size="sm" />
              </div>
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-2 text-sm text-slate-500">
                <div className="font-mono font-medium text-slate-700">
                  NPI: {npi}
                </div>
                <div className="flex items-center gap-1.5">
                  <Stethoscope className="w-4 h-4" />
                  {detail.provider_type ?? "—"}
                </div>
                <div className="flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" />
                  {detail.city ?? "—"}, {detail.state ?? "—"}
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setChatOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-700 text-sm font-semibold rounded-lg hover:bg-slate-50 transition-colors"
            >
              <MessageSquareMore className="w-4 h-4" /> Ask about this provider
            </button>
            <div className="flex items-center gap-8 px-8 py-4 bg-slate-50 rounded-xl border border-slate-100">
              <div className="text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Risk Score
                </p>
                <p
                  className={cn(
                    "text-4xl font-black leading-none",
                    scoreColor(detail.max_seed_risk_score),
                  )}
                >
                  {detail.max_seed_risk_score ?? "—"}
                </p>
              </div>
              <div className="w-px h-12 bg-slate-200" />
              <div className="text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">
                  ML Anomaly
                </p>
                <p
                  className={cn(
                    "text-4xl font-black leading-none",
                    scoreColor(explain?.anomaly_score ?? null),
                  )}
                >
                  {explain?.anomaly_score ?? "—"}
                </p>
              </div>
              <div className="w-px h-12 bg-slate-200" />
              <div className="text-center">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">
                  Revoked
                </p>
                <p className="text-lg font-bold leading-none">
                  {detail.revoked_2026 ? "Yes" : "No"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          {
            name: 'Explainable Risk',
            value: scoreDetails?.explainable_risk_score ?? detail.max_seed_risk_score,
            sub: 'Primary transparent score',
          },
          {
            name: 'Provider Anomaly',
            value: scoreDetails?.anomaly_score,
            sub: 'Isolation-forest provider anomaly',
          },
          {
            name: 'ML Suspicion Max',
            value: scoreDetails?.ml_suspicion_max,
            sub: scoreDetails?.service_line_scored_count ? `${scoreDetails.service_line_scored_count} scored service lines` : 'Latest model not available',
          },
          {
            name: 'Hybrid Composite Max',
            value: scoreDetails?.hybrid_composite_max,
            sub: scoreDetails?.hybrid_risk_label ? `Latest model · ${scoreDetails.hybrid_risk_label}` : 'Assistive hybrid layer',
          },
        ].map((card) => (
          <div key={card.name} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">{card.name}</p>
            <p className={cn('text-3xl font-black leading-none', scoreColor(typeof card.value === 'number' ? card.value : null))}>
              {typeof card.value === 'number' ? card.value.toFixed(1).replace(/\.0$/, '') : '—'}
            </p>
            <p className="text-[10px] text-slate-500 mt-2 font-medium">{card.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            name: "Service Lines",
            value: String(detail.service_line_count ?? 0),
            sub: "Unique service observations",
            icon: Activity,
          },
          {
            name: "Beneficiaries",
            value: String(detail.total_benes ?? 0),
            sub: "Total beneficiaries served",
            icon: UsersIcon,
          },
          {
            name: "Est. Payment",
            value: formatUSD(detail.total_estimated_payment),
            sub: "Total estimated payment",
            icon: DollarSign,
          },
          {
            name: "High-Risk Lines",
            value: String(detail.n_high_risk_lines ?? 0),
            sub: "Lines above risk threshold",
            icon: ShieldAlert,
          },
        ].map((kpi) => (
          <div
            key={kpi.name}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-slate-50 rounded-lg text-slate-500">
                <kpi.icon className="w-4 h-4" />
              </div>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {kpi.name}
              </span>
            </div>
            <p className="text-2xl font-bold text-slate-900">{kpi.value}</p>
            <p className="text-[10px] text-slate-400 mt-1 font-medium">
              {kpi.sub}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Metrics */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-6">Profile Metrics</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                ["Unique HCPCS", String(detail.unique_hcpcs_codes ?? 0)],
                [
                  "Avg Submitted Charge",
                  formatUSD(detail.mean_submitted_charge),
                ],
                [
                  "Avg Risk Score",
                  String(detail.avg_seed_risk_score?.toFixed(1) ?? "—"),
                ],
                ["Service HHI", (detail.service_hhi ?? 0).toFixed(2)],
                [
                  "Top-Code Share",
                  `${((detail.top_code_share ?? 0) * 100).toFixed(1)}%`,
                ],
              ].map(([name, value]) => (
                <div key={name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-500 font-medium">
                      {name}
                    </span>
                    <span className="text-xs font-bold text-slate-900">
                      {value}
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden" />
                </div>
              ))}
            </div>
          </div>

          {/* Signals */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm border-t-4 border-t-rose-500">
              <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 text-rose-500" /> Risk Signals
              </h3>
              <div className="space-y-3">
                {riskSignals.length ? (
                  riskSignals.map((signal) => (
                    <div
                      key={signal.name}
                      className="p-3 bg-rose-50/50 rounded-lg border border-rose-100"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-rose-900">
                          {signal.name}
                        </span>
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.5 bg-rose-200 text-rose-700 rounded">
                          {signal.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-rose-800/80 leading-relaxed">
                        {signal.description}
                      </p>
                      {signal.value != null && (
                        <p className="text-[10px] text-rose-600 mt-1">
                          Value: {signal.value.toFixed(2)} (threshold:{" "}
                          {signal.threshold?.toFixed(2) ?? "—"})
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500">
                    No risk signals found.
                  </div>
                )}
              </div>
            </div>

            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm border-t-4 border-t-emerald-500">
              <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-4">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" /> Legitimacy
                Signals
              </h3>
              <div className="space-y-3">
                {legitimacySignals.length ? (
                  legitimacySignals.map((signal) => (
                    <div
                      key={signal.name}
                      className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-100"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-emerald-900">
                          {signal.name}
                        </span>
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.5 bg-emerald-200 text-emerald-700 rounded">
                          {signal.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-emerald-800/80 leading-relaxed">
                        {signal.description}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500">
                    No legitimacy signals found.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Peer Lines */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-slate-800 mb-4">
              Service Line Peer Comparison
            </h3>
            {peers.length ? (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">
                        HCPCS
                      </th>
                      <th className="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider">
                        Description
                      </th>
                      <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">
                        Services
                      </th>
                      <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">
                        Peer Avg
                      </th>
                      <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">
                        Volume Z
                      </th>
                      <th className="px-4 py-3 text-right font-bold text-slate-500 uppercase tracking-wider">
                        Risk Score
                      </th>
                      <th className="px-4 py-3 text-left font-bold text-slate-500 uppercase tracking-wider whitespace-nowrap">
                        Label
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {peers.slice(0, 20).map((line) => (
                      <tr key={line.hcpcs_cd} className="hover:bg-slate-50">
                        <td className="px-4 py-3 font-mono font-bold text-slate-700">
                          {line.hcpcs_cd}
                        </td>
                        <td className="px-4 py-3 text-slate-600">
                          {line.hcpcs_desc ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-700">
                          {line.tot_srvcs ?? "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-700">
                          {line.peer_avg_tot_srvcs?.toFixed(1) ?? "—"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-3 text-right font-bold",
                            (line.service_volume_peer_z ?? 0) > 2
                              ? "text-rose-600"
                              : "text-slate-700",
                          )}
                        >
                          {line.service_volume_peer_z?.toFixed(2) ?? "—"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-3 text-right font-bold",
                            scoreColor(line.seed_risk_score),
                          )}
                        >
                          {line.seed_risk_score ?? "—"}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge band={line.seed_case_label as RiskBand | null} size="sm" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                No peer data available.
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Radar Chart */}
          {radarData.length > 0 && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-bold text-slate-800 mb-6">Risk Radar</h3>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart
                    cx="50%"
                    cy="50%"
                    outerRadius="80%"
                    data={radarData}
                  >
                    <PolarGrid stroke="#e2e8f0" />
                    <PolarAngleAxis
                      dataKey="subject"
                      tick={{ fontSize: 10, fontWeight: 600, fill: "#64748b" }}
                    />
                    <Radar
                      name="Provider"
                      dataKey="A"
                      stroke="#f43f5e"
                      fill="#f43f5e"
                      fillOpacity={0.4}
                    />
                    <Radar
                      name="Peer Avg"
                      dataKey="B"
                      stroke="#94a3b8"
                      fill="#94a3b8"
                      fillOpacity={0.2}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* ML Anomaly Explanation */}
          {explain?.anomaly_score != null && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-bold text-slate-800 flex items-center gap-2 mb-3">
                <Activity className="w-4 h-4 text-violet-500" /> ML Anomaly
                Explanation
              </h3>
              <p className="text-[10px] text-slate-500 mb-4">
                Independent unsupervised signal — higher values indicate more
                unusual billing patterns relative to all providers.
              </p>

              {/* Score Agreement */}
              {(() => {
                const ruleHigh = (detail.max_seed_risk_score ?? 0) >= 51;
                const mlHigh = (explain.anomaly_score ?? 0) >= 51;
                const ruleLow = (detail.max_seed_risk_score ?? 0) < 31;
                const mlLow = (explain.anomaly_score ?? 0) < 31;
                let label: string, color: string;
                if (ruleHigh && mlHigh) {
                  label = "Corroborated — both signals flag risk";
                  color = "bg-rose-100 text-rose-700 border-rose-200";
                } else if ((ruleHigh && !mlHigh) || (!ruleHigh && mlHigh)) {
                  label =
                    "Divergent — signals disagree, warrants investigation";
                  color = "bg-amber-100 text-amber-700 border-amber-200";
                } else if (ruleLow && mlLow) {
                  label = "Consistent low-risk";
                  color = "bg-emerald-100 text-emerald-700 border-emerald-200";
                } else {
                  label = "Mixed — moderate range on both";
                  color = "bg-slate-100 text-slate-600 border-slate-200";
                }
                return (
                  <div
                    className={cn(
                      "rounded-lg border px-3 py-2 text-[11px] font-semibold mb-4",
                      color,
                    )}
                  >
                    {label}
                  </div>
                );
              })()}

              {/* Feature Importance Bars */}
              {explain.top_features.length > 0 ? (
                <div className="space-y-2">
                  {explain.top_features.map((f) => {
                    const maxContrib = Math.max(
                      ...explain.top_features.map((x) =>
                        Math.abs(x.contribution),
                      ),
                      1,
                    );
                    const pct = Math.min(
                      100,
                      (Math.abs(f.contribution) / maxContrib) * 100,
                    );
                    const isRisk = f.direction === "risk";
                    return (
                      <div key={f.name}>
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-[10px] font-medium text-slate-600 truncate">
                            {f.name.replace(/_/g, " ")}
                          </span>
                          <span
                            className={cn(
                              "text-[10px] font-bold",
                              isRisk ? "text-rose-600" : "text-emerald-600",
                            )}
                          >
                            {isRisk ? "+" : ""}
                            {f.contribution.toFixed(1)}
                          </span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={cn(
                              "h-full rounded-full transition-all",
                              isRisk ? "bg-rose-400" : "bg-emerald-400",
                            )}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                  <p className="text-[9px] text-slate-400 mt-2">
                    Feature contributions to the anomaly score. Red =
                    risk-increasing, green = protective.
                  </p>
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3 text-[11px] text-slate-500">
                  ML explanation unavailable.
                </div>
              )}
            </div>
          )}

          {/* Network Context */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <Network className="w-4 h-4 text-sky-500" />
              <h3 className="font-bold text-slate-800">Network Context</h3>
            </div>
            <div className="space-y-3">
              {(network?.same_zip_flagged ?? []).slice(0, 5).map((n) => (
                <Link
                  key={n.npi}
                  to={`/providers/${n.npi}`}
                  className="block rounded-lg border border-slate-200 bg-slate-50 p-3 hover:border-indigo-200 hover:bg-indigo-50/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {n.provider_name ?? n.npi}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Same zip · {n.provider_type ?? "—"} · {n.state ?? "—"}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "font-bold text-sm",
                        scoreColor(n.risk_score),
                      )}
                    >
                      {n.risk_score ?? "—"}
                    </span>
                  </div>
                </Link>
              ))}
              {(network?.same_org_flagged ?? []).slice(0, 3).map((n) => (
                <Link
                  key={n.npi}
                  to={`/providers/${n.npi}`}
                  className="block rounded-lg border border-slate-200 bg-slate-50 p-3 hover:border-indigo-200 hover:bg-indigo-50/40 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {n.provider_name ?? n.npi}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Same org · {n.provider_type ?? "—"}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "font-bold text-sm",
                        scoreColor(n.risk_score),
                      )}
                    >
                      {n.risk_score ?? "—"}
                    </span>
                  </div>
                </Link>
              ))}
              {!network?.same_zip_flagged?.length &&
                !network?.same_org_flagged?.length && (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                    No network context available.
                  </div>
                )}
            </div>
          </div>

          {/* Evidence Graph */}
          {graph && graph.nodes.length > 0 && (
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              <h3 className="font-bold text-slate-800 mb-4">Evidence Graph</h3>
              <EvidenceGraph nodes={graph.nodes} edges={graph.edges} />
            </div>
          )}

          {/* Enrollment */}
          <div className="bg-slate-900 text-white p-6 rounded-xl shadow-xl">
            <h3 className="font-bold text-indigo-300 text-xs uppercase tracking-widest mb-4">
              Enrollment Context
            </h3>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase">
                  Entity Code
                </p>
                <p>{detail.entity_code ?? "—"}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase">
                  Medicare Participating
                </p>
                <p>{detail.medicare_participating ?? "—"}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase">
                  Enrolled 2025
                </p>
                <p>{detail.enrolled_2025 ? "Yes" : "No"}</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400 font-bold uppercase">
                  Revoked 2026
                </p>
                <p>{detail.revoked_2026 ? "Yes" : "No"}</p>
              </div>
              {detail.revocation_reason && (
                <div>
                  <p className="text-[10px] text-slate-400 font-bold uppercase">
                    Revocation Reason
                  </p>
                  <p>{detail.revocation_reason}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <AssistantDrawer
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        context={{
          type: "provider",
          entityId: npi,
          label: providerDisplayName(detail),
        }}
      />
    </div>
  );
}
