import React from 'react';
import { cn } from '../lib/utils';
import { Info } from 'lucide-react';

/** Small tooltip that says "Mocked" to indicate data is not from a live API */
export function MockedBadge({ className, label }: { className?: string; label?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-600',
        className,
      )}
      title={label ?? 'This data is mocked and not fetched from a live API'}
    >
      <Info className="w-3 h-3" />
      Mocked
    </span>
  );
}
