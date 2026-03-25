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

/* -- Types -------------------------------------------------------- */

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
  provider_type: string;
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

export interface QueueStatus {
  running: boolean;
  ready: boolean;
  queue_size: number;
  position: number;
  total_emitted: number;
  tps: number;
  subscribers: number;
  build_time_s: number;
  distribution: Record<string, number>;
}

export type TpsPreset = 1 | 2 | 5 | 10;

interface LiveStreamState {
  running: boolean;
  tps: TpsPreset;
  events: LiveClaimEvent[];
  stats: LiveStats;
  stateDots: Map<string, LiveClaimEvent>;
  queueStatus: QueueStatus | null;
  start: () => void;
  stop: () => void;
  reset: () => void;
  setTps: (tps: TpsPreset) => void;
}

const LiveStreamContext = createContext<LiveStreamState | null>(null);

/* -- Provider ----------------------------------------------------- */

const MAX_FEED_EVENTS = 200;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 10000;

export function LiveStreamProvider({ children }: { children: ReactNode }) {
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempt = useRef(0);
  const intentionalClose = useRef(false);
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
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);

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

  // Use a ref to break the self-reference cycle for reconnect
  const connectRef = useRef<() => void>(() => {});

  useEffect(() => {
    connectRef.current = () => {
      if (esRef.current) esRef.current.close();
      intentionalClose.current = false;

      const es = new EventSource(`${API_BASE}/api/live/stream`);

      es.onmessage = (e) => {
        const data: LiveClaimEvent = JSON.parse(e.data);
        handleEvent(data);
        reconnectAttempt.current = 0;
      };

      es.onopen = () => {
        setRunning(true);
        reconnectAttempt.current = 0;
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        setRunning(false);

        // Auto-reconnect unless intentionally stopped
        if (!intentionalClose.current) {
          const delay = Math.min(
            RECONNECT_BASE_MS * Math.pow(2, reconnectAttempt.current),
            RECONNECT_MAX_MS,
          );
          reconnectAttempt.current += 1;
          reconnectTimer.current = setTimeout(() => {
            connectRef.current();
          }, delay);
        }
      };

      esRef.current = es;
    };
  }, [handleEvent]);

  const start = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    connectRef.current();
  }, []);

  const stop = useCallback(() => {
    intentionalClose.current = true;
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
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

  const setTps = useCallback((newTps: TpsPreset) => {
    setTpsState(newTps);
    // Tell the server to adjust emission rate
    fetch(`${API_BASE}/api/live/tps?tps=${newTps}`, { method: "POST" }).catch(
      () => {},
    );
    // If not connected, reconnect
    if (!esRef.current) {
      connectRef.current();
    }
  }, []);

  // Fetch queue status periodically
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/live/status`);
        if (res.ok && !cancelled) {
          setQueueStatus(await res.json());
        }
      } catch {
        // ignore
      }
    };
    poll();
    const interval = setInterval(poll, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      intentionalClose.current = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
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
        queueStatus,
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

/* -- Hook --------------------------------------------------------- */

export function useLiveStream(): LiveStreamState {
  const ctx = useContext(LiveStreamContext);
  if (!ctx)
    throw new Error("useLiveStream must be used within LiveStreamProvider");
  return ctx;
}
