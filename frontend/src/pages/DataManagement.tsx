import React from "react";
import {
  Upload,
  RefreshCw,
  Database,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  XCircle,
  Play,
  FlaskConical,
} from "lucide-react";
import { Link } from "react-router-dom";
import { cn } from "../lib/utils";
import { useAuth } from "../contexts/AuthContext";
import { InfoButton } from "../components/InfoButton";
import {
  uploadData,
  triggerRecalibrate,
  triggerRetrain,
  seedSyntheticData,
  getPipelineRuns,
  getPipelineRun,
  getSourceVersions,
} from "../lib/api";
import type {
  SourceVersion,
  UploadResponse,
  PipelineRunDetail,
} from "../lib/api";

/* ── Helpers ───────────────────────────────────────────────── */

function freshnessColor(uploadedAt: string): "green" | "amber" | "red" {
  const days = (Date.now() - new Date(uploadedAt).getTime()) / 86_400_000;
  if (days < 90) return "green";
  if (days < 180) return "amber";
  return "red";
}

function freshnessLabel(color: "green" | "amber" | "red") {
  if (color === "green") return "Current";
  if (color === "amber") return "Aging";
  return "Stale";
}

function formatDuration(s: number | null) {
  if (s == null) return "—";
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

const SOURCE_CADENCE: Record<string, string> = {
  "Part B Service": "Annual",
  "Part B Provider": "Annual",
  Enrollment: "Quarterly",
  Revocations: "Rolling",
};

const STAGE_NAMES: Record<string, string> = {
  data_generation: "Generate Synthetic Data",
  data_loading: "Load Data Sources",
  ingest: "Ingest Raw Data",
  peer_baselines: "Compute Peer Baselines",
  z_scores: "Calculate Z-Scores",
  seed_scoring: "Apply Seed Scoring Rules",
  provider_profiles: "Build Provider Profiles",
  ml_scoring: "ML Scoring & Composite",
};

const RECALIBRATE_STAGES = [
  "ingest",
  "peer_baselines",
  "z_scores",
  "seed_scoring",
  "provider_profiles",
  "ml_scoring",
];

const SEED_STAGES = ["data_generation", "data_loading", ...RECALIBRATE_STAGES];

function stageOrderForRun(runType?: string): string[] {
  if (runType === "seed_synthetic") return SEED_STAGES;
  return RECALIBRATE_STAGES;
}

/* ── Stage status icon ─────────────────────────────────────── */

function StageIcon({ status }: { status: string }) {
  if (status === "done" || status === "completed")
    return <CheckCircle2 className="w-5 h-5 text-emerald-500" />;
  if (status === "running")
    return <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />;
  if (status === "failed" || status === "error")
    return <XCircle className="w-5 h-5 text-rose-500" />;
  return <Clock className="w-5 h-5 text-slate-300" />;
}

/* ── Section 1: Data Sources ───────────────────────────────── */

function DataSourcesSection({
  sources,
  loading,
}: {
  sources: SourceVersion[];
  loading: boolean;
}) {
  const fallback: SourceVersion[] = [
    {
      source_type: "Part B Service",
      version: "—",
      uploaded_at: "",
      row_count: 0,
    },
    {
      source_type: "Part B Provider",
      version: "—",
      uploaded_at: "",
      row_count: 0,
    },
    { source_type: "Enrollment", version: "—", uploaded_at: "", row_count: 0 },
    { source_type: "Revocations", version: "—", uploaded_at: "", row_count: 0 },
  ];
  const display = sources.length > 0 ? sources : fallback;

  return (
    <section aria-labelledby="sources-heading">
      <div className="flex items-center gap-1.5 mb-4">
        <h2
          id="sources-heading"
          className="text-lg font-bold text-slate-800"
        >
          Data Sources
        </h2>
        <InfoButton title="Data Sources">
          Current CMS data files loaded into the system. Freshness badges indicate data currency: Current (uploaded &lt; 90 days ago), Aging (90–180 days), Stale (&gt; 180 days). Four source types: Part B Service (claims), Part B Provider (provider info), Enrollment (status), and Revocations (CMS actions).
        </InfoButton>
      </div>
      {loading ? (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-4">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading sources…
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {display.map((src) => {
            const color = src.uploaded_at
              ? freshnessColor(src.uploaded_at)
              : "red";
            const label = freshnessLabel(color);
            const cadence = SOURCE_CADENCE[src.source_type] ?? "Annual";
            return (
              <div
                key={src.source_type}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-5"
              >
                <div className="flex items-start justify-between mb-3">
                  <Database className="w-5 h-5 text-indigo-500" />
                  <span
                    className={cn(
                      "flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full",
                      color === "green"
                        ? "bg-emerald-50 text-emerald-700"
                        : color === "amber"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-rose-50 text-rose-700",
                    )}
                  >
                    <span
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        color === "green"
                          ? "bg-emerald-500"
                          : color === "amber"
                            ? "bg-amber-500"
                            : "bg-rose-500",
                      )}
                    />
                    {label}
                  </span>
                </div>
                <p className="font-semibold text-slate-800 text-sm">
                  {src.source_type}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Version:{" "}
                  <span className="font-medium">{src.version || "—"}</span>
                </p>
                <p className="text-xs text-slate-500">
                  Uploaded:{" "}
                  <span className="font-medium">
                    {src.uploaded_at
                      ? new Date(src.uploaded_at).toLocaleDateString()
                      : "—"}
                  </span>
                </p>
                <p className="text-xs text-slate-500">
                  Rows:{" "}
                  <span className="font-medium">
                    {src.row_count > 0 ? src.row_count.toLocaleString() : "—"}
                  </span>
                </p>
                <p className="text-xs text-slate-400 mt-2">{cadence}</p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

/* ── Section 2: Upload ─────────────────────────────────────── */

function UploadSection({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [sourceType, setSourceType] = React.useState("Part B Service");
  const [version, setVersion] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const [autoRecalibrate, setAutoRecalibrate] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);
  const [result, setResult] = React.useState<UploadResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.name.endsWith(".csv")) {
      setFile(dropped);
      setError(null);
    } else {
      setError("Only .csv files are accepted.");
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0];
    if (picked && picked.name.endsWith(".csv")) {
      setFile(picked);
      setError(null);
    } else if (picked) {
      setError("Only .csv files are accepted.");
    }
  }

  async function handleUpload() {
    if (!file) {
      setError("Please select a file.");
      return;
    }
    if (!version.trim()) {
      setError("Please enter a version.");
      return;
    }
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadData(file, sourceType, version.trim());
      setResult(res);
      if (autoRecalibrate) {
        await triggerRecalibrate();
      }
      onUploadComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section aria-labelledby="upload-heading">
      <div className="flex items-center gap-1.5 mb-4">
        <h2 id="upload-heading" className="text-lg font-bold text-slate-800">
          Upload New Data
        </h2>
        <InfoButton title="Upload CMS Data">
          Upload CMS data files in CSV format. Supports four source types matching CMS public use files. The optional auto-recalibrate checkbox triggers the full scoring pipeline immediately after upload to refresh all risk scores with the new data.
        </InfoButton>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label
              htmlFor="source-type"
              className="block text-xs font-semibold text-slate-600 mb-1"
            >
              Source Type
            </label>
            <select
              id="source-type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option>Part B Service</option>
              <option>Part B Provider</option>
              <option>Enrollment</option>
              <option>Revocations</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="version"
              className="block text-xs font-semibold text-slate-600 mb-1"
            >
              Version
            </label>
            <input
              id="version"
              type="text"
              placeholder="e.g. 2024 or Q1-2026"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Drop zone */}
        <div
          role="button"
          tabIndex={0}
          aria-label="Drop CSV file or click to browse"
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          className={cn(
            "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors",
            dragOver
              ? "border-indigo-400 bg-indigo-50"
              : file
                ? "border-emerald-400 bg-emerald-50"
                : "border-slate-200 hover:border-slate-300",
          )}
        >
          <Upload className="w-8 h-8 mx-auto mb-2 text-slate-400" />
          {file ? (
            <p className="text-sm font-semibold text-emerald-700">
              {file.name}
            </p>
          ) : (
            <>
              <p className="text-sm text-slate-600">
                Drag &amp; drop a <span className="font-semibold">.csv</span>{" "}
                file here, or click to browse
              </p>
              <p className="text-xs text-slate-400 mt-1">Accepts .csv only</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
            aria-label="File input"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            id="auto-recalibrate"
            type="checkbox"
            checked={autoRecalibrate}
            onChange={(e) => setAutoRecalibrate(e.target.checked)}
            className="w-4 h-4 text-indigo-600"
          />
          <label htmlFor="auto-recalibrate" className="text-sm text-slate-600">
            Auto-recalibrate after upload
          </label>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-4 py-3"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {result && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 text-sm">
            <p className="font-semibold text-emerald-800">Upload successful</p>
            <p className="text-emerald-700 text-xs mt-1">
              {result.row_count.toLocaleString()} rows · Version{" "}
              {result.version}
              {result.duplicate_detected && " · ⚠ Duplicate detected"}
            </p>
            {result.warnings.length > 0 && (
              <ul className="mt-2 text-xs text-amber-700 list-disc list-inside">
                {result.warnings.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={uploading || !file}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Upload className="w-4 h-4" />
          )}
          {uploading ? "Uploading…" : "Upload"}
        </button>
      </div>
    </section>
  );
}

/* ── Section 3: Recalibrate + Pipeline Progress ─────────────── */

function RecalibrateSection({
  activeRunId,
  onStart,
}: {
  activeRunId: number | null;
  onStart: (runId: number) => void;
}) {
  const [triggering, setTriggering] = React.useState(false);
  const [run, setRun] = React.useState<PipelineRunDetail | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const isRunning = run?.status === "running" || run?.status === "pending";

  // poll active run
  React.useEffect(() => {
    if (!activeRunId) return;
    let cancelled = false;
    async function poll() {
      try {
        const r = await getPipelineRun(activeRunId);
        if (!cancelled) {
          setRun(r);
          if (r.status === "running" || r.status === "pending") {
            setTimeout(poll, 2000);
          }
        }
      } catch {
        // ignore polling errors
      }
    }
    void poll();
    return () => {
      cancelled = true;
    };
  }, [activeRunId]);

  async function handleRecalibrate() {
    setTriggering(true);
    setError(null);
    try {
      const r = await triggerRecalibrate();
      onStart(r.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start recalibration",
      );
    } finally {
      setTriggering(false);
    }
  }

  async function handleRetrain() {
    setTriggering(true);
    setError(null);
    try {
      const r = await triggerRetrain();
      onStart(r.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start retrain");
    } finally {
      setTriggering(false);
    }
  }

  // Build ordered stage map
  const stageMap: Record<string, PipelineRunDetail["stage_results"][number]> =
    {};
  (run?.stage_results ?? []).forEach((s) => {
    stageMap[s.stage] = s;
  });

  return (
    <section aria-labelledby="recalibrate-heading">
      <div className="flex items-center gap-1.5 mb-4">
        <h2
          id="recalibrate-heading"
          className="text-lg font-bold text-slate-800"
        >
          Recalibrate Scores
        </h2>
        <InfoButton title="Score Recalibration">
          Triggers the full scoring pipeline: recomputes peer baselines, calculates z-scores, applies deterministic scoring rules, rebuilds provider profiles, and retrains ML models. Shows real-time progress through six pipeline stages with metrics and timing.
        </InfoButton>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleRecalibrate}
            disabled={triggering || isRunning}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {triggering ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Recalibrate Scores
          </button>
          <button
            onClick={handleRetrain}
            disabled={triggering || isRunning}
            className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {triggering ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Retrain Models
          </button>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-center gap-2 text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-4 py-3"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Pipeline progress panel */}
        {run && (
          <div className="border border-slate-200 rounded-xl p-5 space-y-3 bg-slate-50">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wide">
                Run #{run.id} — {run.run_type}
              </span>
              <span
                className={cn(
                  "text-xs font-semibold px-2 py-0.5 rounded-full",
                  run.status === "completed"
                    ? "bg-emerald-100 text-emerald-700"
                    : run.status === "failed"
                      ? "bg-rose-100 text-rose-700"
                      : "bg-indigo-100 text-indigo-700",
                )}
              >
                {run.status}
              </span>
            </div>

            {/* Stage cards */}
            {stageOrderForRun(run?.run_type).map((stageKey) => {
              const s = stageMap[stageKey];
              const stageStatus = s?.status ?? "pending";
              return (
                <div
                  key={stageKey}
                  className="flex items-start gap-3 bg-white rounded-lg border border-slate-100 px-4 py-3"
                >
                  <div className="mt-0.5">
                    <StageIcon status={stageStatus} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800">
                      {STAGE_NAMES[stageKey] ?? stageKey}
                    </p>
                    {s?.metrics && Object.keys(s.metrics).length > 0 && (
                      <p className="text-xs text-slate-500 mt-0.5 truncate">
                        {Object.entries(s.metrics)
                          .map(([k, v]) => `${k}: ${v}`)
                          .join(" · ")}
                      </p>
                    )}
                    {s?.error && (
                      <p className="text-xs text-rose-600 mt-1">{s.error}</p>
                    )}
                  </div>
                  {s?.duration_s != null && (
                    <span className="text-xs text-slate-400 shrink-0">
                      {formatDuration(s.duration_s)}
                    </span>
                  )}
                  {stageStatus === "pending" && (
                    <span className="text-xs text-slate-300 shrink-0">
                      pending
                    </span>
                  )}
                </div>
              );
            })}

            {/* Overall progress bar */}
            <div className="mt-3">
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-slate-500">Overall progress</span>
                <span className="text-xs font-bold text-indigo-600">
                  {run.progress_pct.toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all"
                  style={{ width: `${run.progress_pct}%` }}
                />
              </div>
            </div>

            {run.status === "failed" && run.error_message && (
              <div className="flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-lg px-4 py-3 mt-2">
                <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-rose-800">
                    Pipeline failed
                  </p>
                  <p className="text-xs text-rose-700 mt-0.5">
                    {run.error_message}
                  </p>
                </div>
                <button
                  onClick={handleRecalibrate}
                  className="flex items-center gap-1 text-xs text-rose-600 hover:text-rose-800 font-semibold"
                >
                  <RotateCcw className="w-3 h-3" /> Retry
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Section 4: Run History ─────────────────────────────────── */

function RunHistorySection() {
  const [runs, setRuns] = React.useState<PipelineRunDetail[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [expanded, setExpanded] = React.useState<Set<number>>(new Set());

  React.useEffect(() => {
    let active = true;
    getPipelineRuns()
      .then((r) => {
        if (active) setRuns(Array.isArray(r) ? r : []);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function toggleExpand(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <section aria-labelledby="history-heading">
      <div className="flex items-center gap-1.5 mb-4">
        <h2
          id="history-heading"
          className="text-lg font-bold text-slate-800"
        >
          Run History
        </h2>
        <InfoButton title="Pipeline Run History">
          Audit log of all pipeline executions showing run type, status, who triggered it, start/end times, and stage-by-stage details. Expand any row to see individual stage metrics, durations, and errors. Useful for tracking data lineage and debugging pipeline issues.
        </InfoButton>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center gap-2 text-slate-400 text-sm p-6">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading run history…
          </div>
        ) : runs.length === 0 ? (
          <p className="text-sm text-slate-400 p-6">No pipeline runs found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  {[
                    "Run ID",
                    "Type",
                    "Status",
                    "Triggered By",
                    "Started",
                    "Completed",
                    "",
                  ].map((h) => (
                    <th
                      key={h}
                      scope="col"
                      className="px-4 py-3 text-left text-xs font-bold text-slate-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.map((run) => (
                  <React.Fragment key={run.id}>
                    <tr className="hover:bg-slate-50/60 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono text-slate-700">
                        #{run.id}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-700">
                        {run.run_type}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "text-xs font-semibold px-2 py-0.5 rounded-full",
                            run.status === "completed"
                              ? "bg-emerald-100 text-emerald-700"
                              : run.status === "failed"
                                ? "bg-rose-100 text-rose-700"
                                : run.status === "running"
                                  ? "bg-indigo-100 text-indigo-700"
                                  : "bg-slate-100 text-slate-600",
                          )}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {run.triggered_by ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {formatDate(run.started_at)}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {formatDate(run.completed_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {run.stage_results.length > 0 && (
                          <button
                            onClick={() => toggleExpand(run.id)}
                            className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1 ml-auto"
                            aria-expanded={expanded.has(run.id)}
                          >
                            {expanded.has(run.id) ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                            Details
                          </button>
                        )}
                      </td>
                    </tr>
                    {expanded.has(run.id) && (
                      <tr>
                        <td colSpan={7} className="px-6 pb-4 bg-slate-50">
                          <div className="mt-2 space-y-1.5">
                            {run.stage_results.map((s) => (
                              <div
                                key={s.stage}
                                className="flex items-start gap-3 bg-white rounded-lg border border-slate-100 px-4 py-2"
                              >
                                <StageIcon status={s.status} />
                                <div className="flex-1">
                                  <p className="text-xs font-semibold text-slate-700">
                                    {STAGE_NAMES[s.stage] ?? s.stage}
                                  </p>
                                  {s.error && (
                                    <p className="text-xs text-rose-600">
                                      {s.error}
                                    </p>
                                  )}
                                  {s.metrics &&
                                    Object.keys(s.metrics).length > 0 && (
                                      <p className="text-xs text-slate-500">
                                        {Object.entries(s.metrics)
                                          .map(([k, v]) => `${k}: ${v}`)
                                          .join(" · ")}
                                      </p>
                                    )}
                                </div>
                                <span className="text-xs text-slate-400 shrink-0">
                                  {formatDuration(s.duration_s)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Seed Synthetic Data ───────────────────────────────────── */

function SeedSection({
  onStart,
  isRunning,
}: {
  onStart: (runId: number) => void;
  isRunning: boolean;
}) {
  const [seeding, setSeeding] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function handleSeed() {
    setSeeding(true);
    setError(null);
    try {
      const r = await seedSyntheticData();
      onStart(r.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start synthetic seed",
      );
    } finally {
      setSeeding(false);
    }
  }

  return (
    <section aria-labelledby="seed-heading">
      <div className="flex items-center gap-1.5 mb-4">
        <h2 id="seed-heading" className="text-lg font-bold text-slate-800">
          Demo Mode
        </h2>
        <InfoButton title="Demo Mode — Synthetic Data">
          One-click synthetic data generation for demonstrations. Creates 250 realistic synthetic providers with 4,250 service lines covering diverse specialties, states, and risk profiles. Then runs the full recalibration pipeline (peer baselines → z-scores → scoring → provider profiles → ML models).
        </InfoButton>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <FlaskConical className="w-8 h-8 text-indigo-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-slate-800">
                Seed Synthetic Data
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                Generate 250 synthetic providers (4,250 service lines) and run
                full recalibration pipeline. After completion, visit{" "}
                <Link
                  to="/live"
                  className="text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Live Monitor
                </Link>{" "}
                to see real-time scoring.
              </p>
            </div>
          </div>
          <button
            onClick={handleSeed}
            disabled={seeding || isRunning}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0"
          >
            {seeding ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FlaskConical className="w-4 h-4" />
            )}
            {seeding ? "Starting…" : "Seed Synthetic Data"}
          </button>
        </div>
        {error && (
          <div className="mt-3 flex items-start gap-2 bg-rose-50 border border-rose-200 rounded-lg px-4 py-3">
            <AlertCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-700">{error}</p>
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Main page ─────────────────────────────────────────────── */

export function DataManagement() {
  const { user } = useAuth();
  const [sources, setSources] = React.useState<SourceVersion[]>([]);
  const [sourcesLoading, setSourcesLoading] = React.useState(true);
  const [activeRunId, setActiveRunId] = React.useState<number | null>(null);

  const loadSources = React.useCallback(() => {
    setSourcesLoading(true);
    getSourceVersions()
      .then(setSources)
      .catch(() => setSources([]))
      .finally(() => setSourcesLoading(false));
  }, []);

  React.useEffect(() => {
    loadSources();
  }, [loadSources]);

  // Auto-resume: detect any running pipeline on page load/refresh
  React.useEffect(() => {
    getPipelineRuns()
      .then((runs) => {
        const running = runs.find(
          (r) => r.status === "running" || r.status === "pending",
        );
        if (running) setActiveRunId(running.id);
      })
      .catch(() => {});
  }, []);

  // Admin guard — after hooks
  if (user && user.role !== "admin") {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <AlertCircle className="w-12 h-12 text-rose-400" />
        <h1 className="text-2xl font-bold text-slate-800">Access Denied</h1>
        <p className="text-slate-500">
          This page is only accessible to administrators.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-in fade-in duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Data Management</h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload CMS data, trigger recalibration, and monitor pipeline runs.
        </p>
      </div>
      <DataSourcesSection sources={sources} loading={sourcesLoading} />
      <SeedSection onStart={setActiveRunId} isRunning={activeRunId != null} />
      <UploadSection onUploadComplete={loadSources} />
      <RecalibrateSection activeRunId={activeRunId} onStart={setActiveRunId} />
      <RunHistorySection />
    </div>
  );
}
