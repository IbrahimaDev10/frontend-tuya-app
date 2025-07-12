import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import AlertService from '../../services/alertService'
import Button from '../Button'
import Input from '../Input'
import './AlertDashboard.css'

const AlertDashboard = ({ clientId = null }) => {
  const { isSuperadmin } = useAuth()
  const [criticalAlerts, setCriticalAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState('24')
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    loadCriticalAlerts()
  }, [timeRange])

  const loadCriticalAlerts = async () => {
    try {
      setLoading(true)
      const response = await AlertService.obtenirAlertesCritiques(parseInt(timeRange))
      
      if (response.data.success) {
        setCriticalAlerts(response.data.alertes || [])
      }
    } catch (error) {
      console.error('Erreur chargement alertes critiques:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAnalyzeClient = async () => {
    if (!clientId) return
    
    try {
      setAnalyzing(true)
      const response = await AlertService.analyserClient(clientId, true)
      
      if (response.data.success) {
        setAnalysisResult(response.data)
      }
    } catch (error) {
      console.error('Erreur analyse client:', error)
    } finally {
      setAnalyzing(false)
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

  return (
    <div className="alert-dashboard">
      <div className="dashboard-header">
        <h2>🚨 Alertes Critiques</h2>
        <div className="header-controls">
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
          
          <Button
            variant="outline"
            onClick={loadCriticalAlerts}
            loading={loading}
          >
            🔄 Actualiser
          </Button>
          
          {clientId && (
            <Button
              variant="primary"
              onClick={handleAnalyzeClient}
              loading={analyzing}
            >
              🔬 Analyser
            </Button>
          )}
        </div>
      </div>

      {/* Résumé */}
      <div className="alert-summary">
        <div className="summary-card critical">
          <div className="summary-icon">🚨</div>
          <div className="summary-content">
            <h3>Alertes Critiques</h3>
            <div className="summary-number">{criticalAlerts.length}</div>
            <span>Dernières {timeRange}h</span>
          </div>
        </div>
      </div>

      {/* Liste des alertes critiques */}
      <div className="critical-alerts-list">
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement des alertes critiques...</p>
          </div>
        ) : criticalAlerts.length > 0 ? (
          criticalAlerts.map(alert => (
            <div key={alert.id} className="critical-alert-item">
              <div className="alert-header">
                <div className="alert-info">
                  <span className="alert-icon">
                    {getAlertIcon(alert.type_alerte)}
                  </span>
                  <div className="alert-details">
                    <h4 className="alert-title">{alert.titre}</h4>
                    <p className="alert-device">
                      Appareil: {alert.device_name || alert.appareil_id}
                    </p>
                  </div>
                </div>
                <div className="alert-timestamp">
                  {formatDate(alert.date_creation)}
                </div>
              </div>
              
              <div className="alert-content">
                <p className="alert-message">{alert.message}</p>
                
                {alert.valeur_mesuree && (
                  <div className="alert-measurements">
                    <span className="measurement critical">
                      Valeur: {alert.valeur_mesuree} {alert.unite_mesure}
                    </span>
                    {alert.valeur_seuil && (
                      <span className="measurement threshold">
                        Seuil: {alert.valeur_seuil} {alert.unite_mesure}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="no-critical-alerts">
            <div className="no-alerts-icon">✅</div>
            <h3>Aucune alerte critique</h3>
            <p>Aucune alerte critique trouvée pour cette période.</p>
          </div>
        )}
      </div>

      {/* Résultat d'analyse */}
      {analysisResult && (
        <div className="analysis-result">
          <h3>📊 Résultat d'analyse</h3>
          <div className="analysis-content">
            <pre>{JSON.stringify(analysisResult, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default AlertDashboard
