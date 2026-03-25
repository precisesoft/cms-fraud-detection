import React from 'react';
import { TrendingUp, Map } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { getHeatmap } from '../lib/api';
import type { HeatmapEntry } from '../lib/api';
import { cn } from '../lib/utils';
import { scoreColor } from '../lib/helpers';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/us-atlas@3/states-10m.json';

/**
 * FIPS code → two-letter state abbreviation.
 * The TopoJSON from us-atlas uses FIPS ids (e.g. "06" for California).
 */
const FIPS_TO_ABBR: Record<string, string> = {
  '01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA',
  '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL',
  '13': 'GA', '15': 'HI', '16': 'ID', '17': 'IL', '18': 'IN',
  '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME',
  '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS',
  '29': 'MO', '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH',
  '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND',
  '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA', '44': 'RI',
  '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT',
  '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI',
  '56': 'WY', '72': 'PR',
};

function fillForRisk(avg: number | undefined): string {
  if (avg == null) return '#e2e8f0'; // slate-200 — no data
  if (avg >= 50) return '#f43f5e';   // rose-500
  if (avg >= 35) return '#fb923c';   // orange-400
  if (avg >= 20) return '#facc15';   // yellow-400
  return '#86efac';                   // emerald-300
}

export function RiskMap() {
  const [data, setData] = React.useState<HeatmapEntry[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [tooltip, setTooltip] = React.useState<{ entry: HeatmapEntry; x: number; y: number } | null>(null);

  React.useEffect(() => {
    let active = true;
    getHeatmap()
      .then((r) => { if (active) setData(r.data); })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const byState = React.useMemo(() => {
    const lookup = new globalThis.Map<string, HeatmapEntry>();
    data.forEach((d) => lookup.set(d.state, d));
    return lookup;
  }, [data]);

  const sortedByRisk = React.useMemo(
    () => [...data].sort((a, b) => b.avg_risk_score - a.avg_risk_score),
    [data],
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Risk Map</h1>
          <p className="mt-1 text-sm text-slate-500">Geographic distribution of provider risk scores across states.</p>
        </div>
      </div>

      {loading ? (
        <div role="status" aria-label="Loading risk map" className="flex items-center justify-center py-20">
          <span aria-hidden="true" className="w-6 h-6 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Choropleth Map */}
          <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm relative">
            <h2 className="font-bold text-slate-800 flex items-center gap-2 mb-2">
              <Map className="w-4 h-4 text-indigo-500" /> State Risk Choropleth
            </h2>

            <div role="img" aria-label="United States choropleth map showing average provider risk scores by state">
              <ComposableMap
                projection="geoAlbersUsa"
                projectionConfig={{ scale: 1000 }}
                width={800}
                height={500}
                style={{ width: '100%', height: 'auto' }}
              >
                <Geographies geography={GEO_URL}>
                  {({ geographies }) =>
                    geographies.map((geo) => {
                      const fips = geo.id as string;
                      const abbr = FIPS_TO_ABBR[fips];
                      const entry = abbr ? byState.get(abbr) : undefined;
                      return (
                        <Geography
                          key={geo.rsmKey}
                          geography={geo}
                          fill={fillForRisk(entry?.avg_risk_score)}
                          stroke="#fff"
                          strokeWidth={0.5}
                          style={{
                            default: { outline: 'none' },
                            hover: { outline: 'none', filter: 'brightness(0.96)', cursor: 'default' },
                            pressed: { outline: 'none' },
                          }}
                          onMouseEnter={(evt) => {
                            if (entry) {
                              setTooltip({ entry, x: evt.clientX, y: evt.clientY });
                            }
                          }}
                          onMouseMove={(evt) => {
                            if (entry) {
                              setTooltip({ entry, x: evt.clientX, y: evt.clientY });
                            }
                          }}
                          onMouseLeave={() => setTooltip(null)}
                        />
                      );
                    })
                  }
                </Geographies>
              </ComposableMap>
            </div>

            {/* Floating Tooltip */}
            {tooltip && (
              <div
                className="fixed z-50 pointer-events-none bg-slate-900 text-white rounded-lg px-4 py-3 shadow-xl text-xs"
                style={{ left: tooltip.x + 12, top: tooltip.y - 40 }}
              >
                <p className="font-bold text-sm">{tooltip.entry.state}</p>
                <div className="flex gap-4 mt-1.5 text-slate-300">
                  <span>Providers: <b className="text-white">{tooltip.entry.provider_count}</b></span>
                  <span>Avg Risk: <b className="text-white">{tooltip.entry.avg_risk_score.toFixed(1)}</b></span>
                  <span>Flagged: <b className="text-rose-400">{tooltip.entry.flagged_count}</b></span>
                </div>
              </div>
            )}

            {/* Legend */}
            <div className="flex items-center gap-4 mt-3 text-xs font-bold text-slate-500">
              <div className="flex items-center gap-1"><div className="w-3 h-3 rounded" style={{ background: '#86efac' }} /> Low (&lt;20)</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 rounded" style={{ background: '#facc15' }} /> Moderate (20-35)</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 rounded" style={{ background: '#fb923c' }} /> Elevated (35-50)</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 rounded" style={{ background: '#f43f5e' }} /> High (50+)</div>
              <div className="flex items-center gap-1"><div className="w-3 h-3 rounded" style={{ background: '#e2e8f0' }} /> No data</div>
            </div>
          </div>

          {/* Rankings */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h2 className="font-bold text-slate-800 flex items-center gap-2 mb-4"><TrendingUp className="w-4 h-4 text-rose-500" /> Highest Risk States</h2>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {sortedByRisk.slice(0, 20).map((entry, i) => (
                <Link
                  key={entry.state}
                  to={`/providers?state=${encodeURIComponent(entry.state)}`}
                  className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-black text-slate-600 w-5">{i + 1}.</span>
                    <span className="text-sm font-bold text-slate-800">{entry.state}</span>
                    <span className="text-xs text-slate-600">{entry.provider_count} providers</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">{entry.flagged_count} flagged</span>
                    <span className={cn('text-sm font-bold', scoreColor(entry.avg_risk_score))}>{entry.avg_risk_score.toFixed(1)}</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
