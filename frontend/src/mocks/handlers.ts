import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/providers', () => {
    return HttpResponse.json({ data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } });
  }),

  http.get('/api/providers/:npi', ({ params }) => {
    return HttpResponse.json({ npi: params.npi });
  }),

  http.get('/api/cases', () => {
    return HttpResponse.json({ data: [], meta: { total: 0, page: 1, per_page: 20, pages: 0 } });
  }),

  http.post('/api/v2/score', () => {
    return HttpResponse.json({ risk_score: 0, risk_band: 'stable' });
  }),

  http.post('/api/v2/claims/simulate', () => {
    return HttpResponse.json({ risk_score: 0, risk_band: 'stable' });
  }),

  http.get('/health', () => {
    return HttpResponse.json({ status: 'ok' });
  }),

  // Ingest endpoints
  http.get('/api/ingest/sources', () => {
    return HttpResponse.json([
      {
        source_type: 'Part B Service',
        version: '2024',
        uploaded_at: new Date(Date.now() - 30 * 86_400_000).toISOString(),
        row_count: 1_500_000,
      },
      {
        source_type: 'Part B Provider',
        version: '2024',
        uploaded_at: new Date(Date.now() - 30 * 86_400_000).toISOString(),
        row_count: 10_282,
      },
      {
        source_type: 'Enrollment',
        version: 'Q4-2024',
        uploaded_at: new Date(Date.now() - 60 * 86_400_000).toISOString(),
        row_count: 9_800,
      },
      {
        source_type: 'Revocations',
        version: '2025-01',
        uploaded_at: new Date(Date.now() - 10 * 86_400_000).toISOString(),
        row_count: 325,
      },
    ]);
  }),

  http.post('/api/ingest/upload', () => {
    return HttpResponse.json({
      source_type: 'Part B Service',
      version: '2025',
      row_count: 1_600_000,
      warnings: [],
      duplicate_detected: false,
    });
  }),

  http.post('/api/ingest/runs', () => {
    return HttpResponse.json({
      id: 42,
      run_type: 'recalibration',
      status: 'running',
      current_stage: 'ingest',
      progress_pct: 0,
      source_versions: {},
      stage_results: [],
      error_message: null,
      started_at: new Date().toISOString(),
      completed_at: null,
      triggered_by: 'admin_ui',
    });
  }),

  http.get('/api/ingest/runs', () => {
    return HttpResponse.json([
      {
        id: 41,
        run_type: 'recalibration',
        status: 'completed',
        current_stage: null,
        progress_pct: 100,
        source_versions: {},
        stage_results: [
          { stage: 'ingest', status: 'completed', duration_s: 12.5, metrics: { rows: 1500000 }, error: null },
          { stage: 'peer_baselines', status: 'completed', duration_s: 45.2, metrics: {}, error: null },
          { stage: 'z_scores', status: 'completed', duration_s: 22.1, metrics: {}, error: null },
          { stage: 'seed_scoring', status: 'completed', duration_s: 8.3, metrics: {}, error: null },
          { stage: 'provider_profiles', status: 'completed', duration_s: 30.0, metrics: {}, error: null },
          { stage: 'ml_scoring', status: 'completed', duration_s: 55.7, metrics: { providers_scored: 10282 }, error: null },
        ],
        error_message: null,
        started_at: new Date(Date.now() - 3600_000).toISOString(),
        completed_at: new Date(Date.now() - 3400_000).toISOString(),
        triggered_by: 'admin_ui',
      },
    ]);
  }),

  http.get('/api/ingest/runs/:runId', ({ params }) => {
    const id = Number(params.runId);
    return HttpResponse.json({
      id,
      run_type: 'recalibration',
      status: 'completed',
      current_stage: null,
      progress_pct: 100,
      source_versions: {},
      stage_results: [
        { stage: 'ingest', status: 'completed', duration_s: 12.5, metrics: { rows: 1500000 }, error: null },
        { stage: 'peer_baselines', status: 'completed', duration_s: 45.2, metrics: {}, error: null },
        { stage: 'z_scores', status: 'completed', duration_s: 22.1, metrics: {}, error: null },
        { stage: 'seed_scoring', status: 'completed', duration_s: 8.3, metrics: {}, error: null },
        { stage: 'provider_profiles', status: 'completed', duration_s: 30.0, metrics: {}, error: null },
        { stage: 'ml_scoring', status: 'completed', duration_s: 55.7, metrics: { providers_scored: 10282 }, error: null },
      ],
      error_message: null,
      started_at: new Date(Date.now() - 3600_000).toISOString(),
      completed_at: new Date(Date.now() - 3400_000).toISOString(),
      triggered_by: 'admin_ui',
    });
  }),
];
