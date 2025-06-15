import React, { createContext, useContext, useEffect, useState } from 'react'
import {
  login as apiLogin,
  logout as apiLogout,
  getProfile,
  verifyToken,
} from '../services/authService'

const AuthContext = createContext()

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Check token on first load
  useEffect(() => {
    const initializeAuth = async () => {
      if (!token) {
        setLoading(false)
        return
      }

      try {
        const res = await verifyToken(token)
        setUser(res.data.user) // .user contient id, nom_complet, role, etc.
      } catch (err) {
        console.warn('Token invalide ou expiré')
        handleLogout()
      } finally {
        setLoading(false)
      }
    }

    initializeAuth()
  }, [token])

  // ========================
  // ACTIONS
  // ========================
  const handleLogin = async (email, password) => {
    const res = await apiLogin(email, password)
    const { access_token, user } = res.data.data

    localStorage.setItem('token', access_token)
    setToken(access_token)
    setUser(user)
  }

  const handleLogout = async () => {
    try {
      if (token) await apiLogout(token)
    } catch (err) {
      console.warn('Erreur lors du logout')
    }

    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
  }

  const refreshProfile = async () => {
    if (!token) return
    try {
      const res = await getProfile(token)
      setUser(res.data.data)
    } catch (err) {
      console.error('Erreur lors du rafraîchissement du profil')
    }
  }

  // ========================
  // ROLES HELPERS
  // ========================
  const isSuperadmin = () => user?.role === 'superadmin'
  const isAdmin = () => user?.role === 'admin'
  const isClient = () => user?.role === 'user'

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login: handleLogin,
        logout: handleLogout,
        refreshProfile,
        isSuperadmin,
        isAdmin,
        isClient,
        role: user?.role || null,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
