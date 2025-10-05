import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/authContext'
import { RealtimeProvider } from './store/realtimeContext'
import ProtectedRoute from './routes/ProtectedRoute'
import Login from './auth/Login'
import ForgotPassword from './auth/ForgotPassword'
import ResetPassword from './auth/ResetPassword'
import AdminActivation from './auth/AdminActivation'
import AdminDashboard from './dashboards/AdminDashboard'
import SuperAdminDashboard from './dashboards/SuperAdminDashboard'
import ClientDashboard from './dashboards/ClientDashboard'
import UserManagement from './pages/Users/UserManagement'
import SiteManagement from './pages/sites/SiteManagement'
import DeviceManagement from './pages/Devices/DeviceManagement'
import DeviceConfigurationPage from './pages/Protections/DeviceConfigurationPage' // <-- NOUVEL IMPORT
import AlertsPage from './pages/Alerts/AlertsPage' // <-- NOUVEL IMPORT POUR ALERTES
import NotFound from './pages/NotFound'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <RealtimeProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Routes publiques */}
            <Route path="/login" element={<Login />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/activer-admin/:token" element={<AdminActivation />} />
            <Route path="/activer-utilisateur/:token" element={<AdminActivation />} />
            
            {/* Routes protégées */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardRouter />
                </ProtectedRoute>
              }
            />
            
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <AdminOrClientRoute>
                    <UserManagement />
                  </AdminOrClientRoute>
                </ProtectedRoute>
              }
            />

            <Route
              path="/sites"
              element={
                <ProtectedRoute>
                  <AdminOrClientRoute>
                    <SiteManagement />
                  </AdminOrClientRoute>
                </ProtectedRoute>
              }
            />
            
            <Route
                path="/devices"
                element={
                  <ProtectedRoute>
                    <AdminOrClientRoute>
                      <DeviceManagement />
                    </AdminOrClientRoute>
                  </ProtectedRoute>
                }
              />

            {/* Nouvelle route pour la page de configuration d'appareil */}
            <Route
                path="/devices/config/:deviceId" // <-- NOUVELLE ROUTE AVEC PARAMÈTRE
                element={
                  <ProtectedRoute>
                    <AdminOrClientRoute> {/* Protégée par rôle aussi */}
                      <DeviceConfigurationPage />
                    </AdminOrClientRoute>
                  </ProtectedRoute>
                }
              />
              
            {/* Nouvelle route pour la page des alertes */}
            <Route
                path="/alertes"
                element={
                  <ProtectedRoute>
                    <AdminOrSuperAdminRoute>
                      <AlertsPage />
                    </AdminOrSuperAdminRoute>
                  </ProtectedRoute>
                }
              />
              

            {/* Redirection par défaut */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </Router>
      </RealtimeProvider>
    </AuthProvider>
  )
}

// Composant pour router vers le bon dashboard selon le rôle
const DashboardRouter = () => {
  const { user, isSuperadmin, isAdmin, isClient } = useAuth()

  if (isSuperadmin()) {
    return <SuperAdminDashboard />
  } else if (isAdmin()) {
    return <AdminDashboard />
  } else if (isClient()) {
    return <ClientDashboard />
  }

  return <Navigate to="/login" replace />
}

// Composant pour protéger les routes admin
const AdminOrClientRoute = ({ children }) => {
  const { isAdmin, isSuperadmin, isClient } = useAuth()
  
  // Cette route autorise les Superadmin, Admin et Client.
  // Si vous voulez restreindre la page de configuration d'appareil à certains rôles seulement,
  // vous devrez ajuster cette logique ou créer un nouveau composant de protection de route.
  if (isAdmin() || isSuperadmin() || isClient()) {
    return children
  }
  
  return <Navigate to="/dashboard" replace />
}

// Composant pour protéger les routes accessibles uniquement aux Superadmin et Admin
const AdminOrSuperAdminRoute = ({ children }) => {
  const { isAdmin, isSuperadmin } = useAuth()
  
  // Cette route autorise uniquement les Superadmin et Admin
  if (isAdmin() || isSuperadmin()) {
    return children
  }
  
  return <Navigate to="/dashboard" replace />
}

export default App
