import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/authContext' // Ajout de useAuth
import ProtectedRoute from './routes/ProtectedRoute'
import Login from './auth/Login'
import ForgotPassword from './auth/ForgotPassword'
import ResetPassword from './auth/ResetPassword'
import AdminDashboard from './dashboards/AdminDashboard'
import SuperAdminDashboard from './dashboards/SuperAdminDashboard'
import ClientDashboard from './dashboards/ClientDashboard'
import NotFound from './pages/NotFound'
import './App.css'

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Routes publiques */}
            <Route path="/login" element={<Login />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            
            {/* Routes protégées */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardRouter />
                </ProtectedRoute>
              }
            />
            
            {/* Redirection par défaut */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </Router>
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

export default App