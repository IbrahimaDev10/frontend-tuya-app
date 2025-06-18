import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '../store/authContext'
import ChangePasswordModal from './ChangePasswordModal'
import './Navbar.css'

const Navbar = ({ onMenuToggle }) => {
  const { user, logout } = useAuth()
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false)
  const profileMenuRef = useRef(null)

  // Fermer le menu profil si on clique ailleurs
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setShowProfileMenu(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    setShowProfileMenu(false)
  }

  return (
    <>
      <nav className="navbar">
        <div className="navbar-left">
          <button 
            className="menu-toggle"
            onClick={onMenuToggle}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          
          <div className="navbar-logo">
            <img src="/src/assets/images/logob.png" alt="Logo" />
          </div>
        </div>

        <div className="navbar-center">
          <h1>Sertec Ingénierie</h1>
        </div>

        <div className="navbar-right">
          <div className="profile-menu" ref={profileMenuRef}>
            <button
              className="profile-button"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
            >
              <div className="profile-avatar">
                {user?.nom_complet?.charAt(0) || 'U'}
              </div>
              <span className="profile-name">{user?.nom_complet}</span>
              <svg className="dropdown-arrow" width="12" height="12" viewBox="0 0 12 12">
                <path d="M6 8L2 4h8l-4 4z" fill="currentColor"/>
              </svg>
            </button>

            {showProfileMenu && (
              <div className="profile-dropdown">
                <div className="profile-info">
                  <div className="profile-avatar-large">
                    {user?.nom_complet?.charAt(0) || 'U'}
                  </div>
                  <div>
                    <div className="profile-name">{user?.nom_complet}</div>
                    <div className="profile-email">{user?.email}</div>
                    <div className="profile-role">{user?.role}</div>
                  </div>
                </div>
                
                <div className="profile-actions">
                  <button 
                    className="profile-action"
                    onClick={() => {
                      setShowChangePasswordModal(true)
                      setShowProfileMenu(false)
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zM7 6a1 1 0 1 1 2 0v4a1 1 0 1 1-2 0V6z"/>
                    </svg>
                    Changer mot de passe
                  </button>
                  
                  <button 
                    className="profile-action logout"
                    onClick={handleLogout}
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M6 2a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H6z"/>
                    </svg>
                    Déconnexion
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>

      {showChangePasswordModal && (
        <ChangePasswordModal
          onClose={() => setShowChangePasswordModal(false)}
        />
      )}
    </>
  )
}

export default Navbar