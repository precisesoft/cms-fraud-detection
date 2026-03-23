import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Simulate } from './pages/Simulate';
import { Providers } from './pages/Providers';
import { ProviderDetail } from './pages/ProviderDetail';
import { Claims } from './pages/Claims';
import { ClaimDetail } from './pages/ClaimDetail';
import { RiskMap } from './pages/RiskMap';
import { Fairness } from './pages/Fairness';
import { Analytics } from './pages/Analytics';
import { Investigations } from './pages/Investigations';
import { InvestigationDetail } from './pages/InvestigationDetail';
import { Validation } from './pages/Validation';

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
