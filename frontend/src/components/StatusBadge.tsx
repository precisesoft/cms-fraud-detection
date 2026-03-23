import { cn } from '../lib/utils';
import { riskBandLabel, riskBandColor } from '../lib/helpers';
import type { RiskBand } from '../lib/api';

export function StatusBadge({ band, label, size = 'md' }: { band?: RiskBand | null; label?: string; size?: 'sm' | 'md' }) {
  const display = label ?? riskBandLabel(band);
  const colors = riskBandColor(band);
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-bold uppercase tracking-wider',
        colors.bg,
        colors.text,
        size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-[11px]',
      )}
    >
      {display}
    </span>
  );
}
