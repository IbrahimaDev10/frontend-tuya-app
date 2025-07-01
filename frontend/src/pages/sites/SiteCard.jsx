import React from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import Button from '../../components/Button'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './sitecard.css'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// Fix pour les icônes Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const SiteCard = ({ 
  site, 
  onEdit, 
  onDetails, 
  onToggleStatus, 
  onDelete, 
  onGeocode,
  isSuperadmin 
}) => {
  const hasCoordinates = site.latitude && site.longitude

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('fr-FR')
  }

  return (
    <div className="site-card">
      {/* En-tête de la carte */}
      <div className="site-card-header">
        <div className="site-info">
          <h3 className="site-name">{site.nom_site}</h3>
          <div className="site-badges">
            <span className={`status-badge ${site.actif ? 'active' : 'inactive'}`}>
              {site.actif ? '✅ Actif' : '❌ Inactif'}
            </span>
            {hasCoordinates && (
              <span className="geo-badge">📍 Géocodé</span>
            )}
          </div>
        </div>
        <div className="site-actions">
          <Button
            variant="outline"
            size="small"
            onClick={() => onDetails(site)}
            title="Voir détails"
          >
            👁️
          </Button>
          {isSuperadmin && (
            <>
              <Button
                variant="outline"
                size="small"
                onClick={() => onEdit(site)}
                title="Modifier"
              >
                ✏️
              </Button>
              <Button
                variant="secondary"
                size="small"
                onClick={() => onToggleStatus(site)}
                title={site.actif ? 'Désactiver' : 'Réactiver'}
              >
                {site.actif ? '❌' : '✅'}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Carte mini Leaflet ou placeholder */}
      <div className="site-map-container">
        {hasCoordinates ? (
          <MapContainer
            center={[site.latitude, site.longitude]}
            zoom={13}
            style={{ height: '200px', width: '100%' }}
            className="site-mini-map"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            <Marker position={[site.latitude, site.longitude]}>
              <Popup>
                <div className="popup-content">
                  <strong>{site.nom_site}</strong><br />
                  {site.adresse}
                </div>
              </Popup>
            </Marker>
          </MapContainer>
        ) : (
          <div className="map-placeholder">
            <div className="placeholder-content">
              <div className="placeholder-icon">📍</div>
              <p>Coordonnées non disponibles</p>
              {isSuperadmin && (
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onGeocode(site)}
                >
                  🌍 Géocoder
                </Button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Informations du site */}
      <div className="site-card-body">
        <div className="site-address">
          <strong>📍 Adresse :</strong>
          <p>{site.adresse}</p>
          {site.ville && (
            <p className="city-info">{site.ville}{site.quartier && `, ${site.quartier}`}</p>
          )}
        </div>

        {site.client_nom && (
          <div className="site-client">
            <strong>🏢 Client :</strong>
            <span>{site.client_nom}</span>
          </div>
        )}

        <div className="site-stats">
          <div className="stat-item">
            <span className="stat-label">📱 Appareils :</span>
            <span className="stat-value">{site.nb_appareils || 0}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">📅 Créé :</span>
            <span className="stat-value">{formatDate(site.date_creation)}</span>
          </div>
        </div>

        {site.description && (
          <div className="site-description">
            <strong>📝 Description :</strong>
            <p>{site.description}</p>
          </div>
        )}

        {/* Actions rapides */}
        <div className="site-quick-actions">
          {hasCoordinates && site.map_link && (
            <Button
              variant="outline"
              size="small"
              onClick={() => window.open(site.map_link, '_blank')}
              className="map-link-btn"
            >
              🗺️ Voir sur la carte
            </Button>
          )}
          
          <Button
            variant="primary"
            size="small"
            onClick={() => onDetails(site)}
            className="details-btn"
          >
            📊 Voir détails
          </Button>
        </div>
      </div>

      {/* Actions admin (pied de carte) */}
      {isSuperadmin && (
        <div className="site-card-footer">
          <div className="admin-actions">
            <Button
              variant="outline"
              size="small"
              onClick={() => onEdit(site)}
            >
              ✏️ Modifier
            </Button>
            
            {!hasCoordinates && (
              <Button
                variant="secondary"
                size="small"
                onClick={() => onGeocode(site)}
                title="Géocoder l'adresse"
              >
                🌍 Géocoder
              </Button>
            )}
            
            <Button
              variant="danger"
              size="small"
              onClick={() => onDelete(site)}
              title="Supprimer le site"
            >
              🗑️ Supprimer
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default SiteCard
