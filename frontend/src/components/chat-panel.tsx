"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Loader2,
  MessageSquare,
  SendHorizonal,
  Database,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { ChatMessage, ChatResponse } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DisplayMessage {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  columns?: string[];
  rows?: Record<string, unknown>[];
  row_count?: number;
  duration_ms?: number;
}

const SUGGESTIONS = [
  "How many high-risk providers are there?",
  "Top 5 providers by total payment",
  "Which states have the most flagged providers?",
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
    <div className="my-2 rounded-lg border bg-gradient-to-br from-primary/5 to-primary/10 p-4 text-center">
      <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground mb-1">
        <TrendingUp className="h-3 w-3" />
        {formatColumnName(col)}
      </div>
      <div className="text-2xl font-bold tracking-tight text-primary">
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
    <div className="my-2 rounded-lg border bg-muted/30 p-3 space-y-1.5">
      {columns.map((col) => (
        <div
          key={col}
          className="flex justify-between items-baseline text-sm gap-3"
        >
          <span className="text-muted-foreground text-xs shrink-0">
            {formatColumnName(col)}
          </span>
          <span className="font-medium text-right truncate">
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
    <div className="my-2 rounded-lg border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted/50 border-b">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-2 py-1.5 text-left font-medium text-muted-foreground whitespace-nowrap"
                >
                  {formatColumnName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, i) => (
              <tr
                key={i}
                className="border-b last:border-0 hover:bg-muted/30 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col} className="px-2 py-1.5 whitespace-nowrap">
                    {formatCellValue(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {totalRows > 10 && (
        <div className="px-2 py-1 text-xs text-muted-foreground bg-muted/30 border-t text-center">
          Showing 10 of {totalRows.toLocaleString()} rows
        </div>
      )}
    </div>
  );
}

function QueryResults({ msg }: { msg: DisplayMessage }) {
  const { columns, rows, row_count } = msg;
  if (!columns?.length || !rows?.length) return null;

  if (rows.length === 1 && columns.length === 1) {
    return <ScalarResult columns={columns} rows={rows} />;
  }
  if (rows.length === 1) {
    return <SingleRowResult columns={columns} rows={rows} />;
  }
  return (
    <DataTable
      columns={columns}
      rows={rows}
      totalRows={row_count ?? rows.length}
    />
  );
}

export function ChatPanel() {
  const [open, setOpen] = useState(false);
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

      // Build history from previous messages (role + content only)
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
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        render={
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground"
          />
        }
      >
        <MessageSquare className="h-4 w-4" />
        Ask AI
      </SheetTrigger>

      <SheetContent side="right" className="flex flex-col sm:max-w-md">
        <SheetHeader className="border-b pb-3">
          <SheetTitle>Ask Argus AI</SheetTitle>
          <p className="text-xs text-muted-foreground">
            Ask questions about providers, claims, risk scores, and billing
            patterns.
          </p>
        </SheetHeader>

        {/* Messages */}
        <ScrollArea className="flex-1 min-h-0">
          <div className="space-y-3 p-4">
            {messages.length === 0 && (
              <div className="space-y-2 pt-8">
                <p className="text-sm text-muted-foreground text-center">
                  Try a question:
                </p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className="block w-full text-left text-sm px-3 py-2 rounded-md border hover:bg-muted transition-colors"
                    onClick={() => sendMessage(s)}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "user" ? (
                  <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-primary text-primary-foreground">
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
                        <summary className="text-xs text-muted-foreground cursor-pointer flex items-center gap-1 hover:text-foreground transition-colors">
                          <Database className="h-3 w-3" />
                          SQL &middot; {msg.row_count} rows &middot;{" "}
                          {msg.duration_ms}ms
                        </summary>
                        <pre className="mt-1 text-xs bg-muted rounded-md p-2 overflow-x-auto border">
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
                <div className="bg-muted rounded-lg px-3 py-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        </ScrollArea>

        {/* Input */}
        <form
          onSubmit={handleSubmit}
          className="border-t p-3 flex items-center gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about providers, claims, risk..."
            disabled={loading}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={loading || !input.trim()}>
            <SendHorizonal className="h-4 w-4" />
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  );
}
