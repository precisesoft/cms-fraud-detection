import { lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';

const Dashboard = lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const Simulate = lazy(() => import('./pages/Simulate').then((m) => ({ default: m.Simulate })));
const Providers = lazy(() => import('./pages/Providers').then((m) => ({ default: m.Providers })));
const ProviderDetail = lazy(() => import('./pages/ProviderDetail').then((m) => ({ default: m.ProviderDetail })));
const Claims = lazy(() => import('./pages/Claims').then((m) => ({ default: m.Claims })));
const ClaimDetail = lazy(() => import('./pages/ClaimDetail').then((m) => ({ default: m.ClaimDetail })));
const Investigations = lazy(() => import('./pages/Investigations').then((m) => ({ default: m.Investigations })));
const InvestigationDetail = lazy(() =>
  import('./pages/InvestigationDetail').then((m) => ({ default: m.InvestigationDetail })),
);
const RiskMap = lazy(() => import('./pages/RiskMap').then((m) => ({ default: m.RiskMap })));
const Fairness = lazy(() => import('./pages/Fairness').then((m) => ({ default: m.Fairness })));
const Analytics = lazy(() => import('./pages/Analytics').then((m) => ({ default: m.Analytics })));
const Validation = lazy(() => import('./pages/Validation').then((m) => ({ default: m.Validation })));

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="simulate" element={<Simulate />} />
          <Route path="providers" element={<Providers />} />
          <Route path="providers/:npi" element={<ProviderDetail />} />
          <Route path="claims" element={<Claims />} />
          <Route path="claims/:caseId" element={<ClaimDetail />} />
          <Route path="investigations" element={<Investigations />} />
          <Route path="investigations/:caseId" element={<InvestigationDetail />} />
          <Route path="risk-map" element={<RiskMap />} />
          <Route path="fairness" element={<Fairness />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="validation" element={<Validation />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
