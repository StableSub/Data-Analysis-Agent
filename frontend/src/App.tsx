import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Chat from './pages/Chat';
import Preprocess from './pages/Preprocess';
import Datasets from './pages/Datasets';
import { AppLayout } from './components/layout/AppLayout';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/preprocess" element={<Preprocess />} />
          <Route path="/datasets" element={<Datasets />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
