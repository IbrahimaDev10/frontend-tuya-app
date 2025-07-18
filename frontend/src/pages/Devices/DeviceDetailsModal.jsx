import React, { useState, useEffect } from 'react'
import MultiChartView from '../../pages/DeviceCharts/MultiChartView'
import QuickStatsPanel from '../../pages/DeviceCharts/QuickStatsPanel'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import ProtectionModal from '../../components/DeviceProtection/ProtectionModal'
import ScheduleModal from '../../components/DeviceProtection/ScheduleModal'
import AlertPanel from '../../components/Alerts/AlertPanel'
import AlertIndicator from '../../components/Alerts/AlertIndicator'
import './DeviceModal.css' // Assurez-vous que ce CSS est approprié pour ce modal aussi

const DeviceDetailsModal = ({ device, onClose }) => {
  // MODIFICATION 1: Utiliser deviceFullDetails pour stocker les détails complets de l'appareil
  // C'est l'objet retourné par obtenirAppareil qui contient etat_actuel_tuya, en_ligne, etc.
  const [deviceFullDetails, setDeviceFullDetails] = useState(null) 
  const [deviceData, setDeviceData] = useState([]) // Historique des données
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [refreshing, setRefreshing] = useState(false)

  const [showProtectionModal, setShowProtectionModal] = useState(false)
  const [showScheduleModal, setShowScheduleModal] = useState(false)

  const [showAlerts, setShowAlerts] = useState(false)

  const [showCharts, setShowCharts] = useState(false)

  useEffect(() => {
    if (device) {
      // MODIFICATION 2: Appeler loadFullDeviceDetails au lieu de loadDeviceDetails
      loadFullDeviceDetails() 
      loadDeviceData()
    }
  }, [device])

  // MODIFICATION 3: Nouvelle fonction pour charger tous les détails de l'appareil
  const loadFullDeviceDetails = async () => {
    try {
      setRefreshing(true) // Activer le rafraîchissement pendant le chargement
      // Utiliser device.id pour obtenir les détails complets de l'appareil
      const response = await DeviceService.obtenirAppareil(device.id) 
      if (response.data.success) {
        setDeviceFullDetails(response.data.data) // Stocker toutes les données de l'appareil
      }
    } catch (error) {
      console.error('Erreur chargement détails complets:', error)
    } finally {
      setRefreshing(false) // Désactiver le rafraîchissement
      setLoading(false) // Marquer le chargement initial comme terminé
    }
  }

  const loadDeviceData = async () => {
    try {
      // MODIFICATION 4: Utiliser device.id pour obtenir les données historiques
      const response = await DeviceService.obtenirDonneesAppareil(device.id, 50) 
      if (response.data.success) {
        setDeviceData(response.data.data || [])
      }
    } catch (error) {
      console.error('Erreur chargement données:', error)
    } finally {
      // setLoading(false) // Déplacé dans loadFullDeviceDetails pour une meilleure gestion
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      // MODIFICATION 5: Utiliser device.id pour collecter les données
      await DeviceService.collecterDonnees(device.id) 
      // MODIFICATION 6: Recharger les détails complets après rafraîchissement
      await loadFullDeviceDetails() 
      await loadDeviceData()
    } catch (error) {
      console.error('Erreur rafraîchissement:', error)
    } finally {
      setRefreshing(false)
    }
  }

  // MODIFICATION 7: Adapter handleToggle pour passer la valeur booléenne
  const handleToggle = async () => {
    if (!deviceFullDetails) return; // S'assurer que les données de l'appareil sont chargées

    try {
      // Déterminer le nouvel état souhaité (inverse de l'état actuel)
      const targetState = !deviceFullDetails.etat_actuel_tuya; 
      // Utiliser device.tuya_device_id pour le toggle (car c'est ce que le backend attend)
      const result = await DeviceService.toggleAppareil(device.tuya_device_id, targetState); 
      
      if (result.success) {
        // MODIFICATION 8: Mettre à jour l'état local du modal avec le nouvel état
        setDeviceFullDetails(prev => ({
          ...prev,
          etat_actuel_tuya: result.newState // result.newState vient du backend
        }));
      } else {
        console.error('Erreur toggle:', result.message);
      }
    } catch (error) {
      console.error('Erreur toggle:', error);
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

  // MODIFICATION 9: Afficher le spinner tant que deviceFullDetails n'est pas chargé
  if (loading || !deviceFullDetails) { 
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
  const isTriphase = deviceFullDetails?.type_systeme === 'triphase';
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content extra-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          {/* MODIFICATION 10: Utiliser deviceFullDetails pour le nom */}
          <h3>{deviceFullDetails?.nom_appareil || deviceFullDetails?.tuya_nom_original}</h3> 
          <div className="header-actions">
            <Button
              variant="outline"
              size="small"
              onClick={handleRefresh}
              loading={refreshing}
            >
              🔄 Actualiser
            </Button>
            {/* MODIFICATION 11: Utiliser deviceFullDetails pour vérifier le statut d'assignation */}
            {deviceFullDetails?.statut_assignation === 'assigne' && ( 
              <Button
                variant="primary"
                size="small"
                onClick={handleToggle}
              >
                {/* MODIFICATION 12: Utiliser deviceFullDetails.etat_actuel_tuya pour l'affichage du bouton */}
                {deviceFullDetails?.etat_actuel_tuya ? '⏸️ OFF' : '▶️ ON'} 
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
          <button
              className={`modal-tab ${activeTab === 'protection' ? 'active' : ''}`}
              onClick={() => setActiveTab('protection')}
            >
              🛡️ Protection & Horaires
            </button>
            <button
                className={`modal-tab ${activeTab === 'alerts' ? 'active' : ''}`}
                onClick={() => setActiveTab('alerts')}
              >
                🔔 Alertes
              </button>
          <button
            className={`modal-tab ${activeTab === 'charts' ? 'active' : ''}`}
            onClick={() => setActiveTab('charts')}
          >
            📈 Graphiques
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
                  {/* MODIFICATION 13: Utiliser deviceFullDetails.etat_actuel_tuya pour l'affichage de l'état */}
                  <div className={`status-indicator ${deviceFullDetails?.etat_actuel_tuya ? 'on' : 'off'}`}>
                    {deviceFullDetails?.etat_actuel_tuya ? '🟢 ON' : '🔴 OFF'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Connexion</h4>
                  {/* MODIFICATION 14: Utiliser deviceFullDetails.en_ligne pour l'affichage en ligne */}
                  <div className={`status-indicator ${deviceFullDetails?.en_ligne ? 'online' : 'offline'}`}>
                    {deviceFullDetails?.en_ligne ? '🟢 En ligne' : '🔴 Hors ligne'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Assignation</h4>
                  {/* MODIFICATION 15: Utiliser deviceFullDetails.statut_assignation pour l'affichage d'assignation */}
                  <div className={`status-indicator ${deviceFullDetails?.statut_assignation === 'assigne' ? 'assigned' : 'unassigned'}`}>
                    {deviceFullDetails?.statut_assignation === 'assigne' ? '📎 Assigné' : '❓ Non assigné'}
                  </div>
                </div>
              </div>

              {/* Informations générales */}
              <div className="info-section">
                <h4>Informations générales</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Nom:</label>
                    <span>{deviceFullDetails?.nom_appareil}</span>
                  </div>
                  <div className="info-item">
                    <label>Type:</label>
                    <span>{deviceFullDetails?.type_appareil}</span>
                  </div>
                  <div className="info-item">
                    <label>Emplacement:</label>
                    <span>{deviceFullDetails?.emplacement || 'Non défini'}</span>
                  </div>
                  <div className="info-item">
                    <label>Client:</label>
                    <span>{deviceFullDetails?.client?.nom_entreprise || 'Non assigné'}</span>
                  </div>
                  <div className="info-item">
                    <label>Installation:</label>
                    <span>{formatDate(deviceFullDetails?.date_installation)}</span>
                  </div>
                  <div className="info-item">
                    <label>Dernière activité:</label>
                    <span>{formatDate(deviceFullDetails?.derniere_donnee)}</span>
                  </div>
                </div>
              </div>

              {/* Mesures actuelles */}
              {/* MODIFICATION 16: Utiliser deviceFullDetails.real_time_status.data pour les mesures */}
               {deviceFullDetails?.real_time_status?.data && ( 
                <div className="measurements-section">
                  <h4>Mesures actuelles</h4>
                  {isTriphase ? (
                    // --- VUE POUR APPAREIL TRIPHASÉ ---
                    <div className="measurements-grid triphase">
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Tension L1</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.tension_l1, 'V')}</div></div></div>
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Tension L2</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.tension_l2, 'V')}</div></div></div>
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Tension L3</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.tension_l3, 'V')}</div></div></div>
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Courant L1</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.courant_l1, 'A')}</div></div></div>
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Courant L2</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.courant_l2, 'A')}</div></div></div>
                      <div className="measurement-card phase"><div className="measurement-content"><h5>Courant L3</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.courant_l3, 'A')}</div></div></div>
                      <div className="measurement-card total"><div className="measurement-content"><h5>Puissance Totale</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.puissance_totale, 'W')}</div></div></div>
                    </div>
                  ) : (
                    // --- VUE POUR APPAREIL MONOPHASÉ (code original) ---
                    <div className="measurements-grid">
                      <div className="measurement-card"><div className="measurement-icon">⚡</div><div className="measurement-content"><h5>Tension</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.tension, 'V')}</div></div></div>
                      <div className="measurement-card"><div className="measurement-icon">🔌</div><div className="measurement-content"><h5>Courant</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.courant, 'A')}</div></div></div>
                      <div className="measurement-card"><div className="measurement-icon">💡</div><div className="measurement-content"><h5>Puissance</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.puissance, 'W')}</div></div></div>
                      <div className="measurement-card"><div className="measurement-icon">📊</div><div className="measurement-content"><h5>Énergie</h5><div className="measurement-value">{formatValue(deviceFullDetails.real_time_status.data?.energie, 'kWh')}</div></div></div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Données */}
         {activeTab === 'data' && (
            <div className="data-content">
              <div className="data-header">
                <h4>Historique des données (50 dernières)</h4>
                <Button variant="outline" size="small" onClick={() => loadDeviceData()}>🔄 Actualiser</Button>
              </div>
              
              {deviceData.length > 0 ? (
                <div className="data-table-container">
                  <table className="data-table compact">
                    <thead>
                      {/* MODIFICATION TRIPHASÉ 3: Entêtes de tableau conditionnelles */}
                      {isTriphase ? (
                        <tr>
                          <th>Date/Heure</th>
                          <th>Tension (L1/L2/L3) V</th>
                          <th>Courant (L1/L2/L3) A</th>
                          <th>Puissance Totale (W)</th>
                          <th>État</th>
                        </tr>
                      ) : (
                        <tr>
                          <th>Date/Heure</th>
                          <th>Tension (V)</th>
                          <th>Courant (A)</th>
                          <th>Puissance (W)</th>
                          <th>État</th>
                        </tr>
                      )}
                    </thead>
                    <tbody>
                      {deviceData.map((data, index) => (
                        <tr key={index}>
                          <td>{formatDate(data.horodatage)}</td>
                          {/* MODIFICATION TRIPHASÉ 4: Cellules de tableau conditionnelles */}
                          {isTriphase ? (
                            <>
                              <td>{`${formatValue(data.tension_l1)} / ${formatValue(data.tension_l2)} / ${formatValue(data.tension_l3)}`}</td>
                              <td>{`${formatValue(data.courant_l1)} / ${formatValue(data.courant_l2)} / ${formatValue(data.courant_l3)}`}</td>
                              <td>{formatValue(data.puissance_totale)}</td>
                            </>
                          ) : (
                            <>
                              <td>{formatValue(data.tension)}</td>
                              <td>{formatValue(data.courant)}</td>
                              <td>{formatValue(data.puissance)}</td>
                            </>
                          )}
                          <td><span className={`state-badge ${data.etat_actuel_tuya ? 'on' : 'off'}`}>{data.etat_actuel_tuya ? 'ON' : 'OFF'}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state"><p>Aucune donnée disponible</p></div>
              )}
            </div>
          )}


             {/* Technique */}
          {activeTab === 'technical' && (
            <div className="technical-content">
              <div className="info-section">
                <h4>Informations Tuya</h4>
                <div className="info-grid">
                  <div className="info-item"><label>Device ID:</label><span>{deviceFullDetails?.tuya_device_id}</span></div>
                  <div className="info-item"><label>Nom original:</label><span>{deviceFullDetails?.tuya_nom_original}</span></div>
                  <div className="info-item"><label>Modèle:</label><span>{deviceFullDetails?.tuya_modele}</span></div>
                  <div className="info-item"><label>Firmware:</label><span>{deviceFullDetails?.tuya_version_firmware || 'N/A'}</span></div>
                  <div className="info-item"><label>Catégorie:</label><span>{deviceFullDetails?.type_appareil || 'N/A'}</span></div>
                  <div className="info-item"><label>UUID (BDD):</label><span>{deviceFullDetails?.id}</span></div>
                </div>
              </div>
              <div className="info-section">
                <h4>Seuils configurés</h4>
                <div className="info-grid">
                  <div className="info-item"><label>Tension min:</label><span>{formatValue(deviceFullDetails?.seuil_tension_min, 'V')}</span></div>
                  <div className="info-item"><label>Tension max:</label><span>{formatValue(deviceFullDetails?.seuil_tension_max, 'V')}</span></div>
                  <div className="info-item"><label>Courant max:</label><span>{formatValue(deviceFullDetails?.seuil_courant_max, 'A')}</span></div>
                  <div className="info-item"><label>Puissance max:</label><span>{formatValue(deviceFullDetails?.seuil_puissance_max, 'W')}</span></div>
                </div>
              </div>
              {deviceFullDetails?.real_time_status?.data && ( 
                <div className="info-section">
                  <h4>Données brutes Tuya</h4>
                  <pre className="json-display">{JSON.stringify(deviceFullDetails.real_time_status.data, null, 2)}</pre>
                </div>
              )}
            </div>
          )}

              {activeTab === 'protection' && (
                <div className="protection-content">
                  {device?.statut_assignation === 'assigne' ? (
                    <div className="protection-panels">
                      <div className="protection-panel">
                        <div className="panel-header">
                          <h4>🛡️ Protection Automatique</h4>
                          <Button
                            variant="primary"
                            size="small"
                            onClick={() => setShowProtectionModal(true)}
                          >
                            ⚙️ Configurer
                          </Button>
                        </div>
                        <div className="panel-content">
                          <p>La protection automatique surveille les seuils de tension, courant et température.</p>
                          <div className="protection-status">
                            <div className="status-item">
                              <span>Statut:</span>
                              <span className={`status-badge ${device.protection_automatique_active ? 'active' : 'inactive'}`}>
                                {device.protection_automatique_active ? '✅ Activée' : '❌ Désactivée'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="protection-panel">
                        <div className="panel-header">
                          <h4>⏰ Programmation Horaires</h4>
                          <Button
                            variant="primary"
                            size="small"
                            onClick={() => setShowScheduleModal(true)}
                          >
                            📅 Configurer
                          </Button>
                        </div>
                        <div className="panel-content">
                          <p>Programmez l'allumage et l'extinction automatique selon vos horaires.</p>
                          <div className="schedule-status">
                            <div className="status-item">
                              <span>Statut:</span>
                              <span className={`status-badge ${device.programmation_active ? 'active' : 'inactive'}`}>
                                {device.programmation_active ? '✅ Activée' : '❌ Désactivée'}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="protection-not-available">
                      <div className="empty-icon">🛡️</div>
                      <h4>Protection non disponible</h4>
                      <p>La protection et programmation ne sont disponibles que pour les appareils assignés.</p>
                    </div>
                  )}
                </div>
              )}

                          {showProtectionModal && (
              <ProtectionModal
                device={device}
                onClose={() => setShowProtectionModal(false)}
                onSave={() => {
                  setShowProtectionModal(false)
                  loadDeviceDetails()
                }}
              />
            )}

            {showScheduleModal && (
              <ScheduleModal
                device={device}
                onClose={() => setShowScheduleModal(false)}
                onSave={() => {
                  setShowScheduleModal(false)
                  loadDeviceDetails()
                }}
              />
            )}

                      {activeTab === 'alerts' && (
                        <div className="alerts-content">
                          {device?.statut_assignation === 'assigne' ? (
                            <div className="alerts-section">
                              <div className="alerts-header">
                                <h4>🔔 Historique des alertes</h4>
                                <Button
                                  variant="primary"
                                  size="small"
                                  onClick={() => setShowAlerts(true)}
                                >
                                  📊 Panneau détaillé
                                </Button>
                              </div>
                              
                              <div className="alerts-preview">
                                <AlertIndicator 
                                  device={device} 
                                  onClick={() => setShowAlerts(true)}
                                />
                                <p>Cliquez pour ouvrir le panneau détaillé des alertes</p>
                              </div>
                            </div>
                          ) : (
                            <div className="alerts-not-available">
                              <div className="empty-icon">🔔</div>
                              <h4>Alertes non disponibles</h4>
                              <p>Les alertes ne sont disponibles que pour les appareils assignés.</p>
                            </div>
                          )}
                        </div>
                      )}

                      
                      {showAlerts && (
                        <AlertPanel
                          device={device}
                          onClose={() => setShowAlerts(false)}
                        />
                      )}

          {/* Graphiques */}
          {activeTab === 'charts' && (
            <div className="charts-content">
              {/* MODIFICATION 21: Utiliser deviceFullDetails pour vérifier le statut d'assignation */}
              {deviceFullDetails?.statut_assignation === 'assigne' ? ( 
                <>
                  {/* MODIFICATION 22: Passer deviceFullDetails à QuickStatsPanel */}
                  <QuickStatsPanel device={deviceFullDetails} /> 
                  <div className="charts-section">
                    <div className="charts-header">
                      <h4>📈 Graphiques détaillés</h4>
                                 <Button
                                    variant="primary"
                                    onClick={() => setShowCharts(true)}
                                  >
                                    📊 Ouvrir les graphiques
                                  </Button>
                                </div>
                                
                                <div className="chart-previews">
                                  <p>Cliquez sur "Ouvrir les graphiques" pour voir les graphiques détaillés avec:</p>
                                  <ul>
                                    <li>⚡ Graphique de tension en temps réel</li>
                                    <li>🔌 Évolution du courant</li>
                                    <li>💡 Courbe de puissance</li>
                                    <li>📊 Statistiques avancées</li>
                                    <li>📈 Comparaison BDD vs Tuya</li>
                                    <li>💾 Export des données CSV</li>
                                  </ul>
                                </div>
                              </div>
                            </>
                          ) : (
                            <div className="charts-not-available">
                              <div className="empty-icon">📈</div>
                              <h4>Graphiques non disponibles</h4>
                              <p>Les graphiques ne sont disponibles que pour les appareils assignés.</p>
                            </div>
                          )}
                        </div>
                      )}
                      {showCharts && (
                        <div className="charts-modal-overlay">
                          {/* MODIFICATION 23: Passer deviceFullDetails à MultiChartView */}
                          <MultiChartView 
                            device={deviceFullDetails} 
                            onClose={() => setShowCharts(false)}
                          />
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
