import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Chat from './pages/Chat';
import Preprocess from './pages/Preprocess';
import Datasets from './pages/Datasets';
import DatasetMeta from './pages/DatasetMeta';
import PreprocessBackend from './pages/PreprocessBackend';
import ExportTools from './pages/ExportTools';
import { AppLayout } from './components/layout/AppLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/preprocess" element={<Preprocess />} />
          <Route path="/preprocess/backend" element={<PreprocessBackend />} />
          <Route path="/datasets" element={<Datasets />} />
          <Route path="/datasets/meta" element={<DatasetMeta />} />
          <Route path="/datasets/:sourceId/meta" element={<DatasetMeta />} />
          <Route path="/export" element={<ExportTools />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
