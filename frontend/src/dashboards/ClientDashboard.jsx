import React from 'react'
import ClientLayout from '../layouts/ClientLayout'
import './Dashboard.css'

const ClientDashboard = () => {
  return (
    <ClientLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de bord Client</h1>
          <p>Suivi de vos appareils</p>
        </div>

        <div className="dashboard-content">
          <div className="welcome-card">
            <div className="welcome-icon">📱</div>
            <div className="welcome-text">
              <h2>Bienvenue, Client !</h2>
              <p>
                Consultez l'état de vos appareils, suivez vos demandes de support 
                et accédez à l'historique de vos interventions.
              </p>
            </div>
          </div>

          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">📱</div>
              <div className="stat-content">
                <h3>Mes Appareils</h3>
                <div className="stat-number">--</div>
                <p>Appareils assignés</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">✅</div>
              <div className="stat-content">
                <h3>Fonctionnels</h3>
                <div className="stat-number">--</div>
                <p>État optimal</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🔄</div>
              <div className="stat-content">
                <h3>Support</h3>
                <div className="stat-number">--</div>
                <p>Demandes ouvertes</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📋</div>
              <div className="stat-content">
                <h3>Historique</h3>
                <div className="stat-number">--</div>
                <p>Interventions</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ClientLayout>
  )
}

export default ClientDashboard