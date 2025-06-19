import React from 'react'
import Button from '../../components/Button'

const SiteCard = ({ site, onEdit, onDelete, onToggleStatus, onViewDetails, isSuperadmin, isAdmin }) => {
  const hasCoordinates = site.latitude && site.longitude

  return (
    <div className="site-card">
      <div className="site-card-map-container">
        {/* TODO: Implement Leaflet mini-map here if hasCoordinates is true */}
        {hasCoordinates ? (
          <div className="mini-map">
            📍 Mini-carte Leaflet ({site.latitude}, {site.longitude})
          </div>
        ) : (
          site.map_link ? (
            <a href={site.map_link} target="_blank" rel="noopener noreferrer" className="map-link">
              🗺️ Voir sur la carte
            </a>
          ) : (
            <div className="no-map">📍 Pas de coordonnées / lien carte</div>
          )
        )}
      </div>
      <div className="site-card-content">
        <h3>📌 {site.nom_site}</h3>
        <p><strong>👤 Client:</strong> {site.client_nom || 'N/A'}</p>
        <p><strong>📬 Adresse:</strong> {site.adresse_complete || site.adresse}</p>
        <p><strong>📦 Appareils:</strong> {site.nb_appareils || 0}</p>
        <p><strong>🎛️ Statut:</strong> <span className={`status-badge ${site.actif ? 'active' : 'inactive'}`}>{site.actif ? '✅ Actif' : '❌ Inactif'}</span></p>
      </div>
      <div className="site-card-actions">
        <Button variant="outline" size="small" onClick={() => onEdit(site)}>
          ✏️ Modifier
        </Button>
        {(isSuperadmin || isAdmin) && (
          <Button 
            variant="secondary" 
            size="small" 
            onClick={() => onToggleStatus(site)}
            className={site.actif ? 'btn-deactivate' : 'btn-activate'}
          >
            {site.actif ? '❌ Désactiver' : '✅ Réactiver'}
          </Button>
        )}
        {isSuperadmin && (
          <Button 
            variant="danger" 
            size="small" 
            onClick={() => onDelete(site)}
            className="btn-delete"
          >
            🗑️ Supprimer
          </Button>
        )}
        <Button 
          variant="primary" 
          size="small" 
          onClick={() => onViewDetails(site)}
          className="btn-details"
        >
          🔍 Détails
        </Button>
      </div>
    </div>
  )
}

export default SiteCard