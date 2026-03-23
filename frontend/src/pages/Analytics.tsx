import React from 'react';
import { MessageSquareMore, Send, Database, BarChart3, Table } from 'lucide-react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { chat } from '../lib/api';
import type { ChatMessage, ChatResponse, ChartSpec } from '../lib/api';
import { cn } from '../lib/utils';

const CHART_COLORS = ['#6366f1', '#f43f5e', '#22c55e', '#eab308', '#3b82f6', '#a855f7', '#14b8a6', '#f97316'];

function ChartRenderer({ spec }: { spec: ChartSpec }) {
  if (spec.type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey={spec.xKey ?? spec.nameKey ?? 'name'} tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
          <Bar dataKey={spec.yKey ?? spec.valueKey ?? 'value'} fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  if (spec.type === 'line') {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey={spec.xKey ?? 'name'} tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
          <Line type="monotone" dataKey={spec.yKey ?? 'value'} stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    );
  }
  if (spec.type === 'pie') {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={spec.data} dataKey={spec.valueKey ?? 'value'} nameKey={spec.nameKey ?? 'name'} cx="50%" cy="50%" outerRadius={100} label>
            {spec.data.map((_: unknown, i: number) => (<Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />))}
          </Pie>
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  return null;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  response?: ChatResponse;
}

const SUGGESTIONS = [
  'Which 10 providers have the highest total estimated payments?',
  'How many providers are flagged as high risk by state?',
  'What are the most common HCPCS codes among high-risk providers?',
  'Show me the average risk score by provider type',
  'Compare the top 5 specialties by flagging rate',
];

export function Analytics() {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const chatHistory = React.useRef<ChatMessage[]>([]);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = text ?? input.trim();
    if (!msg || loading) return;
    setInput('');
    const userMsg: Message = { role: 'user', content: msg };
    setMessages((prev) => [...prev, userMsg]);
    chatHistory.current.push({ role: 'user', content: msg });
    setLoading(true);
    try {
      const res = await chat(msg, chatHistory.current.slice(0, -1));
      const assistantMsg: Message = { role: 'assistant', content: res.answer, response: res };
      setMessages((prev) => [...prev, assistantMsg]);
      chatHistory.current.push({ role: 'assistant', content: res.answer });
    } catch (err) {
      const errMsg: Message = { role: 'assistant', content: err instanceof Error ? `Error: ${err.message}` : 'Something went wrong.' };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] animate-in fade-in duration-500">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
          <p className="text-sm text-slate-500">Ask questions about the data in natural language. Powered by text-to-SQL.</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-6 pb-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center mb-4">
              <MessageSquareMore className="w-8 h-8 text-indigo-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 mb-2">Ask anything about the data</h3>
            <p className="text-sm text-slate-500 mb-6 text-center max-w-md">I can query the database for you. Try one of these:</p>
            <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => handleSend(s)} className="px-4 py-2 bg-white border border-slate-200 text-sm text-slate-700 font-medium rounded-xl hover:border-indigo-300 hover:bg-indigo-50/50 transition-all">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={cn('max-w-3xl', msg.role === 'user' ? 'ml-auto' : '')}>
            {msg.role === 'user' ? (
              <div className="bg-indigo-600 text-white px-5 py-3 rounded-2xl rounded-tr-md text-sm font-medium">{msg.content}</div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white px-5 py-4 rounded-2xl rounded-tl-md border border-slate-200 shadow-sm">
                  <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>

                {msg.response?.sql && (
                  <div className="bg-slate-900 text-slate-200 p-4 rounded-xl text-xs font-mono overflow-x-auto">
                    <div className="flex items-center gap-2 text-indigo-400 mb-2"><Database className="w-3.5 h-3.5" /> SQL Query ({msg.response.duration_ms}ms)</div>
                    <pre>{msg.response.sql}</pre>
                  </div>
                )}

                {msg.response?.chart_spec && (
                  <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2"><BarChart3 className="w-3.5 h-3.5" /> {msg.response.chart_spec.title}</p>
                    <ChartRenderer spec={msg.response.chart_spec} />
                  </div>
                )}

                {msg.response && msg.response.rows.length > 0 && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500">
                      <Table className="w-3.5 h-3.5" /> {msg.response.row_count} rows
                    </div>
                    <div className="overflow-x-auto max-h-64">
                      <table className="min-w-full divide-y divide-slate-200 text-xs">
                        <thead className="bg-slate-50/80 sticky top-0">
                          <tr>
                            {msg.response.columns.map((col) => (
                              <th key={col} className="px-4 py-2 text-left font-bold text-slate-500 uppercase tracking-wider">{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {msg.response.rows.slice(0, 50).map((row, ri) => (
                            <tr key={ri} className="hover:bg-slate-50/60">
                              {msg.response!.columns.map((col) => (
                                <td key={col} className="px-4 py-2 text-slate-700">{String(row[col] ?? '')}</td>
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

      {/* Input */}
      <div className="border-t border-slate-200 pt-4">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex items-center gap-3">
          <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about the data..." disabled={loading} className="flex-1 px-5 py-3 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 transition-all disabled:opacity-50" />
          <button type="submit" disabled={loading || !input.trim()} className="p-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
