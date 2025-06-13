import { useState, createContext } from 'react';
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { AuthProvider } from './components/auth/AuthContext';
import PrivateRoute from './components/auth/PrivateRoute/PrivateRoute';
import Login from './components/auth/Login/Login';
import Reset from './components/auth/Reset/Reset';
import Dashboard from './components/dashboard/Dashboard';
import DeviceDetail from './components/DeviceDetail';
import DeviceList from './components/DeviceList';
import DeviceDetailGraph from './components/DeviceDetailGraph';
import DeviceSocket from './components/DeviceSocket';

import Layout from './components/layout/Layout'; // nouveau composant

const queryClient = new QueryClient();
export const MyContext = createContext();

function App() {
  const [isHideSidebarAndHeader, setIsHideSidebarAndHeader] = useState(true);
  const [isClick, setIsClick] = useState(1);
  const [toggleSidebar, setToggleSidebar] = useState(true);

  const values = {
    isHideSidebarAndHeader,
    setIsHideSidebarAndHeader,
    isClick,
    setIsClick,
    toggleSidebar,
    setToggleSidebar,
  };

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <MyContext.Provider value={values}>
            <Routes>
              {/* Route publique */}
              <Route path="/connexion" element={<Login />} />
              <Route path="/reset" element={<Reset />} />
              <Route path="/" element={<Navigate to="/connexion" />} />
              <Route path="*" element={<div>Page non trouvée</div>} />

              {/* Routes privées avec layout */}
              <Route element={<Layout />}>
                <Route path="/dash" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
                <Route path="/device/:id" element={<DeviceDetail />} />
                <Route path="/appareils" element={<PrivateRoute><DeviceList /></PrivateRoute>} />
                <Route path="/appareils_chart/:id" element={<DeviceDetailGraph />} />
                <Route path="/devicesocket/:id" element={<DeviceSocket />} />
              </Route>
            </Routes>
          </MyContext.Provider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
