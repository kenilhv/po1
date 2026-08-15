import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Login from './pages/Login';
import APDashboard from './pages/APDashboard';
import CFODashboard from './pages/CFODashboard';
import { ProtectedRoute } from './router';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route
          path="/ap"
          element={
            <ProtectedRoute requiredRole="ap">
              <APDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/cfo"
          element={
            <ProtectedRoute requiredRole="cfo">
              <CFODashboard />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
