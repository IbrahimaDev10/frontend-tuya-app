import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import ClientLayout from '../../layouts/ClientLayout'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import ToggleSwitch from '../../components/ToggleSwitch';
import Input from '../../components/Input'
import DeviceModal from './DeviceModal' // Non utilisé dans ce fichier, mais laissé pour référence
import AssignModal from './AssignModal'
import { useRealtimeContext } from '../../store/realtimeContext'
import DropdownMenu from '../../components/DropdownMenu'
import DeviceDetailsModal from './DeviceDetailsModal'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import ExportModal from '../../components/ExportModal'
import './DeviceManagement.css'
import MultiChartView from '../DeviceCharts/MultiChartView'
import AlertIndicator from '../../components/Alerts/AlertIndicator'
import AlertPanel from '../../components/Alerts/AlertPanel'
import { useNavigate } from 'react-router-dom';

const DeviceManagement = () => {
  const { isSuperadmin, isAdmin, isClient, user: currentUser } = useAuth()

  // --- MODIFICATION 1 : Logique d'initialisation de l'onglet ---
  // Pour admin et client, on force un onglet unique "mes_appareils".
  // Pour superadmin, on commence par "assigned" par défaut.
  const getDefaultTab = () => {
    if (isSuperadmin()) {
      return 'assigned';
    }
    // Pour admin et client, c'est toujours la même vue.
    return 'mes_appareils'; 
  };

  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTab, setSelectedTab] = useState(getDefaultTab) // Utilise la fonction pour l'état initial
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [selectedDevice, setSelectedDevice] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [stats, setStats] = useState({})
  const [toast, setToast] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [importing, setImporting] = useState(false)
  const [loadingDeviceIds, setLoadingDeviceIds] = useState([])

  const Layout = isSuperadmin() ? SuperAdminLayout : isAdmin() ? AdminLayout : ClientLayout
  const navigate = useNavigate();

  const [showAlertsPanel, setShowAlertsPanel] = useState(false)
  const [selectedDeviceForAlerts, setSelectedDeviceForAlerts] = useState(null)

  const [showChartsModal, setShowChartsModal] = useState(false)
  const [selectedDeviceForCharts, setSelectedDeviceForCharts] = useState(null)
  const [showExportModal, setShowExportModal] = useState(false)

    // ---  UTILISER LE HOOK POUR OBTENIR LES DONNÉES TEMPS RÉEL ---
  const { latestByDevice } = useRealtimeContext();


  useEffect(() => {
    loadData()
  }, [selectedTab, currentUser]) 


  useEffect(() => {
    if (latestByDevice.size === 0) {
      return; 
    }

    console.log("🔄 [Realtime] Détection d'un changement, mise à jour de la liste des appareils...");

    setDevices(prevDevices => 
      prevDevices.map(device => {
        const newData = latestByDevice.get(device.tuya_device_id);
        
        if (newData) {
          // --- MODIFICATION ICI ---
          // On vérifie si 'etat_switch' est défini dans les nouvelles données.
          // S'il est undefined ou null, on garde l'ancienne valeur.
          const newSwitchState = newData.etat_switch;

          return {
            ...device,
            // On s'assure que la valeur est toujours un booléen.
            // Si newSwitchState est undefined/null, on garde device.etat_actuel_tuya.
            etat_actuel_tuya: typeof newSwitchState === 'boolean' ? newSwitchState : device.etat_actuel_tuya,
          };
        }
        
        return device;
      })
    );

  }, [latestByDevice]);
  
  const loadData = async () => {
    try {
      setLoading(true)
      
      let devicesResponse;
      
      // --- MODIFICATION 2 : Simplification de la logique de chargement des données ---
      // Si l'utilisateur n'est pas superadmin, on charge toujours les appareils assignés.
      if (!isSuperadmin()) {
        devicesResponse = await DeviceService.listerAppareils();
      } else {
        // La logique du superadmin reste inchangée
        if (selectedTab === 'assigned') {
          devicesResponse = await DeviceService.listerAppareils();
        } else if (selectedTab === 'unassigned') {
          devicesResponse = await DeviceService.listerNonAssignes();
        } else { // 'all' tab
          devicesResponse = await DeviceService.listerAppareils(null, true);
        }
      }

      const statsResponse = await DeviceService.obtenirStatistiques();
      
      setDevices(devicesResponse.data.data || devicesResponse.data.devices || []);
      setStats(statsResponse.data.data || {});
      
    } catch (error) {
      showToast('Erreur lors du chargement des données', 'error')
      console.error('Erreur chargement:', error)
    } finally {
      setLoading(false)
    }
  }

  // ... (le reste de vos fonctions handle... reste identique)
  // handleShowAlerts, handleSearch, handleImportTuya, handleSyncTuya, handleToggleDevice, etc.
  // Aucune modification nécessaire dans les autres fonctions.

  // --- Le reste de votre composant jusqu'au rendu ---
  
  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }


  const handleShowAlerts = (device) => {
  setSelectedDeviceForAlerts(device)
  setShowAlertsPanel(true)
}

  const handleSearch = async (term) => {
    if (term.length < 2) {
      loadData()
      return
    }

    try {
      const siteIdToFilter = (currentUser && currentUser.role === 'user' && currentUser.site_id) ? currentUser.site_id : null;
      const response = await DeviceService.rechercherAppareils(term, siteIdToFilter);
      setDevices(response.data.data)
    } catch (error) {
      showToast('Erreur lors de la recherche', 'error')
    }
  }

  const handleImportTuya = async () => {
    if (!isSuperadmin()) return
    
    setImporting(true)
    try {
      const response = await DeviceService.importerAppareilsTuya()
      if (response.data.success) {
        showToast(response.data.message, 'success')
        loadData()
      } else {
        showToast(response.data.error, 'error')
      }
    } catch (error) {
      showToast('Erreur lors de l\'importation', 'error')
    } finally {
      setImporting(false)
    }
  }

  const handleSyncTuya = async () => {
    setSyncing(true)
    try {
      const response = await DeviceService.synchroniserTuya()
      if (response.data.success) {
        showToast(response.data.message, 'success')
        loadData()
      } else {
        showToast(response.data.error, 'error')
      }
    } catch (error) {
      showToast('Erreur lors de la synchronisation', 'error')
    } finally {
      setSyncing(false)
    }
  }

  const handleToggleDevice = async (device) => {
  const deviceId = device.tuya_device_id
  setLoadingDeviceIds((prev) => [...prev, deviceId])

  try {
    const newStateValue = !device.etat_actuel_tuya; 
    const result = await DeviceService.toggleAppareil(deviceId, newStateValue); 

    if (result.success) {
      showToast(result.message, 'success')
      setDevices(prev =>
        prev.map(d =>
          d.id === device.id
            ? { ...d, etat_actuel_tuya: result.newState }
            : d
        )
      )
    } else {
      showToast(result.message, 'error')
    }
  } catch (error) {
    showToast('Erreur lors du contrôle de l’appareil', 'error')
  } finally {
    setLoadingDeviceIds((prev) => prev.filter(id => id !== deviceId))
  }
}
  
  

              const handleAssignDevice = (device) => {
                setSelectedDevice(device)
                setShowAssignModal(true)
              }

              const handleCreateDevice = (device) => { 
                setSelectedDevice(device)
                setShowDeviceModal(true)
              }
  
  const handleUnassignDevice = (device) => {
    setConfirmAction({
      type: 'unassign',
      device,
      title: 'Désassigner l\'appareil',
      message: `Êtes-vous sûr de vouloir désassigner "${device.nom_appareil}" ?`,
      confirmText: 'Désassigner',
      onConfirm: () => confirmUnassignDevice(device)
    })
  }

  const confirmUnassignDevice = async (device) => {
    try {
      const response = await DeviceService.desassignerAppareil(device.tuya_device_id)
      if (response.data.success) {
        showToast(response.data.message, 'success')
        loadData()
      } else {
        showToast(response.data.message, 'error')
      }
    } catch (error) {
      showToast('Erreur lors de la désassignation', 'error')
    }
    setConfirmAction(null)
  }

  const handleDeviceDetails = (device) => {
    setSelectedDevice(device)
    setShowDetailsModal(true)
  }

  const handleDeviceAssigned = () => {
    setShowAssignModal(false)
    loadData()
    showToast('Appareil assigné avec succès', 'success')
  }

  const handleCollectData = async (device) => {
    try {
      const response = await DeviceService.collecterDonnees(device.id || device.tuya_device_id)
      if (response.data.success) {
        showToast('Données collectées avec succès', 'success')
      } else {
        showToast('Erreur lors de la collecte', 'error')
      }
    } catch (error) {
      showToast('Erreur lors de la collecte', 'error')
    }
  }

const handleShowCharts = (device) => {
  setSelectedDeviceForCharts(device)
  setShowChartsModal(true)
}

  const handleGoToConfigPage = (device) => {
    navigate(`/devices/config/${device.id}`);
  };

  const handleShowExportModal = () => {
    setShowExportModal(true);
  };

  if (loading) {
    return (
      <Layout>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Chargement des appareils...</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="device-management">
        <div className="device-management-header">
          {/* --- MODIFICATION 3 : Titre dynamique --- */}
          <h1>{isSuperadmin() ? 'Gestion des Appareils' : 'Mes Appareils'}</h1>
          <div className="header-actions">
            <Input
              type="text"
              placeholder="Rechercher un appareil..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                handleSearch(e.target.value)
              }}
              className="search-input"
            />
            <Button
              variant="secondary"
              onClick={handleSyncTuya}
              loading={syncing}
            >
              🔄 Synchroniser
            </Button>
            <Button
              variant="outline"
              onClick={handleShowExportModal}
            >
              📊 Exporter Rapport
            </Button>
            {isSuperadmin() && (
              <Button
                variant="primary"
                onClick={handleImportTuya}
                loading={importing}
              >
                📥 Importer Tuya
              </Button>
            )}
          </div>
        </div>

        {/* Statistiques */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">📱</div>
            <div className="stat-content">
              <h3>Total</h3>
              <div className="stat-number">{stats.total || 0}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h3>Assignés</h3>
              <div className="stat-number">{stats.assignes || 0}</div>
            </div>
          </div>
          {isSuperadmin() && (
            <div className="stat-card">
              <div className="stat-icon">❓</div>
              <div className="stat-content">
                <h3>Non assignés</h3>
                <div className="stat-number">{stats.non_assignes || 0}</div>
              </div>
            </div>
          )}
          <div className="stat-card">
            <div className="stat-icon">🟢</div>
            <div className="stat-content">
              <h3>En ligne</h3>
              <div className="stat-number">{stats.en_ligne || 0}</div>
            </div>
          </div>
        </div>

        {/* --- MODIFICATION 4 : Affichage conditionnel des onglets --- */}
        <div className="tabs">
          {isSuperadmin() ? (
            <>
              <button
                className={`tab ${selectedTab === 'assigned' ? 'active' : ''}`}
                onClick={() => setSelectedTab('assigned')}
              >
                Appareils assignés
              </button>
              <button
                className={`tab ${selectedTab === 'unassigned' ? 'active' : ''}`}
                onClick={() => setSelectedTab('unassigned')}
              >
                Non assignés ({stats.non_assignes || 0})
              </button>
              <button
                className={`tab ${selectedTab === 'all' ? 'active' : ''}`}
                onClick={() => setSelectedTab('all')}
              >
                Tous les appareils
              </button>
            </>
          ) : (
            // Pour admin et client, un seul onglet "Mes appareils" qui est toujours actif.
            <button className="tab active">Mes appareils</button>
          )}
        </div>

        {/* Tableau des appareils */}
        <DevicesTable
                devices={devices}
                onToggle={handleToggleDevice}
                onAssign={handleAssignDevice}
                onUnassign={handleUnassignDevice}
                onDetails={handleDeviceDetails}
                onCollectData={handleCollectData}
                onShowCharts={handleShowCharts}
                // --- MODIFICATION 5 : Logique d'affichage des actions ---
                // Seul le superadmin voit les actions d'assignation/désassignation
                showAssignActions={isSuperadmin() && (selectedTab === 'unassigned' || selectedTab === 'all')}
                isSuperadmin={isSuperadmin()}
                isClient={isClient()}
                onShowAlerts={handleShowAlerts}
                onGoToConfigPage={handleGoToConfigPage}
                currentUserRole={currentUser?.role}
                 loadingDeviceIds={loadingDeviceIds}
              />
        
        {/* ... (Le reste du composant avec les Modals reste identique) ... */}
        {showAssignModal && (
          <AssignModal
            device={selectedDevice}
            onClose={() => setShowAssignModal(false)}
            onSuccess={handleDeviceAssigned}
          />
        )}
                  {showAlertsPanel && selectedDeviceForAlerts && (
                    <AlertPanel
                      device={selectedDeviceForAlerts}
                      onClose={() => {
                        setShowAlertsPanel(false)
                        setSelectedDeviceForAlerts(null)
                      }}
                    />
                  )}


              {showChartsModal && selectedDeviceForCharts && (
                <div className="charts-modal-overlay">
                  <MultiChartView
                    device={selectedDeviceForCharts}
                    onClose={() => {
                      setShowChartsModal(false)
                      setSelectedDeviceForCharts(null)
                    }}
                  />
                </div>
              )}

        {showDetailsModal && (
          <DeviceDetailsModal
            device={selectedDevice}
            onClose={() => setShowDetailsModal(false)}
          />
        )}

        {confirmAction && (
          <ConfirmModal
            title={confirmAction.title}
            message={confirmAction.message}
            confirmText={confirmAction.confirmText}
            onConfirm={confirmAction.onConfirm}
            onCancel={() => setConfirmAction(null)}
            variant="danger"
          />
        )}

        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}

        {showChartsModal && selectedDeviceForCharts && (
          <MultiChartView
            device={selectedDeviceForCharts}
            onClose={() => setShowChartsModal(false)}
          />
        )}

        {showAlertsPanel && selectedDeviceForAlerts && (
          <AlertPanel
            device={selectedDeviceForAlerts}
            onClose={() => setShowAlertsPanel(false)}
          />
        )}

        {showExportModal && (
          <ExportModal
            isOpen={showExportModal}
            onClose={() => setShowExportModal(false)}
            clientId={currentUser?.client_id || ''}
            clientName={currentUser?.nom || ''}
          />
        )}
      </div>
    </Layout>
  )
}

// Le composant DevicesTable reste inchangé, car la logique est gérée dans le composant parent.
// Composant tableau des appareils (VERSION CORRIGÉE)
const DevicesTable = ({ 
  devices, 
  onToggle, 
  onAssign, 
  onUnassign, 
  onDetails, 
  onCollectData,
  onShowCharts,
  showAssignActions,
  isSuperadmin,
  isClient,
  onShowAlerts,
  onGoToConfigPage,
  currentUserRole,
  loadingDeviceIds 
}) => (
  <div className="table-container">
    <table className="data-table">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Type</th>
          <th>Statut</th>
          <th>État</th>
          {isSuperadmin && <th>Client</th>}
          {(isSuperadmin || currentUserRole === 'admin') && <th>Site</th>} 
          <th>En ligne</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {devices.map(device => (
          <tr key={device.id || device.tuya_device_id}>
            <td>
              <div className="device-name">
                <strong>{device.nom_appareil}</strong>
                <small>{device.tuya_device_id}</small>
              </div>
            </td>
            <td>
              <span className={`type-badge type-${device.type_systeme?.replace('_', '-')}`}>
                {device.type_systeme || 'N/A'}
              </span>
            </td>
           
            <td>
              <span className={`status-badge ${device.statut_assignation === 'assigne' ? 'assigned' : 'unassigned'}`}>
                {device.statut_assignation === 'assigne' ? 'Assigné' : 'Non assigné'}
              </span>
            </td>
           
            <td>
              {device.statut_assignation === 'assigne' && !isClient && currentUserRole !== 'user' ? (
                <ToggleSwitch 
                  isOn={device.etat_actuel_tuya}
                  onToggle={() => onToggle(device)}
                  isLoading={loadingDeviceIds.includes(device.tuya_device_id)}
                  isDisabled={!device.en_ligne}
                />
              ) : (
                <span className={`state-badge ${device.etat_actuel_tuya ? 'on' : 'off'}`}>
                  {device.etat_actuel_tuya ? 'ON' : 'OFF'}
                </span>
              )}
            </td>
            {isSuperadmin && (
              <td>{device.client?.nom_entreprise || 'N/A'}</td>
            )}
            {(isSuperadmin || currentUserRole === 'admin') && (
              <td>{device.site?.nom_site || 'N/A'}</td>
            )}
            <td>
              <span className={`online-badge ${device.en_ligne ? 'online' : 'offline'}`}>
                {device.en_ligne ? '🟢' : '🔴'}
              </span>
            </td>
            <td>
              <div className="action-buttons">
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onDetails(device)}
                  title="Détails"
                >
                  👁️ Détails
                </Button>
                
                {device.statut_assignation === 'assigne' && (
                  <Button
                    variant="outline"
                    size="small"
                    onClick={() => onShowAlerts(device)}
                    title="Voir les alertes"
                  >
                    🔔
                  </Button>
                )}

                <DropdownMenu icon="•••" title="Plus d'actions">
                  {device.statut_assignation === 'assigne' && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onShowCharts(device)}
                      title="Voir les graphiques"
                    >
                      📈 Voir les graphiques
                    </Button>
                  )}
                  
                  {device.statut_assignation === 'assigne' && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onCollectData(device)}
                      title="Collecter données"
                    >
                      📊 Collecter données
                    </Button>
                  )}
                  
                  {isSuperadmin && device.statut_assignation !== 'assigne' && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onAssign(device)}
                      title="Assigner"
                    >
                      📎 Assigner
                    </Button>
                  )}
                  
                  {isSuperadmin && device.statut_assignation === 'assigne' && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onUnassign(device)}
                      title="Désassigner"
                    >
                      ✂️ Désassigner
                    </Button>
                  )}
                </DropdownMenu>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    
    {devices.length === 0 && (
      <div className="empty-state">
        <p>Aucun appareil trouvé</p>
      </div>
    )}
  </div>
);



export default DeviceManagement