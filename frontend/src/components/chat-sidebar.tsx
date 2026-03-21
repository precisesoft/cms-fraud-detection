"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Loader2,
  SendHorizonal,
  Database,
  TrendingUp,
  X,
  Sparkles,
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatChart } from "@/components/chat-chart";
import type { ChatMessage, ChatResponse, ChartSpec } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  columns?: string[];
  rows?: Record<string, unknown>[];
  row_count?: number;
  duration_ms?: number;
  chart_spec?: ChartSpec | null;
}

const SUGGESTIONS = [
  "How many high-risk providers are there?",
  "Which states have the most flagged providers?",
  "How many providers are in each risk band?",
];

function formatCellValue(val: unknown): string {
  if (val == null) return "N/A";
  if (typeof val === "number") {
    if (Number.isNaN(val)) return "N/A";
    if (Math.abs(val) >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
    if (Math.abs(val) >= 1_000)
      return val.toLocaleString("en-US", { maximumFractionDigits: 0 });
    if (Number.isInteger(val)) return val.toString();
    return val.toFixed(2);
  }
  return String(val);
}

function formatColumnName(col: string): string {
  return col
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bNpi\b/, "NPI")
    .replace(/\bHcpcs\b/, "HCPCS")
    .replace(/\bAmt\b/, "Amount")
    .replace(/\bAvg\b/, "Avg.");
}

function ScalarResult({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  const col = columns[0];
  const val = rows[0][col];
  return (
    <div className="my-2 rounded-xl neu-card p-4 text-center">
      <div className="flex items-center justify-center gap-1.5 label-stamped mb-1">
        <TrendingUp className="h-3 w-3" />
        {formatColumnName(col)}
      </div>
      <div className="text-3xl font-extrabold tracking-tight text-accent font-mono">
        {formatCellValue(val)}
      </div>
    </div>
  );
}

function SingleRowResult({
  columns,
  rows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
}) {
  const row = rows[0];
  return (
    <div className="my-2 rounded-xl neu-recessed p-3 space-y-1.5">
      {columns.map((col) => (
        <div
          key={col}
          className="flex justify-between items-baseline text-sm gap-3"
        >
          <span className="label-stamped text-[10px] shrink-0">
            {formatColumnName(col)}
          </span>
          <span className="font-semibold text-right truncate font-mono text-sm">
            {formatCellValue(row[col])}
          </span>
        </div>
      ))}
    </div>
  );
}

function DataTable({
  columns,
  rows,
  totalRows,
}: {
  columns: string[];
  rows: Record<string, unknown>[];
  totalRows: number;
}) {
  const displayRows = rows.slice(0, 10);
  return (
    <div className="my-2 rounded-xl neu-recessed overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border/50">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-2 py-1.5 text-left font-mono text-[10px] uppercase tracking-wider text-muted-foreground whitespace-nowrap"
                >
                  {formatColumnName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr key={i} className="border-b border-border/30 last:border-0">
                {columns.map((col) => (
                  <td
                    key={col}
                    className="px-2 py-1.5 whitespace-nowrap font-mono text-xs"
                  >
                    {formatCellValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalRows > 10 && (
        <div className="px-2 py-1 label-stamped text-center border-t border-border/30">
          Showing 10 of {totalRows.toLocaleString()} rows
        </div>
      )}
    </div>
  );
}

function QueryResults({ msg }: { msg: DisplayMessage }) {
  const { columns, rows, row_count, chart_spec } = msg;
  if (!columns?.length || !rows?.length) return null;

  if (rows.length === 1 && columns.length === 1) {
    return <ScalarResult columns={columns} rows={rows} />;
  }
  if (rows.length === 1) {
    return <SingleRowResult columns={columns} rows={rows} />;
  }

  return (
    <>
      {chart_spec && <ChatChart spec={chart_spec} />}
      <DataTable
        columns={columns}
        rows={rows}
        totalRows={row_count ?? rows.length}
      />
    </>
  );
}

interface ChatSidebarProps {
  onClose: () => void;
}

export function ChatSidebar({ onClose }: ChatSidebarProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || loading) return;

      const userMsg: DisplayMessage = { role: "user", content: text.trim() };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setLoading(true);

      const history: ChatMessage[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text.trim(), history }),
        });

        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail ?? `Request failed: ${res.status}`);
        }

        const data: ChatResponse = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.answer,
            sql: data.sql,
            columns: data.columns,
            rows: data.rows,
            row_count: data.row_count,
            duration_ms: data.duration_ms,
            chart_spec: data.chart_spec,
          },
        ]);
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content:
              e instanceof Error
                ? e.message
                : "Something went wrong. Try rephrasing your question.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading, messages],
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    sendMessage(input);
  }

  return (
    <aside className="w-[420px] shrink-0 flex flex-col neu-card border-l border-border/50 relative z-10">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full neu-float">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
          </div>
          <div>
            <span className="font-bold text-sm">Ask Argus</span>
            <span className="label-stamped block text-[9px] leading-none mt-0.5">
              AI ANALYST
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:neu-subtle transition-all duration-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="space-y-3 p-4">
          {messages.length === 0 && (
            <div className="space-y-3 pt-6">
              <div className="text-center">
                <div className="flex h-12 w-12 mx-auto items-center justify-center rounded-full neu-float mb-3">
                  <Sparkles className="h-6 w-6 text-accent" />
                </div>
                <p className="text-sm font-semibold mb-1">Ask anything</p>
                <p className="label-stamped text-[10px]">
                  Providers, claims, risk scores, billing patterns
                </p>
              </div>
              <div className="space-y-2 pt-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="block w-full text-left text-sm px-3 py-2.5 rounded-lg neu-subtle hover:neu-pressed transition-all duration-200 active:translate-y-px"
                    onClick={() => sendMessage(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {msg.role === "user" ? (
                <div className="max-w-[85%] rounded-xl px-3 py-2 text-sm bg-accent text-accent-foreground font-medium neu-subtle">
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                </div>
              ) : (
                <div className="max-w-[95%] w-full text-sm space-y-1">
                  <p className="whitespace-pre-wrap text-foreground leading-relaxed">
                    {msg.content}
                  </p>
                  <QueryResults msg={msg} />
                  {msg.sql && (
                    <details className="mt-1">
                      <summary className="label-stamped text-[10px] cursor-pointer flex items-center gap-1 hover:text-foreground transition-colors">
                        <Database className="h-3 w-3" />
                        SQL · {msg.row_count} rows · {msg.duration_ms}ms
                      </summary>
                      <pre className="mt-1 text-xs font-mono rounded-lg p-2 overflow-x-auto neu-recessed">
                        {msg.sql}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl px-3 py-2 neu-recessed">
                <Loader2 className="h-4 w-4 animate-spin text-accent" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-border/50 p-3 flex items-center gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about providers, claims, risk..."
          disabled={loading}
          className="flex-1 h-10 rounded-lg px-3 text-sm neu-recessed border-none outline-none bg-transparent disabled:opacity-50 font-mono placeholder:font-sans placeholder:text-muted-foreground"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground neu-subtle transition-all duration-150 hover:brightness-110 active:translate-y-px active:neu-pressed disabled:opacity-50 disabled:pointer-events-none"
        >
          <SendHorizonal className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
}
