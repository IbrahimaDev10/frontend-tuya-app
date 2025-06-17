import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './store/authContext'
import ProtectedRoute from './routes/ProtectedRoute'
import Login from './auth/Login'
import ForgotPassword from './auth/ForgotPassword'
import ResetPassword from './auth/ResetPassword'
import AdminDashboard from './dashboards/AdminDashboard'
import SuperAdminDashboard from './dashboards/SuperAdminDashboard'
import ClientDashboard from './dashboards/ClientDashboard'
import UserManagement from './pages/Users/UserManagement'
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
            
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <AdminRoute>
                    <UserManagement />
                  </AdminRoute>
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

// Composant pour protéger les routes admin
const AdminRoute = ({ children }) => {
  const { isAdmin, isSuperadmin } = useAuth()
  
  if (isAdmin() || isSuperadmin()) {
    return children
  }
  
  return <Navigate to="/dashboard" replace />
}

export default App