import { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import SiteService from '../../services/siteService'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import SiteModal from '../Sites/SiteModal'
import SiteDetailsModal from './SiteDetailsModal'
import SiteCard from './SiteCard'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import './SiteManagement.css'
import SiteMap from './SiteMap'


const SiteManagement = () => {
  const { isSuperadmin, isAdmin } = useAuth()
  const [sites, setSites] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedClient, setSelectedClient] = useState('')
  const [viewMode, setViewMode] = useState('cards') // 'cards' ou 'map'
  const [showSiteModal, setShowSiteModal] = useState(false)
  const [showDetailsModal, setShowDetailsModal] = useState(false)
  const [selectedSite, setSelectedSite] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [stats, setStats] = useState({})
  const [toast, setToast] = useState(null)

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const sitesPerPage = 3

  const indexOfLastSite = currentPage * sitesPerPage
  const indexOfFirstSite = indexOfLastSite - sitesPerPage
  const currentSites = sites.slice(indexOfFirstSite, indexOfLastSite)
  const totalPages = Math.ceil(sites.length / sitesPerPage)


  const Layout = isSuperadmin() ? SuperAdminLayout : AdminLayout

  useEffect(() => {
    loadData()
    if (isSuperadmin()) {
      loadClients()
    }
  }, [selectedClient])

  const loadData = async () => {
    try {
      setLoading(true)
      
      const [sitesResponse, statsResponse] = await Promise.all([
        SiteService.listerSites(selectedClient || null),
        SiteService.obtenirStatistiques(selectedClient || null)
      ])
      
      setSites(sitesResponse.data.data || [])
      setStats(statsResponse.data.data || {})
      
    } catch (error) {
      showToast('Erreur lors du chargement des données', 'error')
      console.error('Erreur chargement:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadClients = async () => {
    try {
      const response = await UserService.listerClients()
      setClients(response.data.data || [])
    } catch (error) {
      console.error('Erreur chargement clients:', error)
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
      const response = await SiteService.rechercherSites(term)
      setSites(response.data.data)
    } catch (error) {
      showToast('Erreur lors de la recherche', 'error')
    }
  }

  const handleCreateSite = () => {
    setSelectedSite(null)
    setShowSiteModal(true)
  }

  const handleEditSite = (site) => {
    setSelectedSite(site)
    setShowSiteModal(true)
  }

  const handleSiteDetails = (site) => {
    setSelectedSite(site)
    setShowDetailsModal(true)
  }

  const handleSiteSaved = () => {
    setShowSiteModal(false)
    loadData()
    showToast('Site sauvegardé avec succès', 'success')
  }

  const handleDeactivateSite = (site) => {
    const action = site.actif ? 'désactiver' : 'réactiver'
    setConfirmAction({
      type: 'toggleSite',
      site,
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} le site`,
      message: `Êtes-vous sûr de vouloir ${action} "${site.nom_site}" ?`,
      confirmText: action.charAt(0).toUpperCase() + action.slice(1),
      onConfirm: () => toggleSiteStatus(site)
    })
  }

  const handleDeleteSite = (site) => {
    setConfirmAction({
      type: 'deleteSite',
      site,
      title: 'Supprimer le site',
      message: `Êtes-vous sûr de vouloir supprimer "${site.nom_site}" ? Cette action est irréversible.`,
      confirmText: 'Supprimer',
      onConfirm: () => confirmDeleteSite(site.id)
    })
  }

  const toggleSiteStatus = async (site) => {
    try {
      if (site.actif) {
        await SiteService.desactiverSite(site.id)
      } else {
        await SiteService.reactiverSite(site.id)
      }
      loadData()
      showToast(`Site ${site.actif ? 'désactivé' : 'réactivé'} avec succès`, 'success')
    } catch (error) {
      showToast(error.response?.data?.error || 'Erreur lors de l\'opération', 'error')
    }
    setConfirmAction(null)
  }

  const confirmDeleteSite = async (siteId) => {
    try {
      await SiteService.supprimerSite(siteId)
      loadData()
      showToast('Site supprimé avec succès', 'success')
    } catch (error) {
      showToast(error.response?.data?.error || 'Erreur lors de la suppression', 'error')
    }
    setConfirmAction(null)
  }

  const handleGeocodeSite = async (site) => {
    try {
      const response = await SiteService.geocoderSite(site.id)
      if (response.data.success) {
        showToast('Géocodage effectué avec succès', 'success')
        loadData()
      } else {
        showToast(response.data.message, 'error')
      }
    } catch (error) {
      showToast('Erreur lors du géocodage', 'error')
    }
  }

  

  if (loading) {
    return (
      <Layout>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Chargement des sites...</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="site-management">
        <div className="site-management-header">
          <h1>Gestion des Sites</h1>
          <div className="header-actions">
            <Input
              type="text"
              placeholder="Rechercher un site..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                handleSearch(e.target.value)
              }}
              className="search-input"
            />
            
            {isSuperadmin() && (
              <select
                value={selectedClient}
                onChange={(e) => setSelectedClient(e.target.value)}
                className="client-filter"
              >
                <option value="">Tous les clients</option>
                {clients.map(client => (
                  <option key={client.id} value={client.id}>
                    {client.nom_entreprise}
                  </option>
                ))}
              </select>
            )}

            <div className="view-toggles">
              <Button
                variant={viewMode === 'cards' ? 'primary' : 'outline'}
                size="small"
                onClick={() => setViewMode('cards')}
              >
                🃏 Cartes
              </Button>
              <Button
                variant={viewMode === 'map' ? 'primary' : 'outline'}
                size="small"
                onClick={() => setViewMode('map')}
              >
                🗺️ Carte
              </Button>
            </div>

            {isSuperadmin() && (
              <Button
                variant="primary"
                onClick={handleCreateSite}
              >
                + Nouveau site
              </Button>
            )}
          </div>
        </div>

        {/* Statistiques */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🏢</div>
            <div className="stat-content">
              <h3>Total Sites</h3>
              <div className="stat-number">{stats.total_sites || 0}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h3>Sites Actifs</h3>
              <div className="stat-number">{stats.sites_actifs || 0}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📍</div>
            <div className="stat-content">
              <h3>Géocodés</h3>
              <div className="stat-number">{stats.sites_geocodes || 0}</div>
              <small>{stats.taux_geocodage || 0}%</small>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📱</div>
            <div className="stat-content">
              <h3>Appareils</h3>
              <div className="stat-number">{stats.total_appareils || 0}</div>
            </div>
          </div>
        </div>

        {/* Contenu principal */}
        {viewMode === 'cards' ? (
          <SitesCardsView
  sites={currentSites}
  onEdit={handleEditSite}
  onDetails={handleSiteDetails}
  onToggleStatus={handleDeactivateSite}
  onDelete={handleDeleteSite}
  onGeocode={handleGeocodeSite}
  isSuperadmin={isSuperadmin()}
  currentPage={currentPage}
  totalPages={totalPages}
  setCurrentPage={setCurrentPage}
/>

          
        ) : (
          <SitesMapView
            sites={sites}
            onSiteClick={handleSiteDetails}
          />
        )}

        {/* Modals */}
        {showSiteModal && (
          <SiteModal
            site={selectedSite}
            onClose={() => setShowSiteModal(false)}
            onSave={handleSiteSaved}
          />
        )}

        {showDetailsModal && (
          <SiteDetailsModal
            site={selectedSite}
            onClose={() => setShowDetailsModal(false)}
            onEdit={() => {
              setShowDetailsModal(false)
              handleEditSite(selectedSite)
            }}
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

// Composant vue en cartes
const SitesCardsView = ({ 
  sites, 
  onEdit, 
  onDetails, 
  onToggleStatus, 
  onDelete, 
  onGeocode,
  isSuperadmin,
  currentPage,
  totalPages,
  setCurrentPage
}) => (
  <div className="sites-cards-container">
    {sites.length > 0 ? (
      <>
        <div className="sites-grid">
          {sites.map(site => (
            <SiteCard
              key={site.id}
              site={site}
              onEdit={onEdit}
              onDetails={onDetails}
              onToggleStatus={onToggleStatus}
              onDelete={onDelete}
              onGeocode={onGeocode}
              isSuperadmin={isSuperadmin}
            />
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button 
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Précédent
            </button>
            <span>Page {currentPage} / {totalPages}</span>
            <button 
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Suivant
            </button>
          </div>
        )}
      </>
    ) : (
      <div className="empty-state">
        <div className="empty-icon">🏢</div>
        <h3>Aucun site trouvé</h3>
        <p>Aucun site ne correspond à vos critères de recherche.</p>
      </div>
    )}
  </div>
)


// Composant vue carte
const SitesMapView = ({ sites, onSiteClick }) => (
  <div className="sites-map-container">
    <SiteMap 
      sites={sites}
      onSiteClick={onSiteClick}
    />
  </div>
)

export default SiteManagement
