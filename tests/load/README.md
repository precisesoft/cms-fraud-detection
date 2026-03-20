# Load Testing

## Prerequisites

Install [k6](https://k6.io/docs/get-started/installation/):

```bash
brew install k6
```

## Run

```bash
# Against live deployment
k6 run tests/load/load_test.js

# Against local dev server
k6 run --env BASE_URL=http://localhost:8000 tests/load/load_test.js
```

## Test Profile

- Ramp: 0 -> 10 VUs (15s) -> 50 VUs (15s) -> hold 50 VUs (60s) -> 0 (10s)
- Total duration: ~100 seconds
- Endpoint mix: dashboard 30%, providers 25%, provider detail 20%, score 15%, fairness 10%

## Thresholds

- p95 response time < 2000ms
- Error rate < 5%
