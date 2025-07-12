import React, { useState, useEffect } from 'react'
import AlertService from '../../services/alertService'
import './AlertIndicator.css'

const AlertIndicator = ({ device, onClick }) => {
  const [alertCount, setAlertCount] = useState(0)
  const [criticalCount, setCriticalCount] = useState(0)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (device && device.statut_assignation === 'assigne') {
      loadAlertCounts()
    }
  }, [device])

  const loadAlertCounts = async () => {
    try {
      setLoading(true)
      const response = await AlertService.obtenirAlertesActives(device.id || device.tuya_device_id)
      
      if (response.data.success) {
        const alerts = response.data.alertes || []
        setAlertCount(alerts.length)
        setCriticalCount(alerts.filter(a => a.gravite === 'critique').length)
      }
    } catch (error) {
      console.error('Erreur chargement compteurs alertes:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!device || device.statut_assignation !== 'assigne') {
    return null
  }

  return (
    <div className="alert-indicator" onClick={onClick}>
      {loading ? (
        <div className="alert-loading">
          <div className="mini-spinner"></div>
        </div>
      ) : (
        <>
          <div className="alert-icon">
            {criticalCount > 0 ? '🚨' : alertCount > 0 ? '⚠️' : '🔔'}
          </div>
          
          {alertCount > 0 && (
            <div className={`alert-badge ${criticalCount > 0 ? 'critical' : 'warning'}`}>
              {alertCount}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default AlertIndicator
