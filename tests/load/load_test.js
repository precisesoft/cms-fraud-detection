/**
 * k6 load test for CMS Fraud Detection API.
 *
 * Usage:
 *   k6 run tests/load/load_test.js
 *   k6 run --env BASE_URL=https://argus.precise-lab.com tests/load/load_test.js
 *
 * Stages: ramp to 50 VUs over 30s, hold 60s, ramp down 10s.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "https://argus.precise-lab.com";

// Custom metrics
const errorRate = new Rate("errors");
const dashboardDuration = new Trend("dashboard_duration", true);
const providersDuration = new Trend("providers_duration", true);
const providerDetailDuration = new Trend("provider_detail_duration", true);
const scoreDuration = new Trend("score_duration", true);
const fairnessDuration = new Trend("fairness_duration", true);

// Sample NPIs for provider detail requests (from the demo dataset)
const SAMPLE_NPIS = [
  "1821387911",
  "1003000126",
  "1003000142",
  "1003000167",
  "1003000175",
];

export const options = {
  stages: [
    { duration: "15s", target: 10 }, // warm up
    { duration: "15s", target: 50 }, // ramp to peak
    { duration: "60s", target: 50 }, // hold at peak
    { duration: "10s", target: 0 }, // ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"], // p95 < 2s
    errors: ["rate<0.05"], // error rate < 5%
  },
};

export default function () {
  const scenario = Math.random();

  if (scenario < 0.3) {
    // 30% — Dashboard (heaviest query, aggregation)
    const res = http.get(`${BASE_URL}/api/dashboard`);
    dashboardDuration.add(res.timings.duration);
    check(res, { "dashboard 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  } else if (scenario < 0.55) {
    // 25% — Provider list with search
    const res = http.get(
      `${BASE_URL}/api/providers?limit=20&offset=0&risk_band=high_risk`,
    );
    providersDuration.add(res.timings.duration);
    check(res, { "providers 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  } else if (scenario < 0.75) {
    // 20% — Provider detail (random NPI)
    const npi = SAMPLE_NPIS[Math.floor(Math.random() * SAMPLE_NPIS.length)];
    const res = http.get(`${BASE_URL}/api/providers/${npi}`);
    providerDetailDuration.add(res.timings.duration);
    check(res, { "provider detail 2xx": (r) => r.status < 300 });
    errorRate.add(res.status >= 300);
  } else if (scenario < 0.9) {
    // 15% — Score endpoint (simulate scoring)
    const payload = JSON.stringify({
      npi: "1821387911",
      hcpcs_cd: "99213",
      place_of_service: "O",
      tot_benes: 150,
      tot_srvcs: 500,
      avg_submitted_charge: 120.0,
      avg_medicare_allowed_amt: 80.0,
      avg_medicare_payment_amt: 65.0,
    });
    const res = http.post(`${BASE_URL}/api/score`, payload, {
      headers: { "Content-Type": "application/json" },
    });
    scoreDuration.add(res.timings.duration);
    check(res, { "score 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  } else {
    // 10% — Fairness endpoint
    const res = http.get(`${BASE_URL}/api/fairness`);
    fairnessDuration.add(res.timings.duration);
    check(res, { "fairness 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  }

  sleep(0.5 + Math.random() * 1.5); // 0.5-2s think time
}
