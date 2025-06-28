import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import ClientLayout from '../../layouts/ClientLayout'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import DeviceModal from './DeviceModal'
import AssignModal from './AssignModal'
import DeviceDetailsModal from './DeviceDetailsModal'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import './DeviceManagement.css'
import MultiChartView from '../DeviceCharts/MultiChartView'

const DeviceManagement = () => {
  const { isSuperadmin, isAdmin, isClient } = useAuth()
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTab, setSelectedTab] = useState('assigned')
  const [showDeviceModal, setShowDeviceModal] = useState(false)
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

  const [showChartsModal, setShowChartsModal] = useState(false)
  const [selectedDeviceForCharts, setSelectedDeviceForCharts] = useState(null)


  useEffect(() => {
    loadData()
  }, [selectedTab])

  const loadData = async () => {
    try {
      setLoading(true)
      
      let devicesResponse
      if (selectedTab === 'assigned') {
        devicesResponse = await DeviceService.listerAppareils()
      } else if (selectedTab === 'unassigned' && isSuperadmin()) {
        devicesResponse = await DeviceService.listerNonAssignes()
      } else {
        devicesResponse = await DeviceService.listerAppareils(null, isSuperadmin())
      }

      const statsResponse = await DeviceService.obtenirStatistiques()
      
      setDevices(devicesResponse.data.data || devicesResponse.data.devices || [])
      setStats(statsResponse.data.data || {})
      
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

  const handleSearch = async (term) => {
    if (term.length < 2) {
      loadData()
      return
    }

    try {
      const response = await DeviceService.rechercherAppareils(term)
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
      const result = await DeviceService.toggleAppareil(deviceId)
  
      if (result.success) {
        showToast(result.message, 'success')
  
        setDevices(prev =>
          prev.map(d =>
            d.id === device.id
              ? { ...d, etat_switch: result.newState }
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

  //  fonction pour ouvrir les graphiques
const handleShowCharts = (device) => {
  setSelectedDeviceForCharts(device)
  setShowChartsModal(true)
}

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
              />
                      {/* Modals */}
        {showAssignModal && (
          <AssignModal
            device={selectedDevice}
            onClose={() => setShowAssignModal(false)}
            onSuccess={handleDeviceAssigned}
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
  isClient
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
              <span className={`state-badge ${device.etat_switch ? 'on' : 'off'}`}>
                {device.etat_switch ? 'ON' : 'OFF'}
              </span>
            </td>
            {isSuperadmin && (
              <td>{device.client?.nom_entreprise || 'N/A'}</td>
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
                  👁️
                </Button>
                
                {device.statut_assignation === 'assigne' && (
                  <Button
                    variant="outline"
                    size="small"
                    onClick={() => onShowCharts(device)}
                    title="Voir les graphiques"
                  >
                    📈
                  </Button>
                )}
                
                {device.statut_assignation === 'assigne' && !isClient && (
                  <Button
                    variant="outline"
                    size="small"
                    onClick={() => onToggle(device)}
                    title="Toggle ON/OFF"
                  >
                    {device.etat_switch ? '⏸️' : '▶️'}
                  </Button>
                )}
                
                {device.statut_assignation === 'assigne' && (
                  <Button
                    variant="outline"
                    size="small"
                    onClick={() => onCollectData(device)}
                    title="Collecter données"
                  >
                    📊
                  </Button>
                )}
                
                {showAssignActions && device.statut_assignation !== 'assigne' && (
                  <Button
                    variant="primary"
                    size="small"
                    onClick={() => onAssign(device)}
                    title="Assigner"
                  >
                    📎
                  </Button>
                )}
                
                {showAssignActions && device.statut_assignation === 'assigne' && isSuperadmin && (
                  <Button
                    variant="secondary"
                    size="small"
                    onClick={() => onUnassign(device)}
                    title="Désassigner"
                  >
                    ✂️
                  </Button>
                )}
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