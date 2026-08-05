import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { ABBenchmarkPage } from './routes/ABBenchmarkPage'
import { AnnInspector } from './routes/AnnInspector'
import { DashboardHome } from './routes/DashboardHome'
import { DatasetExplorer } from './routes/DatasetExplorer'
import { EvaluationPage } from './routes/EvaluationPage'
import { MetricsPage } from './routes/MetricsPage'
import { PipelineComparison } from './routes/PipelineComparison'
import { PipelineExplorer } from './routes/PipelineExplorer'
import { Playground } from './routes/Playground'
import { SettingsPage } from './routes/SettingsPage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardHome />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/pipeline" element={<PipelineExplorer />} />
        <Route path="/pipeline-comparison" element={<PipelineComparison />} />
        <Route path="/ann-inspector" element={<AnnInspector />} />
        <Route path="/dataset" element={<DatasetExplorer />} />
        <Route path="/dataset/tickets/:ticketId" element={<DatasetExplorer />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/ab-benchmark" element={<ABBenchmarkPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppShell>
  )
}

export default App
