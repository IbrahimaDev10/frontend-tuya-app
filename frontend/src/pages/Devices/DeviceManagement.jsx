import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import ClientLayout from '../../layouts/ClientLayout'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import DeviceModal from './DeviceModal' // Non utilisé dans ce fichier, mais laissé pour référence
import AssignModal from './AssignModal'
import DropdownMenu from '../../components/DropdownMenu'
import DeviceDetailsModal from './DeviceDetailsModal'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import './DeviceManagement.css'
import MultiChartView from '../DeviceCharts/MultiChartView'
import AlertIndicator from '../../components/Alerts/AlertIndicator'
import AlertPanel from '../../components/Alerts/AlertPanel'
import { useNavigate } from 'react-router-dom';

const DeviceManagement = () => {
  const { isSuperadmin, isAdmin, isClient, user: currentUser } = useAuth() // <-- NOUVEAU : Récupérez l'utilisateur courant
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTab, setSelectedTab] = useState('assigned')
  const [showDeviceModal, setShowDeviceModal] = useState(false) // Non utilisé
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
  const navigate = useNavigate(); // <-- ÉTAPE 1 : Initialiser useNavigate

const [showAlertsPanel, setShowAlertsPanel] = useState(false)
const [selectedDeviceForAlerts, setSelectedDeviceForAlerts] = useState(null)

  const [showChartsModal, setShowChartsModal] = useState(false)
  const [selectedDeviceForCharts, setSelectedDeviceForCharts] = useState(null)


  useEffect(() => {
    loadData()
  }, [selectedTab, currentUser]) // <-- NOUVEAU : Ajoutez currentUser comme dépendance
  
  const loadData = async () => {
    try {
      setLoading(true)
      
      let devicesResponse
      let siteIdToFilter = null;

      // <-- NOUVEAU : Logique de filtrage par site pour les utilisateurs simples
      if (currentUser && currentUser.role === 'user' && currentUser.site_id) {
        siteIdToFilter = currentUser.site_id;
        // Pour un utilisateur simple, on ne montre que les appareils de son site,
        // donc les onglets "unassigned" et "all" n'ont pas de sens ou doivent être adaptés.
        // Ici, on force à "assigned" pour simplifier.
        if (selectedTab !== 'assigned') {
          setSelectedTab('assigned'); // Force l'onglet à "assigned"
        }
      }

      if (selectedTab === 'assigned') {
        devicesResponse = await DeviceService.listerAppareils(siteIdToFilter); // <-- Passez siteIdToFilter
      } else if (selectedTab === 'unassigned' && isSuperadmin()) {
        devicesResponse = await DeviceService.listerNonAssignes();
      } else { // 'all' tab
        devicesResponse = await DeviceService.listerAppareils(siteIdToFilter, isSuperadmin()); // <-- Passez siteIdToFilter
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
      // Pour la recherche, nous devons aussi potentiellement filtrer par site
      const siteIdToFilter = (currentUser && currentUser.role === 'user' && currentUser.site_id) ? currentUser.site_id : null;
      const response = await DeviceService.rechercherAppareils(term, siteIdToFilter); // <-- Passez siteIdToFilter
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
    // Déterminez le nouvel état souhaité basé sur l'état actuel de Tuya
    // Si device.etat_actuel_tuya est True (ON), le nouvel état souhaité est False (OFF)
    // Si device.etat_actuel_tuya est False (OFF), le nouvel état souhaité est True (ON)
    const newStateValue = !device.etat_actuel_tuya; 
    
    // Appelez le service avec le deviceId Tuya et le nouvel état souhaité
    const result = await DeviceService.toggleAppareil(deviceId, newStateValue); 

    if (result.success) {
      showToast(result.message, 'success')

      // Mettez à jour l'état local des appareils avec le nouvel état reçu du backend
      setDevices(prev =>
        prev.map(d =>
          d.id === device.id
            ? { ...d, etat_actuel_tuya: result.newState } // Utilisez le nouveau champ
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

              const handleCreateDevice = (device) => { // Non utilisé
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

  //  fonction pour ouvrir les graphiques
const handleShowCharts = (device) => {
  setSelectedDeviceForCharts(device)
  setShowChartsModal(true)
}

  // <-- ÉTAPE 2 : Créer la fonction de navigation vers la page de configuration
  const handleGoToConfigPage = (device) => {
    navigate(`/devices/config/${device.id}`);
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
          <h1>Gestion des Appareils</h1>
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

        {/* Onglets */}
        {/* <-- NOUVEAU : Affichage conditionnel des onglets */}
        {currentUser && currentUser.role !== 'user' ? (
          <div className="tabs">
            <button
              className={`tab ${selectedTab === 'assigned' ? 'active' : ''}`}
              onClick={() => setSelectedTab('assigned')}
            >
              Appareils assignés
            </button>
            {isSuperadmin() && (
              <button
                className={`tab ${selectedTab === 'unassigned' ? 'active' : ''}`}
                onClick={() => setSelectedTab('unassigned')}
              >
                Non assignés ({stats.non_assignes || 0})
              </button>
            )}
            <button
              className={`tab ${selectedTab === 'all' ? 'active' : ''}`}
              onClick={() => setSelectedTab('all')}
            >
              Tous les appareils
            </button>
          </div>
        ) : (
          // Pour les utilisateurs simples, un seul onglet "Mes appareils"
          <div className="tabs">
            <button className="tab active">Mes appareils</button>
          </div>
        )}

        {/* Tableau des appareils */}
        <DevicesTable
                devices={devices}
                onToggle={handleToggleDevice}
                onAssign={handleAssignDevice}
                onUnassign={handleUnassignDevice}
                onDetails={handleDeviceDetails}
                onCollectData={handleCollectData}
                onShowCharts={handleShowCharts} // Nouvelle prop
                showAssignActions={selectedTab === 'unassigned' || isSuperadmin()}
                isSuperadmin={isSuperadmin()}
                isClient={isClient()}
                onShowAlerts={handleShowAlerts}
                onGoToConfigPage={handleGoToConfigPage}
                currentUserRole={currentUser?.role} // <-- NOUVEAU : Passez le rôle de l'utilisateur
              />
                      {/* Modals */}
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
      </div>
    </Layout>
  )
}

// Composant tableau des appareils
const DevicesTable = ({ 
  devices, 
  onToggle, 
  onAssign, 
  onUnassign, 
  onDetails, 
  onCollectData,
  onShowCharts, // Nouvelle prop
  showAssignActions,
  isSuperadmin,
  isClient,
   onShowAlerts,
  onGoToConfigPage, // <-- NOUVEAU : Prop pour la navigation
  currentUserRole // <-- NOUVEAU : Récupérez le rôle ici
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
          {/* <-- NOUVEAU : Afficher la colonne Site si Superadmin ou Admin */}
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
              <span className={`type-badge type-${device.type_appareil?.replace('_', '-')}`}>
                {device.type_appareil || 'N/A'}
              </span>
            </td>
            <td>
              <span className={`status-badge ${device.statut_assignation === 'assigne' ? 'assigned' : 'unassigned'}`}>
                {device.statut_assignation === 'assigne' ? 'Assigné' : 'Non assigné'}
              </span>
            </td>
            <td>
              <span className={`state-badge ${device.etat_actuel_tuya ? 'on' : 'off'}`}>
                {device.etat_actuel_tuya ? 'ON' : 'OFF'}
              </span>
            </td>
            {isSuperadmin && (
              <td>{device.client?.nom_entreprise || 'N/A'}</td>
            )}
            {/* <-- NOUVEAU : Afficher le nom du site */}
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
                {/* Bouton Détails (toujours visible) */}
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onDetails(device)}
                  title="Détails"
                >
                  👁️ Détails
                </Button>
                
                {/* Bouton ON/OFF (visible si assigné et contrôlable) */}
                {device.statut_assignation === 'assigne' && !isClient && currentUserRole !== 'user' && (
                  <Button
                    variant="outline"
                    size="small"
                    onClick={() => onToggle(device)}
                    title="Toggle ON/OFF"
                  >
                    {device.etat_actuel_tuya ? '⏸️ OFF'  : '▶️ ON'}
                  </Button>
                )}
                
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

                {/* Bouton "Plus d'actions" avec menu déroulant */}
                <DropdownMenu icon="•••" title="Plus d'actions">
                  {/* Les autres boutons vont ici */}

                  {/* Bouton Voir les graphiques */}
                  {device.statut_assignation === 'assigne' && (
                    <Button
                      variant="text" // Utilisez 'text' pour un style de lien dans le menu
                      size="small"
                      onClick={() => onShowCharts(device)}
                      title="Voir les graphiques"
                    >
                      📈 Voir les graphiques
                    </Button>
                  )}
                  
                  {/* Bouton Collecter données */}
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
                  
                  {/* Bouton Configurer l'appareil */}
                  {device.statut_assignation === 'assigne' && (isSuperadmin || currentUserRole === 'admin') && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onGoToConfigPage(device)}
                      title="Configurer l'appareil"
                    >
                      ⚙️ Configurer
                    </Button>
                  )}

                  {/* Bouton Assigner (si non assigné et l'action est visible) */}
                  {showAssignActions && device.statut_assignation !== 'assigne' && currentUserRole !== 'user' && (
                    <Button
                      variant="text"
                      size="small"
                      onClick={() => onAssign(device)}
                      title="Assigner"
                    >
                      📎 Assigner
                    </Button>
                  )}
                  
                  {/* Bouton Désassigner (si assigné et Superadmin) */}
                  {showAssignActions && device.statut_assignation === 'assigne' && isSuperadmin && (
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
)


export default DeviceManagement
