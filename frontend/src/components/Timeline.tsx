import type { CaseActionRecord } from '../lib/api';

export function Timeline({ events, emptyText = 'No events yet.' }: { events: CaseActionRecord[]; emptyText?: string }) {
  if (!events.length) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <div key={event.id} className="border-l-2 border-indigo-100 pl-4">
          <p className="text-sm font-semibold text-slate-900">
            {event.action} — Case {event.case_id}
          </p>
          {event.notes && <p className="mt-1 text-sm text-slate-500">{event.notes}</p>}
          <p className="mt-1 text-xs text-slate-400">
            {event.analyst_id} · {new Date(event.created_at).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}
