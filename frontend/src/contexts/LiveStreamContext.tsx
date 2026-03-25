import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

/* ── Types ──────────────────────────────────────────────────── */

export interface LiveClaimEvent {
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

export interface LiveStats {
  total: number;
  flagged: number;
  totalLatency: number;
}

export type TpsPreset = 1 | 2 | 5 | 10;

const TPS_TO_INTERVAL: Record<TpsPreset, number> = {
  1: 1.0,
  2: 0.5,
  5: 0.2,
  10: 0.1,
};

interface LiveStreamState {
  running: boolean;
  tps: TpsPreset;
  events: LiveClaimEvent[];
  stats: LiveStats;
  stateDots: Map<string, LiveClaimEvent>;
  start: () => void;
  stop: () => void;
  reset: () => void;
  setTps: (tps: TpsPreset) => void;
}

const LiveStreamContext = createContext<LiveStreamState | null>(null);

/* ── Provider ───────────────────────────────────────────────── */

const MAX_FEED_EVENTS = 200;

export function LiveStreamProvider({ children }: { children: ReactNode }) {
  const esRef = useRef<EventSource | null>(null);
  const [running, setRunning] = useState(false);
  const [tps, setTpsState] = useState<TpsPreset>(2);
  const [events, setEvents] = useState<LiveClaimEvent[]>([]);
  const [stats, setStats] = useState<LiveStats>({
    total: 0,
    flagged: 0,
    totalLatency: 0,
  });
  const [stateDots, setStateDots] = useState<Map<string, LiveClaimEvent>>(
    new Map(),
  );

  const handleEvent = useCallback((evt: LiveClaimEvent) => {
    setEvents((prev) => [evt, ...prev].slice(0, MAX_FEED_EVENTS));
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

  const openConnection = useCallback(
    (interval: number) => {
      if (esRef.current) esRef.current.close();
      const es = new EventSource(
        `${API_BASE}/api/live/stream?interval=${interval}`,
      );
      es.onmessage = (e) => {
        const data: LiveClaimEvent = JSON.parse(e.data);
        handleEvent(data);
      };
      es.onerror = () => {
        es.close();
        esRef.current = null;
        setRunning(false);
      };
      esRef.current = es;
      setRunning(true);
    },
    [handleEvent],
  );

  const start = useCallback(() => {
    openConnection(TPS_TO_INTERVAL[tps]);
  }, [tps, openConnection]);

  const stop = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setRunning(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    setEvents([]);
    setStats({ total: 0, flagged: 0, totalLatency: 0 });
    setStateDots(new Map());
  }, [stop]);

  const setTps = useCallback(
    (newTps: TpsPreset) => {
      setTpsState(newTps);
      if (esRef.current) {
        openConnection(TPS_TO_INTERVAL[newTps]);
      }
    },
    [openConnection],
  );

  // Cleanup only on full app unmount (not navigation)
  useEffect(() => {
    return () => {
      esRef.current?.close();
    };
  }, []);

  return (
    <LiveStreamContext.Provider
      value={{
        running,
        tps,
        events,
        stats,
        stateDots,
        start,
        stop,
        reset,
        setTps,
      }}
    >
      {children}
    </LiveStreamContext.Provider>
  );
}

/* ── Hook ───────────────────────────────────────────────────── */

export function useLiveStream(): LiveStreamState {
  const ctx = useContext(LiveStreamContext);
  if (!ctx)
    throw new Error("useLiveStream must be used within LiveStreamProvider");
  return ctx;
}
