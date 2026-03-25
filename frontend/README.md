# CMS Fraud Detection — Frontend

> Vite + React 19 + TypeScript + Tailwind CSS v4

## Quick Start

```bash
npm install
npm run dev          # http://localhost:3000
```

## Scripts

| Command                 | Purpose                        |
| ----------------------- | ------------------------------ |
| `npm run dev`           | Development server (port 3000) |
| `npm run build`         | Production build to `dist/`    |
| `npm run preview`       | Preview production build       |
| `npm run lint`          | ESLint check                   |
| `npm test`              | Run tests (Vitest)             |
| `npm run test:coverage` | Tests with coverage report     |

## Stack

- **React 19** + **React Router 7** (SPA, client-side routing)
- **Vite 6** (build tool + HMR dev server)
- **Tailwind CSS v4** (utility-first styling)
- **Recharts 3** (data visualizations)
- **react-simple-maps** (US choropleth heatmap)
- **Lucide React** (icons)
- **Motion** (animations)
- **Vitest** + **Testing Library** + **MSW** (testing)

## Pages

| Route             | Page           | Description                                 |
| ----------------- | -------------- | ------------------------------------------- |
| `/`               | Dashboard      | Aggregate stats, risk distribution, heatmap |
| `/providers`      | Providers      | Provider list with search                   |
| `/providers/:npi` | ProviderDetail | Deep-dive into a single provider            |
| `/claims`         | Claims         | Claims queue                                |
| `/claims/:id`     | ClaimDetail    | Individual claim view                       |
| `/simulate`       | Simulate       | Claims simulator with real-time scoring     |
| `/fairness`       | Fairness       | Fairness metrics dashboard                  |
| `/risk-map`       | RiskMap        | Geographic risk heatmap                     |
| `/investigations` | Investigations | Investigation case list                     |
| `/analytics`      | Analytics      | Analytics view                              |
| `/validation`     | Validation     | Retrospective validation results            |
| `/login`          | Login          | Authentication                              |

## Project Structure

```
frontend/src/
  App.tsx               Route definitions
  main.tsx              Entry point
  index.css             Global styles (Tailwind)
  pages/                Route page components
  components/           Shared components (Layout, AssistantDrawer, EvidenceGraph, ...)
  contexts/             React context providers (AuthContext)
  lib/                  API client, helpers, utilities
  mocks/                MSW handlers for testing
```

## Environment

The frontend connects to the FastAPI backend. In development, configure the API URL:

```bash
# Dev server proxy target
VITE_API_BASE_URL=https://argus.precise-lab.com
```

When running `npm run dev`, API requests stay same-origin and are proxied by Vite
to `VITE_API_BASE_URL`. Production builds use `VITE_API_BASE_URL` directly.

## Docker

```bash
# Build production image (nginx serving static build)
docker build -t cms-fraud-frontend .

# Run
docker run -p 3000:3000 cms-fraud-frontend
```
