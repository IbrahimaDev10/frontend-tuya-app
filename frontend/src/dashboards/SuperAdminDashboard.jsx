import React from 'react'
import SuperAdminLayout from '../layouts/SuperAdminLayout'
import './Dashboard.css'

const SuperAdminDashboard = () => {
  return (
    <SuperAdminLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de bord SuperAdmin</h1>
          <p>Vue d'ensemble du système complet</p>
        </div>

        <div className="dashboard-content">
          <div className="welcome-card">
            <div className="welcome-icon">👑</div>
            <div className="welcome-text">
              <h2>Bienvenue, SuperAdmin !</h2>
              <p>
                Vous avez accès à toutes les fonctionnalités du système. 
                Vous pouvez gérer les utilisateurs, les structures, tous les appareils 
                et consulter les rapports globaux.
              </p>
            </div>
          </div>

          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">🏢</div>
              <div className="stat-content">
                <h3>Structures</h3>
                <div className="stat-number">--</div>
                <p>Structures actives</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">👥</div>
              <div className="stat-content">
                <h3>Utilisateurs</h3>
                <div className="stat-number">--</div>
                <p>Utilisateurs totaux</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📱</div>
              <div className="stat-content">
                <h3>Appareils</h3>
                <div className="stat-number">--</div>
                <p>Appareils gérés</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">⚡</div>
              <div className="stat-content">
                <h3>Activité</h3>
                <div className="stat-number">--</div>
                <p>Actions aujourd'hui</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </SuperAdminLayout>
  )
}

export default SuperAdminDashboard