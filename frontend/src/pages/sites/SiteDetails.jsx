import React from 'react'
import Button from '../../components/Button'
import siteService from '../../services/siteService'

const SiteDetails = ({ site, onBack, onEdit, onToggleStatus, isSuperadmin, isAdmin }) => {
  const hasCoordinates = site.latitude && site.longitude

  const handleGeocode = async () => {
    try {
      await siteService.geocoderSite(site.id)
      // Recharger les données du site après géocodage
      window.location.reload()
    } catch (error) {
      console.error('Erreur lors du géocodage:', error)
    }
  }

  const generateGoogleMapsLink = () => {
    if (hasCoordinates) {
      return `https://www.google.com/maps?q=${site.latitude},${site.longitude}`
    } else if (site.adresse_complete || site.adresse) {
      const address = encodeURIComponent(site.adresse_complete || site.adresse)
      return `https://www.google.com/maps/search/${address}`
    }
    return null
  }

  const googleMapsLink = generateGoogleMapsLink()

  return (
    <div className="site-details">
      <div className="site-details-header">
        <Button variant="outline" onClick={onBack} className="back-button">
          ← Retour à la liste
        </Button>
        <h1>Détails du Site</h1>
      </div>

      <div className="site-details-content">
        {/* Grande carte */}
        <div className="site-details-map">
          {hasCoordinates ? (
            <div className="large-map">
              {/* TODO: Implement large Leaflet map with marker */}
              <div className="map-placeholder">
                📍 Grande carte Leaflet avec marqueur<br/>
                Coordonnées: {site.latitude}, {site.longitude}
              </div>
            </div>
          ) : (
            <div className="no-coordinates">
              <p>🗺️ Aucune coordonnée GPS disponible</p>
              <Button variant="secondary" onClick={handleGeocode}>
                📍 Géocoder l'adresse
              </Button>
            </div>
          )}
        </div>

        {/* Informations détaillées */}
        <div className="site-info-grid">
          <div className="info-row">
            <span className="info-label">📛 Nom du site :</span>
            <span className="info-value">{site.nom_site}</span>
          </div>
          
          <div className="info-row">
            <span className="info-label">👤 Client :</span>
            <span className="info-value">{site.client_nom || 'N/A'}</span>
          </div>
          
          <div className="info-row">
            <span className="info-label">📬 Adresse complète :</span>
            <span className="info-value">
              {site.adresse_complete || 
               `${site.adresse || ''} ${site.quartier || ''} ${site.ville || ''} ${site.code_postal || ''}`.trim() || 
               'N/A'}
            </span>
          </div>
          
          {hasCoordinates && (
            <div className="info-row">
              <span className="info-label">🌍 Coordonnées GPS :</span>
              <span className="info-value">{site.latitude}, {site.longitude}</span>
            </div>
          )}
          
          <div className="info-row">
            <span className="info-label">📦 Nombre d'appareils :</span>
            <span className="info-value">{site.nb_appareils || 0}</span>
          </div>
          
          {site.contact_site && (
            <div className="info-row">
              <span className="info-label">📞 Contact :</span>
              <span className="info-value">
                {site.contact_site}
                {site.telephone_site && ` / ${site.telephone_site}`}
              </span>
            </div>
          )}
          
          <div className="info-row">
            <span className="info-label">🎛️ Statut :</span>
            <span className="info-value">
              <span className={`status-badge ${site.actif ? 'active' : 'inactive'}`}>
                {site.actif ? '✅ Actif' : '❌ Inactif'}
              </span>
            </span>
          </div>
          
          {site.pays && (
            <div className="info-row">
              <span className="info-label">🌍 Pays :</span>
              <span className="info-value">{site.pays}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="site-details-actions">
          <Button variant="primary" onClick={() => onEdit(site)}>
            ✏️ Modifier
          </Button>
          
          {(isSuperadmin || isAdmin) && (
            <Button 
              variant={site.actif ? 'danger' : 'success'} 
              onClick={() => onToggleStatus(site)}
            >
              {site.actif ? '❌ Désactiver' : '✅ Réactiver'}
            </Button>
          )}
          
          <Button variant="secondary" onClick={handleGeocode}>
            📍 Re-géocoder
          </Button>
        </div>

        {/* Lien Google Maps */}
        {googleMapsLink && (
          <div className="google-maps-link">
            <a 
              href={googleMapsLink} 
              target="_blank" 
              rel="noopener noreferrer"
              className="maps-link"
            >
              🔗 Ouvrir dans Google Maps
            </a>
          </div>
        )}
      </div>
    </div>
  )
}

export default SiteDetails