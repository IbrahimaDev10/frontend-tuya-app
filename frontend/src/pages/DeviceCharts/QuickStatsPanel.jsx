import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import './DeviceCharts.css'

const QuickStatsPanel = ({ device }) => {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('24h')

  useEffect(() => {
    loadStats()
  }, [device, period])

  const loadStats = async () => {
    try {
      setLoading(true)
      
      // Charger les données récentes pour calculer les stats
      const endTime = new Date().getTime()
      const periodHours = {
        '1h': 1,
        '6h': 6,
        '24h': 24,
        '7d': 168
      }
      const startTime = endTime - (periodHours[period] * 60 * 60 * 1000)

      const [tensionData, courantData, puissanceData] = await Promise.all([
        DeviceService.obtenirGraphiqueTension(device.id || device.tuya_device_id, startTime, endTime),
        DeviceService.obtenirGraphiqueCourant(device.id || device.tuya_device_id, startTime, endTime),
        DeviceService.obtenirGraphiquePuissance(device.id || device.tuya_device_id, startTime, endTime)
      ])

      const tensionValues = tensionData.data.donnees_bdd?.map(d => d.value) || []
      const courantValues = courantData.data.donnees_bdd?.map(d => d.value) || []
      const puissanceValues = puissanceData.data.donnees_bdd?.map(d => d.value) || []

      setStats({
        tension: calculateStats(tensionValues, 'V'),
        courant: calculateStats(courantValues, 'A'),
        puissance: calculateStats(puissanceValues, 'W'),
        periode: period,
        derniereMesure: getLastMeasurement([tensionData.data, courantData.data, puissanceData.data])
      })

    } catch (error) {
      console.error('Erreur chargement stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const calculateStats = (values, unit) => {
    if (!values || values.length === 0) {
      return {
        min: 'N/A',
        max: 'N/A',
        avg: 'N/A',
        current: 'N/A',
        count: 0,
        unit
      }
    }

    const numValues = values.filter(v => v !== null && v !== undefined && !isNaN(v))
    
    return {
      min: Math.min(...numValues).toFixed(2),
      max: Math.max(...numValues).toFixed(2),
      avg: (numValues.reduce((sum, val) => sum + val, 0) / numValues.length).toFixed(2),
      current: numValues[numValues.length - 1]?.toFixed(2) || 'N/A',
      count: numValues.length,
      unit
    }
  }

  const getLastMeasurement = (dataArrays) => {
    let lastTimestamp = null
    
    dataArrays.forEach(data => {
      if (data.donnees_bdd && data.donnees_bdd.length > 0) {
        const lastData = data.donnees_bdd[data.donnees_bdd.length - 1]
        const timestamp = new Date(lastData.timestamp)
        if (!lastTimestamp || timestamp > lastTimestamp) {
          lastTimestamp = timestamp
        }
      }
    })

    return lastTimestamp
  }

  if (loading) {
    return (
      <div className="quick-stats-panel">
        <div className="stats-header">
          <h4>📊 Statistiques rapides</h4>
        </div>
        <div className="stats-loading">
          <div className="loading-spinner small"></div>
          <span>Chargement...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="quick-stats-panel">
      <div className="stats-header">
        <h4>📊 Statistiques rapides</h4>
        <select 
          value={period} 
          onChange={(e) => setPeriod(e.target.value)}
          className="period-selector"
        >
          <option value="1h">Dernière heure</option>
          <option value="6h">6 dernières heures</option>
          <option value="24h">24 dernières heures</option>
          <option value="7d">7 derniers jours</option>
        </select>
      </div>

      {stats && (
        <div className="stats-content">
          <div className="stats-grid">
            {/* Tension */}
            <div className="stat-card tension">
              <div className="stat-header">
                <span className="stat-icon">⚡</span>
                <span className="stat-title">Tension</span>
              </div>
              <div className="stat-values">
                <div className="stat-row">
                  <span className="stat-label">Actuelle:</span>
                  <span className="stat-value current">{stats.tension.current} {stats.tension.unit}</span>
                   <span className="stat-label">Min:</span>
                  <span className="stat-value">{stats.tension.min} {stats.tension.unit}</span>
                  </div>

                <div className="stat-row">
                  <span className="stat-label">Max:</span>
                  <span className="stat-value">{stats.tension.max} {stats.tension.unit}</span>
                  <span className="stat-label">Moyenne:</span>
                  <span className="stat-value">{stats.tension.avg} {stats.tension.unit}</span>
                </div>
              </div>
            </div>

            {/* Courant */}
            <div className="stat-card courant">
              <div className="stat-header">
                <span className="stat-icon">🔌</span>
                <span className="stat-title">Courant</span>
              </div>
              <div className="stat-values">
                <div className="stat-row">
                  <span className="stat-label">Actuel:</span>
                  <span className="stat-value current">{stats.courant.current} {stats.courant.unit}</span>
                   <span className="stat-label">Min:</span>
                  <span className="stat-value">{stats.courant.min} {stats.courant.unit}</span>
                </div>
                
                <div className="stat-row">
                  <span className="stat-label">Max:</span>
                  <span className="stat-value">{stats.courant.max} {stats.courant.unit}</span>
                  <span className="stat-label">Moyenne:</span>
                  <span className="stat-value">{stats.courant.avg} {stats.courant.unit}</span>
                </div>
                
              </div>
            </div>

            {/* Puissance */}
            <div className="stat-card puissance">
              <div className="stat-header">
                <span className="stat-icon">💡</span>
                <span className="stat-title">Puissance</span>
              </div>
              <div className="stat-values">
                <div className="stat-row">
                  <span className="stat-label">Actuelle:</span>
                  <span className="stat-value current">{stats.puissance.current} {stats.puissance.unit}</span>
                 <span className="stat-label">Min:</span>
                  <span className="stat-value">{stats.puissance.min} {stats.puissance.unit}</span>
                </div>
                
                <div className="stat-row">
                  <span className="stat-label">Max:</span>
                  <span className="stat-value">{stats.puissance.max} {stats.puissance.unit}</span>
                <span className="stat-label">Moyenne:</span>
                  <span className="stat-value">{stats.puissance.avg} {stats.puissance.unit}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="stats-footer">
            <div className="data-info">
              <span>📊 {stats.tension.count + stats.courant.count + stats.puissance.count} mesures</span>
              {stats.derniereMesure && (
                <span>⏱️ Dernière mesure: {stats.derniereMesure.toLocaleString('fr-FR')}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default QuickStatsPanel
