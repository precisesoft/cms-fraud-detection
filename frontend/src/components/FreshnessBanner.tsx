import React from 'react';
import { Link } from 'react-router-dom';
import { RefreshCw, Upload } from 'lucide-react';
import { getIngestStatus } from '../lib/api';
import type { IngestStatus } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 30) return `${diffDays} days ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths === 1) return '1 month ago';
  if (diffMonths < 12) return `${diffMonths} months ago`;
  const diffYears = Math.floor(diffDays / 365);
  return diffYears === 1 ? '1 year ago' : `${diffYears} years ago`;
}

function absoluteDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function daysSince(dateStr: string): number {
  const diffMs = Date.now() - new Date(dateStr).getTime();
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
}

type DotColor = 'green' | 'amber' | 'red';

function freshnessColor(lastRecalibration: IngestStatus['last_recalibration']): DotColor {
  if (!lastRecalibration) return 'red';
  const days = daysSince(lastRecalibration.completed_at);
  if (days > 180) return 'red';
  if (days > 90) return 'amber';
  return 'green';
}

const DOT_CLASSES: Record<DotColor, string> = {
  green: 'bg-emerald-500',
  amber: 'bg-amber-500',
  red: 'bg-rose-500',
};

const DOT_LABELS: Record<DotColor, string> = {
  green: 'Fresh',
  amber: 'Approaching staleness',
  red: 'Stale',
};

export function FreshnessBanner() {
  const { user } = useAuth();
  const [status, setStatus] = React.useState<IngestStatus | null>(null);

  React.useEffect(() => {
    getIngestStatus()
      .then(setStatus)
      .catch(() => {
        // Graceful fallback: endpoint not yet deployed or unavailable
        setStatus(null);
      });
  }, []);

  if (!status) return null;

  const dotColor = freshnessColor(status.last_recalibration);
  const isAdmin = user?.role === 'admin';

  return (
    <div
      aria-label="Data freshness banner"
      className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3"
    >
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm text-slate-600 min-w-0">
        {/* Freshness dot */}
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full ${DOT_CLASSES[dotColor]}`}
            aria-label={DOT_LABELS[dotColor]}
            title={DOT_LABELS[dotColor]}
          />
          <span className="font-semibold text-slate-700">Data</span>
        </div>

        {/* Sources */}
        {status.sources.length > 0 && (
          <span className="truncate">
            {status.sources.map((s) => `${s.type} ${s.version}`).join(' · ')}
          </span>
        )}

        {/* Recalibration info */}
        {status.last_recalibration ? (
          <span className="shrink-0">
            Scores recalibrated:{' '}
            <span className="font-medium text-slate-800">
              {absoluteDate(status.last_recalibration.completed_at)}
            </span>
            {' '}
            <span className="text-slate-400">
              ({relativeTime(status.last_recalibration.completed_at)})
            </span>
          </span>
        ) : (
          <span className="text-rose-600 font-medium shrink-0">No recalibration on record</span>
        )}

        {/* Provider count */}
        <span className="shrink-0 text-slate-500">
          {status.providers_in_system.toLocaleString()} providers
        </span>
      </div>

      {/* Admin actions */}
      {isAdmin && (
        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/data"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
            aria-label="Recalibrate scores"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Recalibrate
          </Link>
          <Link
            to="/data"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
            aria-label="Upload data"
          >
            <Upload className="w-3.5 h-3.5" />
            Upload Data
          </Link>
        </div>
      )}
    </div>
  );
}
