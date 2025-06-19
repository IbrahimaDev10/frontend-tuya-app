import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import siteService from '../../services/siteService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import SiteModal from './SiteModal'
import SiteCard from './SiteCard'
import SiteDetails from './SiteDetails'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import './SiteManagement.css'

const SiteManagement = () => {
  const { isSuperadmin, isAdmin } = useAuth()
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [showSiteModal, setShowSiteModal] = useState(false)
  const [selectedSite, setSelectedSite] = useState(null)
  const [showSiteDetails, setShowSiteDetails] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)
  const [stats, setStats] = useState({})
  const [toast, setToast] = useState(null)

  const Layout = isSuperadmin() ? SuperAdminLayout : AdminLayout

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [sitesResponse, statsResponse] = await Promise.all([
        siteService.listerSites(),
        siteService.obtenirStatistiques()
      ])
      setSites(sitesResponse.data.data || sitesResponse.data.sites || [])
      setStats(statsResponse.data.data || statsResponse.data || {})
    } catch (error) {
      showToast('Erreur lors du chargement des données', 'error')
      console.error('Erreur:', error)
    } finally {
      setLoading(false)
    }
  }

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const handleSearch = async (term) => {
    setSearchTerm(term)
    if (term.length < 2) {
      loadData()
      return
    }

    try {
      const response = await siteService.rechercherSites(term)
      setSites(response.data.data || response.data.sites || [])
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

  const handleViewDetails = (site) => {
    setSelectedSite(site)
    setShowSiteDetails(true)
  }

  const handleToggleStatus = (site) => {
    setConfirmAction({
      type: site.actif ? 'deactivate' : 'activate',
      site,
      title: site.actif ? 'Désactiver le site' : 'Réactiver le site',
      message: `Êtes-vous sûr de vouloir ${site.actif ? 'désactiver' : 'réactiver'} le site "${site.nom_site}" ?`,
      confirmText: site.actif ? 'Désactiver' : 'Réactiver',
      onConfirm: () => toggleSiteStatus(site)
    })
  }

  const handleDeleteSite = (site) => {
    setConfirmAction({
      type: 'delete',
      site,
      title: 'Supprimer le site',
      message: `Êtes-vous sûr de vouloir supprimer définitivement le site "${site.nom_site}" ?\n\nCette action est irréversible.`,
      confirmText: 'Supprimer',
      onConfirm: () => deleteSite(site),
      variant: 'danger'
    })
  }

  const toggleSiteStatus = async (site) => {
    try {
      if (site.actif) {
        await siteService.desactiverSite(site.id)
        showToast('Site désactivé avec succès', 'success')
      } else {
        await siteService.reactiverSite(site.id)
        showToast('Site réactivé avec succès', 'success')
      }
      loadData()
    } catch (error) {
      showToast('Erreur lors de la modification du statut', 'error')
    }
    setConfirmAction(null)
  }

  const deleteSite = async (site) => {
    try {
      await siteService.supprimerSite(site.id)
      showToast('Site supprimé avec succès', 'success')
      loadData()
    } catch (error) {
      showToast('Erreur lors de la suppression', 'error')
    }
    setConfirmAction(null)
  }

  const handleSiteModalClose = () => {
    setShowSiteModal(false)
    setSelectedSite(null)
  }

  const handleSiteModalSave = () => {
    setShowSiteModal(false)
    setSelectedSite(null)
    loadData()
    showToast('Site sauvegardé avec succès', 'success')
  }

  const handleBackToList = () => {
    setShowSiteDetails(false)
    setSelectedSite(null)
  }

  const filteredSites = sites.filter(site =>
    site.nom_site?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    site.client_nom?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    site.adresse?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (showSiteDetails && selectedSite) {
    return (
      <Layout>
        <SiteDetails
          site={selectedSite}
          onBack={handleBackToList}
          onEdit={handleEditSite}
          onToggleStatus={handleToggleStatus}
          isSuperadmin={isSuperadmin()}
          isAdmin={isAdmin()}
        />
        {showSiteModal && (
          <SiteModal
            site={selectedSite}
            onClose={handleSiteModalClose}
            onSave={handleSiteModalSave}
          />
        )}
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
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
              onChange={(e) => handleSearch(e.target.value)}
              className="search-input"
            />
            <Button onClick={handleCreateSite}>+ Nouveau Site</Button>
          </div>
        </div>

        {/* Statistiques */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">🏢</div>
            <div className="stat-content">
              <h3>Total Sites</h3>
              <p className="stat-number">{stats.total_sites || 0}</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">📱</div>
            <div className="stat-content">
              <h3>Total Appareils</h3>
              <p className="stat-number">{stats.total_appareils || 0}</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <h3>Sites Actifs</h3>
              <p className="stat-number">{stats.sites_actifs || 0}</p>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">❌</div>
            <div className="stat-content">
              <h3>Sites Inactifs</h3>
              <p className="stat-number">{stats.sites_inactifs || 0}</p>
            </div>
          </div>
        </div>

        {/* Liste des sites */}
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement des sites...</p>
          </div>
        ) : (
          <div className="sites-grid">
            {filteredSites.length > 0 ? (
              filteredSites.map(site => (
                <SiteCard
                  key={site.id}
                  site={site}
                  onEdit={handleEditSite}
                  onDelete={handleDeleteSite}
                  onToggleStatus={handleToggleStatus}
                  onViewDetails={handleViewDetails}
                  isSuperadmin={isSuperadmin()}
                  isAdmin={isAdmin()}
                />
              ))
            ) : (
              <div className="no-sites">
                <p>Aucun site trouvé</p>
                {searchTerm && (
                  <Button variant="outline" onClick={() => handleSearch('')}>
                    Effacer la recherche
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modals */}
      {showSiteModal && (
        <SiteModal
          site={selectedSite}
          onClose={handleSiteModalClose}
          onSave={handleSiteModalSave}
        />
      )}

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          confirmText={confirmAction.confirmText}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
          variant={confirmAction.variant}
        />
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </Layout>
  )
}

export default SiteManagement