import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import './DeviceModal.css'

const DeviceDetailsModal = ({ device, onClose }) => {
  const [deviceDetails, setDeviceDetails] = useState(null)
  const [deviceData, setDeviceData] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (device) {
      loadDeviceDetails()
      loadDeviceData()
    }
  }, [device])

  const loadDeviceDetails = async () => {
    try {
      const response = await DeviceService.obtenirStatutAppareil(device.id || device.tuya_device_id)
      if (response.data.success) {
        setDeviceDetails(response.data)
      }
    } catch (error) {
      console.error('Erreur chargement détails:', error)
    }
  }

  const loadDeviceData = async () => {
    try {
      const response = await DeviceService.obtenirDonneesAppareil(device.id || device.tuya_device_id, 50)
      if (response.data.success) {
        setDeviceData(response.data.data || [])
      }
    } catch (error) {
      console.error('Erreur chargement données:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await DeviceService.collecterDonnees(device.id || device.tuya_device_id)
      await loadDeviceDetails()
      await loadDeviceData()
    } catch (error) {
      console.error('Erreur rafraîchissement:', error)
    } finally {
      setRefreshing(false)
    }
  }

  const handleToggle = async () => {
    try {
      const response = await DeviceService.toggleAppareil(device.id || device.tuya_device_id)
      if (response.data.success) {
        await loadDeviceDetails()
      }
    } catch (error) {
      console.error('Erreur toggle:', error)
    }
  }

  const formatValue = (value, unit = '') => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return `${value.toFixed(2)} ${unit}`.trim()
    }
    return value
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('fr-FR')
  }

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Détails de l'appareil</h3>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Chargement des détails...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content extra-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{device?.nom_appareil || device?.tuya_nom_original}</h3>
          <div className="header-actions">
            <Button
              variant="outline"
              size="small"
              onClick={handleRefresh}
              loading={refreshing}
            >
              🔄 Actualiser
            </Button>
            {device?.statut_assignation === 'assigne' && (
              <Button
                variant="primary"
                size="small"
                onClick={handleToggle}
              >
                {deviceDetails?.statut_bdd?.etat_switch ? '⏸️ OFF' : '▶️ ON'}
              </Button>
            )}
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
        </div>

        {/* Onglets */}
        <div className="modal-tabs">
          <button
            className={`modal-tab ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📊 Vue d'ensemble
          </button>
          <button
            className={`modal-tab ${activeTab === 'data' ? 'active' : ''}`}
            onClick={() => setActiveTab('data')}
          >
            📈 Données
          </button>
          <button
            className={`modal-tab ${activeTab === 'technical' ? 'active' : ''}`}
            onClick={() => setActiveTab('technical')}
          >
            🔧 Technique
          </button>
        </div>

        <div className="modal-body">
          {/* Vue d'ensemble */}
          {activeTab === 'overview' && (
            <div className="overview-content">
              {/* Statut actuel */}
              <div className="status-cards">
                <div className="status-card">
                  <h4>État</h4>
                  <div className={`status-indicator ${device?.etat_switch ? 'on' : 'off'}`}>
                    {device?.etat_switch ? '🟢 ON' : '🔴 OFF'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Connexion</h4>
                  <div className={`status-indicator ${device?.en_ligne ? 'online' : 'offline'}`}>
                    {device?.en_ligne ? '🟢 En ligne' : '🔴 Hors ligne'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Assignation</h4>
                  <div className={`status-indicator ${device?.statut_assignation === 'assigne' ? 'assigned' : 'unassigned'}`}>
                    {device?.statut_assignation === 'assigne' ? '📎 Assigné' : '❓ Non assigné'}
                  </div>
                </div>
              </div>

              {/* Informations générales */}
              <div className="info-section">
                <h4>Informations générales</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Nom:</label>
                    <span>{device?.nom_appareil}</span>
                  </div>
                  <div className="info-item">
                    <label>Type:</label>
                    <span>{device?.type_appareil}</span>
                  </div>
                  <div className="info-item">
                    <label>Emplacement:</label>
                    <span>{device?.emplacement || 'Non défini'}</span>
                  </div>
                  <div className="info-item">
                    <label>Client:</label>
                    <span>{device?.client?.nom_entreprise || 'Non assigné'}</span>
                  </div>
                  <div className="info-item">
                    <label>Installation:</label>
                    <span>{formatDate(device?.date_installation)}</span>
                  </div>
                  <div className="info-item">
                    <label>Dernière activité:</label>
                    <span>{formatDate(device?.derniere_donnee)}</span>
                  </div>
                </div>
              </div>

              {/* Mesures actuelles */}
              {deviceDetails?.statut_tuya && (
                <div className="measurements-section">
                  <h4>Mesures actuelles</h4>
                  <div className="measurements-grid">
                    <div className="measurement-card">
                      <div className="measurement-icon">⚡</div>
                      <div className="measurement-content">
                        <h5>Tension</h5>
                        <div className="measurement-value">
                          {formatValue(deviceDetails.statut_tuya.values?.tension, 'V')}
                        </div>
                      </div>
                    </div>
                    <div className="measurement-card">
                      <div className="measurement-icon">🔌</div>
                      <div className="measurement-content">
                        <h5>Courant</h5>
                        <div className="measurement-value">
                          {formatValue(deviceDetails.statut_tuya.values?.courant, 'A')}
                        </div>
                      </div>
                    </div>
                    <div className="measurement-card">
                      <div className="measurement-icon">💡</div>
                      <div className="measurement-content">
                        <h5>Puissance</h5>
                        <div className="measurement-value">
                          {formatValue(deviceDetails.statut_tuya.values?.puissance, 'W')}
                        </div>
                      </div>
                    </div>
                    <div className="measurement-card">
                      <div className="measurement-icon">📊</div>
                      <div className="measurement-content">
                        <h5>Énergie</h5>
                        <div className="measurement-value">
                          {formatValue(deviceDetails.statut_tuya.values?.energie, 'kWh')}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Données */}
          {activeTab === 'data' && (
            <div className="data-content">
              <div className="data-header">
                <h4>Historique des données (50 dernières)</h4>
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => loadDeviceData()}
                >
                  🔄 Actualiser
                </Button>
              </div>
              
              {deviceData.length > 0 ? (
                <div className="data-table-container">
                  <table className="data-table compact">
                    <thead>
                      <tr>
                        <th>Date/Heure</th>
                        <th>Tension (V)</th>
                        <th>Courant (A)</th>
                        <th>Puissance (W)</th>
                        <th>État</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deviceData.map((data, index) => (
                        <tr key={index}>
                          <td>{formatDate(data.horodatage)}</td>
                          <td>{formatValue(data.tension)}</td>
                          <td>{formatValue(data.courant)}</td>
                          <td>{formatValue(data.puissance)}</td>
                          <td>
                            <span className={`state-badge ${data.etat_switch ? 'on' : 'off'}`}>
                              {data.etat_switch ? 'ON' : 'OFF'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <p>Aucune donnée disponible</p>
                </div>
              )}
            </div>
          )}

          {/* Technique */}
          {activeTab === 'technical' && (
            <div className="technical-content">
              <div className="info-section">
                <h4>Informations Tuya</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Device ID:</label>
                    <span className="code">{device?.tuya_device_id}</span>
                  </div>
                  <div className="info-item">
                    <label>Nom original:</label>
                    <span>{device?.tuya_nom_original}</span>
                  </div>
                  <div className="info-item">
                    <label>Modèle:</label>
                    <span>{device?.tuya_modele}</span>
                  </div>
                  <div className="info-item">
                    <label>Firmware:</label>
                    <span>{device?.tuya_version_firmware || 'N/A'}</span>
                  </div>
                  <div className="info-item">
                    <label>Catégorie:</label>
                    <span>{device?.tuya_categorie || 'N/A'}</span>
                  </div>
                  <div className="info-item">
                    <label>UUID (BDD):</label>
                    <span className="code">{device?.id}</span>
                  </div>
                </div>
              </div>

              {/* Seuils configurés */}
              <div className="info-section">
                <h4>Seuils configurés</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Tension min:</label>
                    <span>{formatValue(device?.seuil_tension_min, 'V')}</span>
                  </div>
                  <div className="info-item">
                    <label>Tension max:</label>
                    <span>{formatValue(device?.seuil_tension_max, 'V')}</span>
                  </div>
                  <div className="info-item">
                    <label>Courant max:</label>
                    <span>{formatValue(device?.seuil_courant_max, 'A')}</span>
                  </div>
                  <div className="info-item">
                    <label>Puissance max:</label>
                    <span>{formatValue(device?.seuil_puissance_max, 'W')}</span>
                  </div>
                </div>
              </div>

              {/* Données brutes */}
              {deviceDetails?.statut_tuya?.values && (
                <div className="info-section">
                  <h4>Données brutes Tuya</h4>
                  <pre className="json-display">
                    {JSON.stringify(deviceDetails.statut_tuya.values, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
          >
            Fermer
          </Button>
        </div>
      </div>
    </div>
  )
}

export default DeviceDetailsModal