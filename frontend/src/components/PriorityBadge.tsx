import { cn } from '../lib/utils';

export function PriorityBadge({ label, size = 'md' }: { label: string | null | undefined; size?: 'sm' | 'md' }) {
  const display = label ?? 'Unknown';
  const l = (label ?? '').toLowerCase();
  const color =
    l.includes('high') || l.includes('critical')
      ? 'bg-rose-100 text-rose-700'
      : l.includes('review') || l.includes('medium')
        ? 'bg-amber-100 text-amber-700'
        : 'bg-emerald-100 text-emerald-700';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-bold uppercase tracking-wider',
        color,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-[11px]',
      )}
    >
      {display}
    </span>
  );
}
