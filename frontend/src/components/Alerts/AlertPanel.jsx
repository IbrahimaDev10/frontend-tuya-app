import React, { useState, useEffect, useRef } from 'react'
import AlertService from '../../services/alertService'
import Button from '../Button'
import Input from '../Input'
import './AlertPanel.css'

const AlertPanel = ({ device, onClose }) => {
  const [alerts, setAlerts] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('recent')
  const [timeRange, setTimeRange] = useState('24')
  const [resolving, setResolving] = useState({})
  
  // ✅ Ref pour la zone scrollable
  const alertListRef = useRef(null)

  useEffect(() => {
    if (device) {
      loadAlerts()
      loadStats()
    }
  }, [device, timeRange])

  // ✅ Effet pour auto-scroll vers le haut lors du changement d'onglet
  useEffect(() => {
    if (alertListRef.current) {
      alertListRef.current.scrollTop = 0
    }
  }, [activeTab, alerts])

  const loadAlerts = async () => {
    try {
      setLoading(true)
      const response = await AlertService.obtenirAlertesAppareil(
        device.id || device.tuya_device_id,
        parseInt(timeRange),
        50
      )
      
      if (response.data.success) {
        setAlerts(response.data.alertes || [])
      }
    } catch (error) {
      console.error('Erreur chargement alertes:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadActiveAlerts = async () => {
    try {
      setLoading(true)
      const response = await AlertService.obtenirAlertesActives(device.id || device.tuya_device_id)
      
      if (response.data.success) {
        setAlerts(response.data.alertes || [])
      }
    } catch (error) {
      console.error('Erreur chargement alertes actives:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const response = await AlertService.obtenirStatistiquesAlertes(
        device.id || device.tuya_device_id,
        7
      )
      
      if (response.data.success) {
        setStats(response.data.stats)
      }
    } catch (error) {
      console.error('Erreur chargement stats:', error)
    }
  }

  const handleResolveAlert = async (alertId) => {
    try {
      setResolving(prev => ({ ...prev, [alertId]: true }))
      
      const response = await AlertService.resoudreAlerte(alertId, 'Résolu depuis l\'interface')
      
      if (response.data.success) {
        // Actualiser les alertes
        if (activeTab === 'recent') {
          loadAlerts()
        } else {
          loadActiveAlerts()
        }
        loadStats()
      }
    } catch (error) {
      console.error('Erreur résolution alerte:', error)
    } finally {
      setResolving(prev => ({ ...prev, [alertId]: false }))
    }
  }

  const handleMarkSeen = async (alertId) => {
    try {
      await AlertService.marquerAlerteVue(alertId)
      if (activeTab === 'recent') {
        loadAlerts()
      } else {
        loadActiveAlerts()
      }
    } catch (error) {
      console.error('Erreur marquage alerte:', error)
    }
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    if (tab === 'active') {
      loadActiveAlerts()
    } else {
      loadAlerts()
    }
  }

  // ✅ Gestion du clavier pour l'accessibilité
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('fr-FR')
  }

  const getAlertIcon = (type) => {
    const icons = {
      'seuil_depasse': '⚠️',
      'hors_ligne': '📡',
      'erreur_communication': '🔌',
      'maintenance_requise': '🔧',
      'protection_declenchee': '🛡️',
      'temperature_haute': '🌡️',
      'tension_anormale': '⚡',
      'courant_depasse': '🔌'
    }
    return icons[type] || '🔔'
  }

  const getGravityColor = (gravite) => {
    const colors = {
      'info': '#17a2b8',
      'warning': '#ffc107',
      'critique': '#dc3545'
    }
    return colors[gravite] || '#6c757d'
  }

  if (loading && alerts.length === 0) {
    return (
      <div className="alert-panel" onKeyDown={handleKeyDown} tabIndex={0}>
        <div className="alert-panel-header">
          <h3>🔔 Alertes - {device?.nom_appareil}</h3>
          <Button variant="outline" size="small" onClick={onClose}>
            ✕ Fermer
          </Button>
        </div>
        <div className="alert-panel-body">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement des alertes...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="alert-panel" onKeyDown={handleKeyDown} tabIndex={0}>
      <div className="alert-panel-header">
        <h3>🔔 Alertes - {device?.nom_appareil}</h3>
        <div className="header-actions">
          <select 
            value={timeRange} 
            onChange={(e) => setTimeRange(e.target.value)}
            className="time-range-select"
          >
            <option value="1">1 heure</option>
            <option value="6">6 heures</option>
            <option value="24">24 heures</option>
            <option value="168">7 jours</option>
          </select>
          <Button variant="outline" size="small" onClick={onClose}>
            ✕ Fermer
          </Button>
        </div>
      </div>

      {/* Statistiques */}
      {stats && (
        <div className="alert-stats">
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Total (7j):</span>
              <span className="stat-value">{stats.total}</span>
            </div>
            <div className="stat-item critiques">
              <span className="stat-label">Critiques:</span>
              <span className="stat-value">{stats.par_gravite?.critique || 0}</span>
            </div>
            <div className="stat-item warnings">
              <span className="stat-label">Warnings:</span>
              <span className="stat-value">{stats.par_gravite?.warning || 0}</span>
            </div>
            <div className="stat-item resolues">
              <span className="stat-label">Résolues:</span>
              <span className="stat-value">{stats.par_statut?.resolue || 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Onglets */}
      <div className="alert-tabs">
        <button
          className={`alert-tab ${activeTab === 'recent' ? 'active' : ''}`}
          onClick={() => handleTabChange('recent')}
        >
          Récentes ({alerts.length})
        </button>
        <button
          className={`alert-tab ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => handleTabChange('active')}
        >
          Actives
        </button>
      </div>

      {/* ✅ Zone scrollable avec ref */}
      <div 
        className="alert-list" 
        ref={alertListRef}
        role="region"
        aria-label="Liste des alertes"
        aria-live="polite"
      >
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement...</p>
          </div>
        ) : alerts.length > 0 ? (
          alerts.map((alert, index) => (
            <div 
              key={alert.id} 
              className={`alert-item ${alert.gravite}`}
              role="article"
              aria-label={`Alerte ${index + 1} de ${alerts.length}`}
            >
              <div className="alert-header">
                <div className="alert-info">
                  <span className="alert-icon">
                    {getAlertIcon(alert.type_alerte)}
                  </span>
                  <div className="alert-title-group">
                    <h4 className="alert-title">{alert.titre}</h4>
                    <span 
                      className="alert-gravity"
                      style={{ color: getGravityColor(alert.gravite) }}
                    >
                      {alert.gravite.toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="alert-actions">
                  {alert.statut === 'nouvelle' && (
                    <Button
                      variant="outline"
                      size="small"
                      onClick={() => handleMarkSeen(alert.id)}
                      aria-label="Marquer comme vue"
                    >
                      👁️ Vu
                    </Button>
                  )}
                  {alert.statut !== 'resolue' && (
                    <Button
                      variant="primary"
                      size="small"
                      onClick={() => handleResolveAlert(alert.id)}
                      loading={resolving[alert.id]}
                      aria-label="Résoudre l'alerte"
                    >
                      ✅ Résoudre
                    </Button>
                  )}
                </div>
              </div>
              
              <div className="alert-content">
                <p className="alert-message">{alert.message}</p>
                
                {alert.valeur_mesuree && (
                  <div className="alert-measurements">
                    <span className="measurement">
                      Valeur: {alert.valeur_mesuree} {alert.unite_mesure}
                    </span>
                    {alert.valeur_seuil && (
                      <span className="measurement">
                        Seuil: {alert.valeur_seuil} {alert.unite_mesure}
                      </span>
                    )}
                  </div>
                )}
                
                <div className="alert-meta">
                  <span className="alert-date">
                    {formatDate(alert.date_creation)}
                  </span>
                  <span className={`alert-status ${alert.statut}`}>
                    {alert.statut}
                  </span>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="no-alerts">
            <div className="no-alerts-icon">🔔</div>
            <h4>Aucune alerte</h4>
            <p>Aucune alerte trouvée pour cette période.</p>
          </div>
        )}
      </div>

      <div className="alert-panel-footer">
        <Button
          variant="outline"
          onClick={activeTab === 'recent' ? loadAlerts : loadActiveAlerts}
          loading={loading}
        >
          🔄 Actualiser
        </Button>
        <Button
          variant="secondary"
          onClick={onClose}
        >
          Fermer
        </Button>
      </div>
    </div>
  )
}

export default AlertPanel
