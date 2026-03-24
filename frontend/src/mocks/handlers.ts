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
];
