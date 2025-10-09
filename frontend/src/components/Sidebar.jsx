import React from 'react'
import { useAuth } from '../store/authContext'
import './Sidebar.css'

const Sidebar = ({ isOpen, onClose }) => {
  const { user, isSuperadmin, isAdmin, isClient, logout } = useAuth()

  const getRoleLabel = (role) => {
  const roleLabels = {
    user: 'Utilisateur',
    admin: 'Administrateur',
    superadmin: 'Super administrateur'
  }
  return roleLabels[role] || 'Rôle inconnu'
}

  const getSidebarItems = () => {
    const baseItems = [
      {
        icon: '🏠',
        label: 'Tableau de bord',
        path: '/dashboard',
        active: window.location.pathname === '/dashboard'
      }
    ]

    



    if (isSuperadmin()) {
      return [
        ...baseItems,
        {
          icon: '👥',
          label: 'Gestion des Utilisateurs',
          path: '/users',
          active: window.location.pathname === '/users'
        },
        {
          icon: '🏢',
          label: 'Gestion des Sites',
          path: '/sites',
          active: window.location.pathname === '/sites'
        },
        {
          icon: '📱',
          label: 'Gestion des Appareils',
          path: '/devices',
          active: window.location.pathname === '/devices'
        },
        {
          icon: '🔔',
          label: 'Alertes',
          path: '/alertes',
          active: window.location.pathname === '/alertes'
        },
      ]
    }

    if (isAdmin()) {
      return [
        ...baseItems,
        {
          icon: '👥',
          label: 'Gestion des Utilisateurs',
          path: '/users',
          active: window.location.pathname === '/users'
        },
        {
          icon: '🏢',
          label: 'Gestion des Sites',
          path: '/sites',
          active: window.location.pathname === '/sites'
        },
        // {
        //   icon: '👤',
        //   label: 'Gestion des Clients',
        //   path: '/clients',
        //   active: window.location.pathname === '/clients'
        // },
        {
          icon: '📱',
          label: 'Gestion des Appareils',
          path: '/devices',
          active: window.location.pathname === '/devices'
        },
  
        {
          icon: '🔔',
          label: 'Alertes',
          path: '/alertes',
          active: window.location.pathname === '/alertes'
        }
      ]
    }

    if (isClient()) {
      return [
        ...baseItems,
        {
          icon: '📱',
          label: 'Mes Appareils',
          path: '/devices',
          active: window.location.pathname === '/devices'
        },
        // {
        //   icon: '🔄',
        //   label: 'Demandes Support',
        //   path: '/support-requests'
        // }
       
      ]
    }

    return baseItems
  }

  const sidebarItems = getSidebarItems()

  const handleNavigation = (path) => {
    // Utiliser window.location pour le moment
    window.location.href = path
    onClose()
  }

  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose}></div>}
      
      <aside className={`sidebar ${isOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
             <img src="/src/assets/images/logob.png" alt="Logo" />
          </div>
          <button className="sidebar-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {user?.nom_complet?.charAt(0) || 'U'}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-username">{user?.nom_complet}</div>
            <div className="sidebar-role">{getRoleLabel(user?.role)}</div>

          </div>
        </div>

        <nav className="sidebar-nav">
          <ul className="sidebar-menu">
            {sidebarItems.map((item, index) => (
              <li key={index} className="sidebar-item">
                <button 
                  className={`sidebar-link ${item.active ? 'active' : ''}`}
                  onClick={() => handleNavigation(item.path)}
                >
                  <span className="sidebar-icon">{item.icon}</span>
                  <span className="sidebar-label">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="sidebar-footer">
          <button 
            className="sidebar-logout"
            onClick={logout}
          >
            <span className="sidebar-icon">🚪</span>
            <span className="sidebar-label">Déconnexion</span>
          </button>
        </div>
      </aside>
    </>
  )
}

export default Sidebar