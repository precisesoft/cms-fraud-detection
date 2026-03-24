import React from "react";
import { AnimatePresence, motion } from "motion/react";
import { Bot, Send, Sparkles, X } from "lucide-react";
import { chat } from "../lib/api";
import type { ChatMessage, ChatResponse } from "../lib/api";

interface AssistantDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  context: { type: string; entityId: string; label: string };
}

const suggestedPrompts: Record<string, string[]> = {
  provider: [
    "What are the top risk signals for this provider?",
    "How does this provider compare to peers?",
    "Show the highest-risk service lines for this provider",
  ],
  claim: [
    "Why was this case flagged?",
    "What peer comparison data exists for this case?",
    "Show related high-risk cases for this provider",
  ],
  investigation: [
    "Summarize the evidence for this investigation",
    "What other cases should be reviewed?",
    "Show the risk trend for this provider",
  ],
  default: [
    "Show the top 10 high risk providers",
    "What states have the highest risk concentration?",
    "How many providers are flagged as high risk?",
  ],
};

export function AssistantDrawer({
  isOpen,
  onClose,
  context,
}: AssistantDrawerProps) {
  const [input, setInput] = React.useState("");
  const [messages, setMessages] = React.useState<
    Array<{
      id: string;
      role: "user" | "assistant";
      content: string;
      data?: ChatResponse;
    }>
  >([]);
  const [loading, setLoading] = React.useState(false);
  const [history, setHistory] = React.useState<ChatMessage[]>([]);
  const msgIdRef = React.useRef(0);
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);
  const drawerRef = React.useRef<HTMLElement>(null);
  const nextId = () => `msg-${++msgIdRef.current}`;

  const prompts = suggestedPrompts[context.type] ?? suggestedPrompts.default;

  React.useEffect(() => {
    if (isOpen) textareaRef.current?.focus();
  }, [isOpen]);

  const trapFocus = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
      return;
    }
    if (e.key !== "Tab" || !drawerRef.current) return;
    const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
      'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])',
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  const handleSend = async (prompt?: string) => {
    const content = (prompt ?? input).trim();
    if (!content || loading) return;

    const userMsg = { id: nextId(), role: "user" as const, content };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await chat(content, history);
      const assistantMsg = {
        id: nextId(),
        role: "assistant" as const,
        content: response.answer,
        data: response,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setHistory((prev) => [
        ...prev,
        { role: "user", content },
        { role: "assistant", content: response.answer },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "assistant",
          content: err instanceof Error ? err.message : "Request failed.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setHistory([]);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-slate-900/20 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.aside
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Investigation Assistant"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 24, stiffness: 220 }}
            className="fixed inset-y-0 right-0 z-50 w-full max-w-xl border-l border-slate-200 bg-white shadow-2xl"
            onKeyDown={trapFocus}
          >
            <div className="flex h-full flex-col">
              {/* Header */}
              <div className="border-b border-slate-100 px-6 py-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600">
                        <Bot className="h-4 w-4" />
                      </div>
                      <div>
                        <h2 className="font-bold text-slate-900">
                          Investigation Assistant
                        </h2>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Context: {context.type} · {context.label}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3 text-xs text-indigo-900">
                      Powered by text-to-SQL. Ask questions about providers,
                      claims, risk scores, and fairness.
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    aria-label="Close assistant"
                    className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
                {!messages.length && (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
                    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white text-indigo-500 shadow-sm">
                      <Sparkles className="h-5 w-5" />
                    </div>
                    <h3 className="mt-4 text-base font-bold text-slate-900">
                      Ask about this {context.type}
                    </h3>
                    <p className="mt-2 text-sm text-slate-500">
                      Questions are answered via text-to-SQL against the backend
                      database.
                    </p>
                  </div>
                )}

                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={
                      msg.role === "user"
                        ? "flex justify-end"
                        : "flex justify-start"
                    }
                  >
                    <div
                      className={
                        msg.role === "user"
                          ? "max-w-[85%] rounded-2xl bg-indigo-600 px-4 py-3 text-white"
                          : "max-w-[92%] rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm"
                      }
                    >
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {msg.content}
                      </p>
                      {msg.data?.sql && (
                        <div className="mt-3 rounded-lg bg-slate-50 border border-slate-200 p-3">
                          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">
                            SQL
                          </p>
                          <code className="text-xs text-slate-600 whitespace-pre-wrap break-all">
                            {msg.data.sql}
                          </code>
                        </div>
                      )}
                      {msg.data?.rows &&
                        msg.data.rows.length > 0 &&
                        msg.data.columns.length > 0 && (
                          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
                            <table className="min-w-full divide-y divide-slate-200 text-xs">
                              <thead className="bg-slate-50">
                                <tr>
                                  {msg.data.columns.map((col) => (
                                    <th
                                      scope="col"
                                      key={col}
                                      className="px-3 py-2 text-left font-bold text-slate-500 uppercase tracking-wider"
                                    >
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-100">
                                {msg.data.rows.slice(0, 10).map((row, ri) => (
                                  <tr key={ri}>
                                    {msg.data!.columns.map((col) => (
                                      <td
                                        key={col}
                                        className="px-3 py-2 text-slate-700"
                                      >
                                        {String(row[col] ?? "")}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {msg.data.rows.length > 10 && (
                              <p className="px-3 py-2 text-xs text-slate-400">
                                Showing 10 of {msg.data.rows.length} rows
                              </p>
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <div className="w-4 h-4 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
                        Thinking...
                      </div>
                    </div>
                  </div>
                )}

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                    Suggested Prompts
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {prompts.map((prompt) => (
                      <button
                        key={prompt}
                        onClick={() => void handleSend(prompt)}
                        className="rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Input */}
              <div className="border-t border-slate-100 px-6 py-4 space-y-3">
                {messages.length > 0 && (
                  <button
                    onClick={handleClear}
                    className="text-xs font-semibold text-slate-500 hover:text-slate-700"
                  >
                    Clear Thread
                  </button>
                )}
                <div className="flex items-end gap-3">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        void handleSend();
                      }
                    }}
                    rows={2}
                    placeholder={`Ask about this ${context.type}...`}
                    className="min-h-[56px] flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                  <button
                    onClick={() => void handleSend()}
                    disabled={loading}
                    className="inline-flex h-12 items-center justify-center rounded-xl bg-indigo-600 px-4 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
