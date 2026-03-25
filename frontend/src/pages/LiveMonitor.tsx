import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
} from "react-simple-maps";
import {
  Activity,
  Expand,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  X,
  Zap,
  TrendingUp,
} from "lucide-react";
import { cn } from "../lib/utils";
import { formatUSD } from "../lib/helpers";

const API_BASE = import.meta.env.DEV
  ? ""
  : import.meta.env.VITE_API_BASE_URL ?? "";
const GEO_URL = "https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json";

/* ── Types ──────────────────────────────────────────────────── */

interface LiveClaimEvent {
  event_id: string;
  timestamp: string;
  npi: string;
  provider_name: string;
  state: string;
  city: string;
  hcpcs_code: string;
  hcpcs_desc: string;
  submitted_charge: number;
  risk_score: number;
  legitimacy_score: number;
  case_label: "high_risk" | "review" | "stable";
  anomaly_score: number | null;
  signals: string[];
  scoring_latency_ms: number;
}

interface LiveStats {
  total: number;
  flagged: number;
  totalLatency: number;
}

/* ── State centroids (lon, lat) for geoAlbersUsa projection ── */

const STATE_CENTROIDS: Record<string, [number, number]> = {
  AL: [-86.9, 32.8],
  AK: [-153.5, 64.3],
  AZ: [-111.1, 34.0],
  AR: [-92.4, 34.8],
  CA: [-119.7, 36.8],
  CO: [-105.8, 39.0],
  CT: [-72.8, 41.6],
  DE: [-75.5, 39.0],
  DC: [-77.0, 38.9],
  FL: [-81.5, 27.7],
  GA: [-83.5, 32.7],
  HI: [-155.5, 19.9],
  ID: [-114.7, 44.1],
  IL: [-89.4, 40.0],
  IN: [-86.1, 39.8],
  IA: [-93.1, 42.0],
  KS: [-98.5, 38.5],
  KY: [-84.3, 37.8],
  LA: [-92.5, 31.2],
  ME: [-69.4, 45.3],
  MD: [-76.6, 39.0],
  MA: [-71.8, 42.4],
  MI: [-84.5, 44.3],
  MN: [-94.7, 46.4],
  MS: [-89.7, 32.7],
  MO: [-91.8, 38.6],
  MT: [-110.4, 46.9],
  NE: [-99.9, 41.5],
  NV: [-116.6, 38.8],
  NH: [-71.6, 43.7],
  NJ: [-74.4, 40.1],
  NM: [-105.9, 34.5],
  NY: [-75.5, 43.0],
  NC: [-79.0, 35.8],
  ND: [-101.0, 47.5],
  OH: [-82.8, 40.4],
  OK: [-97.5, 35.5],
  OR: [-120.6, 43.9],
  PA: [-77.2, 41.2],
  RI: [-71.5, 41.7],
  SC: [-81.2, 34.0],
  SD: [-99.9, 44.3],
  TN: [-86.6, 35.5],
  TX: [-99.9, 31.5],
  UT: [-111.1, 39.3],
  VT: [-72.6, 44.0],
  VA: [-79.5, 37.8],
  WA: [-120.7, 47.4],
  WV: [-80.6, 38.6],
  WI: [-89.6, 44.3],
  WY: [-107.6, 43.0],
};

const FIPS_TO_ABBR: Record<string, string> = {
  "01": "AL",
  "02": "AK",
  "04": "AZ",
  "05": "AR",
  "06": "CA",
  "08": "CO",
  "09": "CT",
  "10": "DE",
  "11": "DC",
  "12": "FL",
  "13": "GA",
  "15": "HI",
  "16": "ID",
  "17": "IL",
  "18": "IN",
  "19": "IA",
  "20": "KS",
  "21": "KY",
  "22": "LA",
  "23": "ME",
  "24": "MD",
  "25": "MA",
  "26": "MI",
  "27": "MN",
  "28": "MS",
  "29": "MO",
  "30": "MT",
  "31": "NE",
  "32": "NV",
  "33": "NH",
  "34": "NJ",
  "35": "NM",
  "36": "NY",
  "37": "NC",
  "38": "ND",
  "39": "OH",
  "40": "OK",
  "41": "OR",
  "42": "PA",
  "44": "RI",
  "45": "SC",
  "46": "SD",
  "47": "TN",
  "48": "TX",
  "49": "UT",
  "50": "VT",
  "51": "VA",
  "53": "WA",
  "54": "WV",
  "55": "WI",
  "56": "WY",
};

/* ── Helpers ─────────────────────────────────────────────────── */

function labelColor(label: string): string {
  if (label === "high_risk") return "#ef4444";
  if (label === "review") return "#f59e0b";
  return "#22c55e";
}

function labelDot(label: string): string {
  if (label === "high_risk") return "bg-rose-500";
  if (label === "review") return "bg-amber-500";
  return "bg-emerald-500";
}

/* ── Component ───────────────────────────────────────────────── */

export function LiveMonitor() {
  const navigate = useNavigate();
  const esRef = useRef<EventSource | null>(null);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(0.5);
  const [events, setEvents] = useState<LiveClaimEvent[]>([]);
  const [stats, setStats] = useState<LiveStats>({
    total: 0,
    flagged: 0,
    totalLatency: 0,
  });
  const [stateDots, setStateDots] = useState<Map<string, LiveClaimEvent>>(
    new Map(),
  );
  const [feedExpanded, setFeedExpanded] = useState(false);

  const handleEvent = useCallback((evt: LiveClaimEvent) => {
    setEvents((prev) => [evt, ...prev].slice(0, 50));
    setStats((prev) => ({
      total: prev.total + 1,
      flagged: prev.flagged + (evt.case_label === "high_risk" ? 1 : 0),
      totalLatency: prev.totalLatency + evt.scoring_latency_ms,
    }));
    setStateDots((prev) => {
      const next = new Map(prev);
      next.set(evt.state, evt);
      return next;
    });
  }, []);

  const startStream = useCallback(() => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource(`${API_BASE}/api/live/stream?interval=${speed}`);
    es.onmessage = (e) => {
      const data: LiveClaimEvent = JSON.parse(e.data);
      handleEvent(data);
    };
    es.onerror = () => {
      es.close();
      setRunning(false);
    };
    esRef.current = es;
    setRunning(true);
  }, [speed, handleEvent]);

  const stopStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setRunning(false);
  }, []);

  const resetStream = useCallback(() => {
    stopStream();
    setEvents([]);
    setStats({ total: 0, flagged: 0, totalLatency: 0 });
    setStateDots(new Map());
  }, [stopStream]);

  // Restart stream when speed changes while running
  useEffect(() => {
    if (running) {
      startStream();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  // Close modal on Escape
  useEffect(() => {
    if (!feedExpanded) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFeedExpanded(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [feedExpanded]);

  const flagRate = stats.total > 0 ? (stats.flagged / stats.total) * 100 : 0;
  const avgLatency = stats.total > 0 ? stats.totalLatency / stats.total : 0;

  return (
    <div className="space-y-4 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Real-Time Payment Monitor
          </h1>
          {running && (
            <span className="flex items-center gap-1.5 text-xs font-bold text-rose-600">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
              LIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500 font-medium">TPS</label>
          <input
            type="range"
            min={0.1}
            max={2}
            step={0.1}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="w-24 accent-indigo-600"
          />
          <span className="text-xs text-slate-600 font-mono w-12">~{Math.round(1 / speed)}/s</span>
          <button
            onClick={running ? stopStream : startStream}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors",
              running
                ? "bg-slate-200 text-slate-700 hover:bg-slate-300"
                : "bg-indigo-600 text-white hover:bg-indigo-700",
            )}
          >
            {running ? (
              <>
                <Pause className="w-4 h-4" /> Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4" /> Start
              </>
            )}
          </button>
          <button
            onClick={resetStream}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Reset"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          label="Claims Processed"
          value={stats.total.toLocaleString()}
          icon={<Activity className="w-4 h-4 text-indigo-500" />}
          color="text-slate-800"
        />
        <StatCard
          label="Flagged (High Risk)"
          value={stats.flagged.toLocaleString()}
          icon={<ShieldAlert className="w-4 h-4 text-rose-500" />}
          color={stats.flagged > 0 ? "text-rose-600" : "text-slate-800"}
        />
        <StatCard
          label="Flag Rate"
          value={`${flagRate.toFixed(1)}%`}
          icon={<TrendingUp className="w-4 h-4 text-amber-500" />}
          color={
            flagRate > 10
              ? "text-rose-600"
              : flagRate > 5
                ? "text-amber-600"
                : "text-emerald-600"
          }
        />
        <StatCard
          label="Avg Latency"
          value={`${avgLatency.toFixed(1)}ms`}
          icon={<Zap className="w-4 h-4 text-emerald-500" />}
          color={
            avgLatency > 100
              ? "text-rose-600"
              : avgLatency > 50
                ? "text-amber-600"
                : "text-emerald-600"
          }
        />
      </div>

      {/* Map + Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 items-start">
        {/* US Map */}
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm p-4 overflow-hidden">
          <div className="aspect-[8/5]">
            <ComposableMap
              projection="geoAlbersUsa"
              projectionConfig={{ scale: 1000 }}
              width={800}
              height={500}
              style={{ width: "100%", height: "100%" }}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const abbr = FIPS_TO_ABBR[geo.id as string];
                    const dot = abbr ? stateDots.get(abbr) : undefined;
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        fill={
                          dot ? `${labelColor(dot.case_label)}22` : "#e2e8f0"
                        }
                        stroke="#fff"
                        strokeWidth={0.5}
                        style={{
                          default: { outline: "none", transition: "fill 0.3s" },
                          hover: { outline: "none" },
                          pressed: { outline: "none" },
                        }}
                      />
                    );
                  })
                }
              </Geographies>

              {/* Pulsing dots */}
              <AnimatePresence>
                {Array.from(stateDots.entries()).map(([st, evt]) => {
                  const coords = STATE_CENTROIDS[st];
                  if (!coords) return null;
                  return (
                    <Marker key={`${st}-${evt.event_id}`} coordinates={coords}>
                      <motion.circle
                        r={6}
                        fill={labelColor(evt.case_label)}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: [0, 1.6, 1], opacity: [0, 1, 0.9] }}
                        transition={{ duration: 0.6, ease: "easeOut" }}
                      />
                      <motion.circle
                        r={8}
                        fill="none"
                        stroke={labelColor(evt.case_label)}
                        strokeWidth={1.5}
                        initial={{ scale: 1, opacity: 0.6 }}
                        animate={{ scale: [1, 2.5], opacity: [0.6, 0] }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                          ease: "easeOut",
                        }}
                      />
                    </Marker>
                  );
                })}
              </AnimatePresence>
            </ComposableMap>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-1 text-xs font-bold text-slate-500">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-emerald-500" /> Stable
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-amber-500" /> Review
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-rose-500" /> High Risk
            </div>
          </div>
        </div>

        {/* Live Feed */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[500px]">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800">Live Feed</h3>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-slate-400">
                {events.length} events
              </span>
              <button
                onClick={() => setFeedExpanded(true)}
                className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                title="Expand feed"
              >
                <Expand className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
          <FeedList
            events={events}
            running={running}
            maxItems={20}
            navigate={navigate}
          />
        </div>
      </div>

      {/* Expanded Feed Modal */}
      {feedExpanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={() => setFeedExpanded(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Expanded live feed"
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800">Live Feed</h3>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-slate-400">
                  {events.length} events
                </span>
                <button
                  onClick={() => setFeedExpanded(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <FeedList
              events={events}
              running={running}
              maxItems={50}
              navigate={navigate}
            />
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────── */

function FeedList({
  events,
  running,
  maxItems,
  navigate,
}: {
  events: LiveClaimEvent[];
  running: boolean;
  maxItems: number;
  navigate: (path: string) => void;
}) {
  return (
    <div className="flex-1 overflow-y-auto divide-y divide-slate-50">
      {events.length === 0 ? (
        <div className="flex items-center justify-center h-40 text-sm text-slate-400">
          {running ? "Waiting for events..." : 'Press "Start" to begin'}
        </div>
      ) : (
        <AnimatePresence initial={false}>
          {events.slice(0, maxItems).map((evt) => (
            <motion.button
              key={evt.event_id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => navigate(`/providers/${evt.npi}`)}
              className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-slate-50 transition-colors"
            >
              <span
                className={cn(
                  "w-2 h-2 rounded-full shrink-0",
                  labelDot(evt.case_label),
                )}
              />
              <span className="text-xs font-bold text-slate-500 w-6">
                {evt.state}
              </span>
              <span className="text-xs text-slate-700 truncate flex-1 min-w-0">
                {evt.provider_name}
              </span>
              <span className="text-[10px] font-mono text-slate-400 shrink-0">
                {evt.hcpcs_code}
              </span>
              <span className="text-[10px] text-slate-500 shrink-0 w-14 text-right">
                {formatUSD(evt.submitted_charge)}
              </span>
              <span
                className={cn(
                  "text-xs font-bold shrink-0 w-6 text-right",
                  evt.risk_score >= 51
                    ? "text-rose-600"
                    : evt.risk_score >= 31
                      ? "text-amber-600"
                      : "text-emerald-600",
                )}
              >
                {evt.risk_score}
              </span>
              <span className="text-[10px] font-mono text-slate-300 shrink-0 w-10 text-right">
                {evt.scoring_latency_ms.toFixed(1)}ms
              </span>
            </motion.button>
          ))}
        </AnimatePresence>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-4 py-3 flex items-center gap-3">
      <div className="p-2 rounded-lg bg-slate-50">{icon}</div>
      <div>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
          {label}
        </p>
        <p className={cn("text-lg font-bold", color)}>{value}</p>
      </div>
    </div>
  );
}
