import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GoogleOAuthProvider } from '@react-oauth/google';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Funcionarios from './pages/Funcionarios';
import Viaturas from './pages/Viaturas';
import Quarteis from './pages/Quarteis';
import Login from './pages/Login';
import useAuthStore from './store/authStore';

const queryClient = new QueryClient();

// ID Client fictício para rodar localmente. O usuário precisará colocar o real.
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'SEU_CLIENT_ID_AQUI';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore(state => state.token);
  return token ? <>{children}</> : <Navigate to="/login" />;
};

const App: React.FC = () => {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            
            <Route element={<PrivateRoute><Layout /></PrivateRoute>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/funcionarios" element={<Funcionarios />} />
              <Route path="/viaturas" element={<Viaturas />} />
              <Route path="/quarteis" element={<Quarteis />} />
            </Route>
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </QueryClientProvider>
    </GoogleOAuthProvider>
  );
};

export default App;
