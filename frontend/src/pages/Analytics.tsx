import React from "react";
import {
  MessageSquareMore,
  Send,
  Database,
  BarChart3,
  Table,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { chat } from "../lib/api";
import type { ChatMessage, ChatResponse, ChartSpec } from "../lib/api";
import { cn } from "../lib/utils";
import { InfoButton } from "../components/InfoButton";

const CHART_COLORS = [
  "#6366f1",
  "#f43f5e",
  "#22c55e",
  "#eab308",
  "#3b82f6",
  "#a855f7",
  "#14b8a6",
  "#f97316",
];

function ChartRenderer({ spec }: { spec: ChartSpec }) {
  if (spec.type === "bar") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey={spec.xKey ?? spec.nameKey ?? "name"}
            tick={{ fontSize: 10, fill: "#64748b" }}
          />
          <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e2e8f0",
            }}
          />
          <Bar
            dataKey={spec.yKey ?? spec.valueKey ?? "value"}
            fill="#6366f1"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (spec.type === "line") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey={spec.xKey ?? "name"}
            tick={{ fontSize: 10, fill: "#64748b" }}
          />
          <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e2e8f0",
            }}
          />
          <Line
            type="monotone"
            dataKey={spec.yKey ?? "value"}
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (spec.type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={spec.data}
            dataKey={spec.valueKey ?? "value"}
            nameKey={spec.nameKey ?? "name"}
            cx="50%"
            cy="50%"
            outerRadius={100}
            label
          >
            {spec.data.map((_: unknown, i: number) => (
              <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
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
    );
  }
  return null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

const SUGGESTIONS = [
  "Which 10 providers have the highest total estimated payments?",
  "How many providers are flagged as high risk by state?",
  "What are the most common HCPCS codes among high-risk providers?",
  "Show me the average risk score by provider type",
  "Compare the top 5 specialties by flagging rate",
];

export function Analytics() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const chatHistory = React.useRef<ChatMessage[]>([]);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const msgIdRef = React.useRef(0);
  const nextMsgId = () => `analytics-msg-${++msgIdRef.current}`;

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = text ?? input.trim();
    if (!msg || loading) return;
    setInput("");
    const userMsg: Message = { id: nextMsgId(), role: "user", content: msg };
    setMessages((prev) => [...prev, userMsg]);
    chatHistory.current.push({ role: "user", content: msg });
    setLoading(true);
    try {
      const res = await chat(msg, chatHistory.current.slice(0, -1));
      const assistantMsg: Message = {
        id: nextMsgId(),
        role: "assistant",
        content: res.answer,
        response: res,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      chatHistory.current.push({ role: "assistant", content: res.answer });
    } catch (err) {
      const errMsg: Message = {
        id: nextMsgId(),
        role: "assistant",
        content:
          err instanceof Error
            ? `Error: ${err.message}`
            : "Something went wrong.",
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-9rem)] flex-col animate-in fade-in duration-500">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
            <InfoButton title="AI-Powered Analytics">Natural language analytics powered by text-to-SQL. Type questions about the data in plain English — the system converts your question to a SQL query, executes it against the database, and returns results with auto-generated charts and tables. Powered by Claude on AWS Bedrock.</InfoButton>
          </div>
          <p className="text-sm text-slate-500">
            Ask questions about the data in natural language. Powered by
            text-to-SQL.
          </p>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex-1 overflow-y-auto p-6">
          <div className="space-y-6">
            {messages.length === 0 && (
              <div className="flex min-h-[24rem] flex-col items-center justify-center px-4 py-8 text-center">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-50">
                  <MessageSquareMore className="w-8 h-8 text-indigo-400" />
                </div>
                <h3 className="mb-2 text-lg font-bold text-slate-800">
                  Ask anything about the data
                </h3>
                <p className="mb-6 max-w-md text-sm text-slate-500">
                  I can query the database for you. Try one of these:
                </p>
                <div className="flex max-w-2xl flex-wrap justify-center gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSend(s)}
                      className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-all hover:border-indigo-300 hover:bg-indigo-50/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn("max-w-3xl", msg.role === "user" ? "ml-auto" : "")}
              >
                {msg.role === "user" ? (
                  <div className="rounded-2xl rounded-tr-md bg-indigo-600 px-5 py-3 text-sm font-medium text-white">
                    {msg.content}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-2xl rounded-tl-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
                      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                        {msg.content}
                      </p>
                    </div>

                    {msg.response?.sql && (
                      <div className="overflow-x-auto rounded-xl bg-slate-900 p-4 text-xs font-mono text-slate-200">
                        <div className="mb-2 flex items-center gap-2 text-indigo-400">
                          <Database className="w-3.5 h-3.5" /> SQL Query (
                          {msg.response.duration_ms}ms)
                        </div>
                        <pre>{msg.response.sql}</pre>
                      </div>
                    )}

                    {msg.response?.chart_spec && (
                      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                        <p className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
                          <BarChart3 className="w-3.5 h-3.5" />
                          {msg.response.chart_spec.title}
                        </p>
                        <ChartRenderer spec={msg.response.chart_spec} />
                      </div>
                    )}

                    {msg.response && msg.response.rows.length > 0 && (
                      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                        <div className="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-bold text-slate-500">
                          <Table className="w-3.5 h-3.5" /> {msg.response.row_count} rows
                        </div>
                        <div className="max-h-64 overflow-x-auto">
                          <table className="min-w-full divide-y divide-slate-200 text-xs">
                            <thead className="sticky top-0 bg-slate-50/80">
                              <tr>
                                {msg.response.columns.map((col) => (
                                  <th
                                    scope="col"
                                    key={col}
                                    className="px-4 py-2 text-left font-bold text-slate-500 uppercase tracking-wider"
                                  >
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                              {msg.response.rows.slice(0, 50).map((row, ri) => (
                                <tr key={ri} className="hover:bg-slate-50/60">
                                  {msg.response.columns.map((col) => (
                                    <td
                                      key={col}
                                      className="px-4 py-2 text-slate-700"
                                    >
                                      {String(row[col] ?? "")}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <span className="w-4 h-4 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                Thinking...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="border-t border-slate-200 bg-white p-4 sm:p-5">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-3"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about the data..."
              aria-label="Ask a question about the data"
              disabled={loading}
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-5 py-3 text-sm transition-all focus:border-indigo-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send analytics question"
              className="rounded-xl bg-indigo-600 p-3 text-white shadow-sm transition-all hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
