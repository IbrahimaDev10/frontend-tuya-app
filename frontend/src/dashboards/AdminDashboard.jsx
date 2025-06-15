import React from 'react'
import AdminLayout from '../layouts/AdminLayout'
import './Dashboard.css'

const AdminDashboard = () => {
  return (
    <AdminLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de bord Admin</h1>
          <p>Gestion de votre structure</p>
        </div>

        <div className="dashboard-content">
          <div className="welcome-card">
            <div className="welcome-icon">🛠️</div>
            <div className="welcome-text">
              <h2>Bienvenue, Admin !</h2>
              <p>
                Vous pouvez gérer les clients de votre structure, 
                suivre l'inventaire des appareils et planifier la maintenance.
              </p>
            </div>
          </div>

          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">👤</div>
              <div className="stat-content">
                <h3>Clients</h3>
                <div className="stat-number">--</div>
                <p>Clients actifs</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📱</div>
              <div className="stat-content">
                <h3>Appareils</h3>
                <div className="stat-number">--</div>
                <p>Appareils structure</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🔧</div>
              <div className="stat-content">
                <h3>Maintenance</h3>
                <div className="stat-number">--</div>
                <p>En attente</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <h3>Rapports</h3>
                <div className="stat-number">--</div>
                <p>Cette semaine</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  )
}

export default AdminDashboard