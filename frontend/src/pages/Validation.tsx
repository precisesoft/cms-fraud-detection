import React from "react";
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Target,
  Activity,
  TrendingUp,
  Users,
  ArrowRight,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from "recharts";
import { getValidation } from "../lib/api";
import type { ValidationReport } from "../lib/api";
import { cn } from "../lib/utils";
import { InfoButton } from "../components/InfoButton";

export function Validation() {
  const [report, setReport] = React.useState<ValidationReport | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let active = true;
    getValidation()
      .then((r) => {
        if (active) setReport(r);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4 animate-in fade-in duration-500">
        <h1 className="text-2xl font-bold text-slate-900">Validation</h1>
        <p className="text-sm text-slate-400">
          Unable to load validation report.
        </p>
      </div>
    );
  }

  const chartData = report.detection_by_reason.map((d) => ({
    reason: d.reason,
    rate: +(d.rate * 100).toFixed(1),
    count: d.count,
    detected: d.detected,
  }));

  const detected =
    report.total_revoked_providers - (report.provider_level?.stable ?? 0);
  const missed = report.provider_level?.stable ?? 0;

  const pieData = [
    { name: "Detected", value: detected, color: "#22c55e" },
    { name: "Missed", value: missed, color: "#f43f5e" },
  ];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">
          Retrospective Validation
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Can behavioral signals alone detect providers that CMS eventually
          revoked?
        </p>
      </div>

      {/* Key Insight Callout */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-6 h-6 text-emerald-600 mt-0.5 shrink-0" />
          <div className="flex-1">
            <p className="font-bold text-emerald-900 text-lg">
              {(report.overall_detection_rate * 100).toFixed(1)}% of revoked
              providers detected from billing patterns alone
            </p>
            <p className="text-sm text-emerald-700 mt-1">
              Without seeing the revocation flag, our behavioral signals
              identified {detected} of {report.total_revoked_providers}{" "}
              eventually-revoked providers as needing review. The scoring engine
              saw only peer comparisons, enrollment status, and billing patterns
              — the same data available before CMS acted.
            </p>
          </div>
          <InfoButton title="Key Insight">
            Headline result of retrospective validation: what percentage of
            CMS-revoked providers our system would have flagged using only
            billing patterns, without ever seeing the revocation flag. This
            proves the system can identify fraud proactively.
          </InfoButton>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-500">
              <Target className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Detection Rate
            </span>
            <InfoButton title="Detection Rate">
              Percentage of eventually-revoked providers that our behavioral
              signals identified as high-risk or review — scored blind, without
              access to the revocation flag. Higher values indicate stronger
              predictive power.
            </InfoButton>
          </div>
          <p
            className={cn(
              "text-4xl font-black",
              report.overall_detection_rate >= 0.7
                ? "text-emerald-600"
                : report.overall_detection_rate >= 0.5
                  ? "text-amber-600"
                  : "text-rose-600",
            )}
          >
            {(report.overall_detection_rate * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Revoked providers flagged blind
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-rose-50 rounded-lg text-rose-500">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Revoked Tested
            </span>
          </div>
          <p className="text-4xl font-black text-slate-900">
            {report.total_revoked_providers}
          </p>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Providers in evaluation set
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-500">
              <TrendingUp className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Detection Lift
            </span>
            <InfoButton title="Detection Lift">
              How many times more likely a revoked provider is to be flagged
              compared to a non-revoked provider. For example, 3.0x means
              revoked providers are three times more likely to trigger a flag.
              Higher values indicate better signal specificity.
            </InfoButton>
          </div>
          <p className="text-4xl font-black text-indigo-600">
            {report.detection_lift ?? "—"}x
          </p>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            vs. non-revoked flagging rate
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-sky-50 rounded-lg text-sky-500">
              <Activity className="w-5 h-5" />
            </div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Baseline Rate
            </span>
            <InfoButton title="Baseline Flagging Rate">
              Percentage of non-revoked providers that are also flagged by our
              behavioral signals. Lower values mean fewer false positives. This
              represents the background noise level of the scoring engine.
            </InfoButton>
          </div>
          <p className="text-4xl font-black text-slate-900">
            {(report.baseline_flagging_rate * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-slate-400 mt-1 font-medium">
            Non-revoked providers flagged
          </p>
        </div>
      </div>

      {/* Comparison Strip: Revoked vs Non-Revoked */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-6 rounded-xl border border-rose-200 shadow-sm text-center">
          <Users className="w-5 h-5 text-rose-500 mx-auto mb-2" />
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Revoked Providers
          </p>
          <p className="text-3xl font-black text-rose-600">
            {(report.overall_detection_rate * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">
            flagged by behavioral signals
          </p>
        </div>
        <div className="flex items-center justify-center">
          <div className="bg-indigo-100 rounded-full p-3">
            <ArrowRight className="w-5 h-5 text-indigo-600" />
          </div>
          <p className="ml-2 text-sm font-bold text-indigo-600">
            {report.detection_lift ?? "—"}x more likely
          </p>
          <span className="ml-2">
            <InfoButton title="Revoked vs Non-Revoked Comparison">
              Side-by-side comparison of flagging rates. The left panel shows
              what percentage of revoked providers were flagged; the right shows
              the same for non-revoked providers. The multiplier in the center
              is the detection lift.
            </InfoButton>
          </span>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm text-center">
          <Users className="w-5 h-5 text-slate-400 mx-auto mb-2" />
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">
            Non-Revoked Providers
          </p>
          <p className="text-3xl font-black text-slate-700">
            {(report.baseline_flagging_rate * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">
            flagged by behavioral signals
          </p>
        </div>
      </div>

      {/* Provider-Level Outcome Donut + Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-emerald-500" /> Provider-Level
            Outcome
            <InfoButton title="Provider-Level Outcome">
              Donut chart showing how many revoked providers were correctly
              detected (flagged as high-risk or review) versus missed (labeled
              stable) by blind behavioral scoring. The detected segment
              validates the system&apos;s effectiveness.
            </InfoButton>
          </h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  strokeWidth={2}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: "1px solid #e2e8f0",
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-2 text-xs">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-emerald-500" /> Detected
              ({detected})
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-full bg-rose-500" /> Missed (
              {missed})
            </span>
          </div>
        </div>

        {/* Provider Label Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-indigo-500" /> Blind Scoring Label
            Distribution
            <InfoButton title="Blind Scoring Labels">
              How the scoring engine labeled revoked providers without seeing
              the revocation flag: High Risk, Review, or Stable (missed). A
              good system pushes most revoked providers into High Risk or Review
              bands.
            </InfoButton>
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            How revoked providers were labeled without seeing the revocation
            flag:
          </p>
          <div className="space-y-4">
            {[
              {
                label: "High Risk",
                count: report.provider_level?.high_risk ?? 0,
                color: "bg-rose-500",
                textColor: "text-rose-700",
              },
              {
                label: "Review",
                count: report.provider_level?.review ?? 0,
                color: "bg-amber-400",
                textColor: "text-amber-700",
              },
              {
                label: "Stable (missed)",
                count: report.provider_level?.stable ?? 0,
                color: "bg-slate-300",
                textColor: "text-slate-600",
              },
            ].map((item) => {
              const pct =
                report.total_revoked_providers > 0
                  ? (item.count / report.total_revoked_providers) * 100
                  : 0;
              return (
                <div key={item.label}>
                  <div className="flex justify-between items-center mb-1">
                    <span
                      className={cn("text-sm font-semibold", item.textColor)}
                    >
                      {item.label}
                    </span>
                    <span className="text-sm font-bold text-slate-700">
                      {item.count}{" "}
                      <span className="text-slate-400 font-normal">
                        ({pct.toFixed(1)}%)
                      </span>
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3">
                    <div
                      className={cn(
                        "h-3 rounded-full transition-all",
                        item.color,
                      )}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Detection by Reason Chart */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-500" /> Detection Rate by
          Revocation Reason
          <InfoButton title="Detection by Revocation Reason">
            Bar chart showing detection rates broken down by CMS revocation
            reason (e.g., fraud, abuse, felony conviction). Some reasons
            correlate more strongly with billing anomalies than others.
          </InfoButton>
        </h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 20, bottom: 60, left: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="reason"
                tick={{ fontSize: 10, fontWeight: 600, fill: "#64748b" }}
                angle={-45}
                textAnchor="end"
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                tickFormatter={(v: number) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid #e2e8f0",
                }}
                formatter={(value: number) => [`${value}%`, "Detection Rate"]}
              />
              <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={
                      entry.rate >= 70
                        ? "#22c55e"
                        : entry.rate >= 50
                          ? "#eab308"
                          : "#f43f5e"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detail Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-200 flex items-center gap-2">
          <h3 className="text-sm font-bold text-slate-700">Detection Detail by Reason</h3>
          <InfoButton title="Detection Detail by Reason">
            Tabular breakdown showing total providers, detected count, and
            detection rate for each revocation reason category. Green checkmarks
            indicate ≥ 70% detection; amber/red indicate lower rates.
          </InfoButton>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50/80">
              <tr>
                <th scope="col" className="px-5 py-3.5 text-left text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Revocation Reason
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Total
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Detected
                </th>
                <th scope="col" className="px-5 py-3.5 text-right text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Rate
                </th>
                <th scope="col" className="px-5 py-3.5 text-center text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.detection_by_reason.map((d) => (
                <tr
                  key={d.reason}
                  className="hover:bg-slate-50/60 transition-colors"
                >
                  <td className="px-5 py-3 text-xs font-semibold text-slate-800">
                    {d.reason}
                  </td>
                  <td className="px-5 py-3 text-xs text-right text-slate-700">
                    {d.count}
                  </td>
                  <td className="px-5 py-3 text-xs text-right text-slate-700">
                    {d.detected}
                  </td>
                  <td
                    className={cn(
                      "px-5 py-3 text-xs text-right font-bold",
                      d.rate >= 0.7
                        ? "text-emerald-600"
                        : d.rate >= 0.5
                          ? "text-amber-600"
                          : "text-rose-600",
                    )}
                  >
                    {(d.rate * 100).toFixed(1)}%
                  </td>
                  <td className="px-5 py-3 text-center">
                    {d.rate >= 0.7 ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 mx-auto" />
                    ) : d.rate >= 0.5 ? (
                      <AlertTriangle className="w-4 h-4 text-amber-500 mx-auto" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-rose-500 mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Methodology Flow */}
      <div className="bg-slate-900 text-white p-6 rounded-xl shadow-xl">
        <div className="flex items-center gap-2 mb-4">
          <p className="text-indigo-300 text-xs font-bold uppercase tracking-widest">
            Methodology
          </p>
          <InfoButton title="Validation Methodology">
            Three-step blind evaluation: (1) Remove the revocation flag from
            scoring inputs, (2) Score providers using only peer z-scores,
            enrollment status, and billing patterns, (3) Compare predicted risk
            labels against actual CMS revocation outcomes.
          </InfoButton>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {[
            {
              step: "1",
              title: "Remove Revocation Flag",
              desc: "Score providers as if CMS had not yet revoked them",
            },
            {
              step: "2",
              title: "Score on Behavior Alone",
              desc: "Use only peer z-scores, enrollment status, and billing patterns",
            },
            {
              step: "3",
              title: "Compare Against Outcomes",
              desc: "Check how many revoked providers were flagged by behavioral signals",
            },
          ].map((s) => (
            <div key={s.step} className="flex items-start gap-3">
              <span className="shrink-0 w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center font-bold text-sm">
                {s.step}
              </span>
              <div>
                <p className="font-semibold text-white text-sm">{s.title}</p>
                <p className="text-xs text-slate-400 mt-0.5">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="text-sm leading-relaxed text-slate-300">
          {report.methodology}
        </p>
      </div>
    </div>
  );
}
