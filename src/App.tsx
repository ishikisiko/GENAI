import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import CaseCreation from "./pages/CaseCreation";
import GlobalSourcesPage from "./pages/GlobalSourcesPage";
import DocumentsPage from "./pages/DocumentsPage";
import GroundingPage from "./pages/GroundingPage";
import SimulationPage from "./pages/SimulationPage";
import ComparisonPage from "./pages/ComparisonPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/cases/new" element={<Layout><CaseCreation /></Layout>} />
        <Route path="/sources" element={<Layout><GlobalSourcesPage /></Layout>} />
        <Route path="/cases/:caseId/documents" element={<Layout><DocumentsPage /></Layout>} />
        <Route path="/cases/:caseId/grounding" element={<Layout><GroundingPage /></Layout>} />
        <Route path="/cases/:caseId/simulation" element={<Layout><SimulationPage /></Layout>} />
        <Route path="/cases/:caseId/comparison" element={<Layout><ComparisonPage /></Layout>} />
      </Routes>
    </BrowserRouter>
  );
}
