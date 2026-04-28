import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import CaseCreation from "./pages/CaseCreation";
import GlobalSourcesPage from "./pages/GlobalSourcesPage";
import DocumentsPage from "./pages/DocumentsPage";
import SourceDiscoverySetupPage from "./pages/SourceDiscoverySetupPage";
import CandidateSourcesReviewPage from "./pages/CandidateSourcesReviewPage";
import EvidencePackPreviewPage from "./pages/EvidencePackPreviewPage";
import GroundingPage from "./pages/GroundingPage";
import SimulationPage from "./pages/SimulationPage";
import ComparisonPage from "./pages/ComparisonPage";
import { I18nProvider } from "./lib/i18n";

export default function App() {
  return (
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><Dashboard /></Layout>} />
          <Route path="/cases/new" element={<Layout><CaseCreation /></Layout>} />
          <Route path="/sources" element={<Layout><GlobalSourcesPage /></Layout>} />
          <Route path="/cases/:caseId/documents" element={<Layout><DocumentsPage /></Layout>} />
          <Route path="/cases/:caseId/source-discovery" element={<Layout><SourceDiscoverySetupPage /></Layout>} />
          <Route path="/cases/:caseId/source-discovery/:jobId/review" element={<Layout><CandidateSourcesReviewPage /></Layout>} />
          <Route path="/cases/:caseId/evidence-packs/:packId" element={<Layout><EvidencePackPreviewPage /></Layout>} />
          <Route path="/cases/:caseId/grounding" element={<Layout><GroundingPage /></Layout>} />
          <Route path="/cases/:caseId/simulation" element={<Layout><SimulationPage /></Layout>} />
          <Route path="/cases/:caseId/comparison" element={<Layout><ComparisonPage /></Layout>} />
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  );
}
