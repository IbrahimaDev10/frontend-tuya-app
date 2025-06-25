import React, { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'


import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import './SiteMap.css'

// Fix pour les icônes Leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

// Icônes personnalisées pour différents états
const createCustomIcon = (color, isActive) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div class="marker-pin ${isActive ? 'active' : 'inactive'}" style="background-color: ${color}">
        <div class="marker-icon">${isActive ? '✅' : '❌'}</div>
      </div>
    `,
    iconSize: [30, 42],
    iconAnchor: [15, 42],
    popupAnchor: [0, -42]
  })
}

const SiteMap = ({ sites, onSiteClick, selectedSite }) => {
  const [mapCenter, setMapCenter] = useState([14.6928, -17.4467]) // Dakar par défaut
  const [mapZoom, setMapZoom] = useState(6)
  const mapRef = useRef()

  useEffect(() => {
    if (sites && sites.length > 0) {
      // Calculer le centre et le zoom optimal pour afficher tous les sites
      const sitesWithCoords = sites.filter(site => site.latitude && site.longitude)
      
      if (sitesWithCoords.length > 0) {
        const bounds = L.latLngBounds(
          sitesWithCoords.map(site => [site.latitude, site.longitude])
        )
        
        const center = bounds.getCenter()
        setMapCenter([center.lat, center.lng])
        
        // Ajuster le zoom selon la dispersion des points
        if (sitesWithCoords.length === 1) {
          setMapZoom(13)
        } else {
          // Le zoom sera ajusté automatiquement par fitBounds
          setMapZoom(6)
        }
      }
    }
  }, [sites])

  useEffect(() => {
    // Centrer sur le site sélectionné
    if (selectedSite && selectedSite.latitude && selectedSite.longitude && mapRef.current) {
      const map = mapRef.current
      map.setView([selectedSite.latitude, selectedSite.longitude], 15)
    }
  }, [selectedSite])

  const handleMarkerClick = (site) => {
    if (onSiteClick) {
      onSiteClick(site)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString('fr-FR')
  }

  const sitesWithCoords = sites.filter(site => site.latitude && site.longitude)
  const sitesWithoutCoords = sites.filter(site => !site.latitude || !site.longitude)

  return (
    <div className="site-map-wrapper">
      {/* Informations sur la carte */}
      <div className="map-info-panel">
        <div className="map-stats">
          <div className="stat-item">
            <span className="stat-label">Total sites :</span>
            <span className="stat-value">{sites.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Géocodés :</span>
            <span className="stat-value">{sitesWithCoords.length}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Non géocodés :</span>
            <span className="stat-value">{sitesWithoutCoords.length}</span>
          </div>
        </div>
        
        {sitesWithoutCoords.length > 0 && (
          <div className="ungeocode-warning">
            <span className="warning-icon">⚠️</span>
            <span>{sitesWithoutCoords.length} site(s) sans coordonnées</span>
          </div>
        )}
      </div>

      {/* Carte principale */}
      <div className="map-container">
        <MapContainer center={mapCenter} zoom={mapZoom} style={{ height: '100%', width: '100%' }}>
  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
  
  {sitesWithCoords.map(site => (
    <Marker
      key={site.id}
      position={[site.latitude, site.longitude]}
      icon={createCustomIcon(site.actif ? '#10b981' : '#ef4444', site.actif)}
      eventHandlers={{ click: () => handleMarkerClick(site) }}
    >
                <Popup className="site-popup">
                  <div className="popup-content">
                    <div className="popup-header">
                      <h3 className="site-name">{site.nom_site}</h3>
                      <div className="site-badges">
                        <span className={`status-badge ${site.actif ? 'active' : 'inactive'}`}>
                          {site.actif ? '✅ Actif' : '❌ Inactif'}
                        </span>
                      </div>
                    </div>
                    
                    <div className="popup-body">
                      <div className="info-row">
                        <strong>📍 Adresse :</strong>
                        <span>{site.adresse}</span>
                      </div>
                      
                      {site.ville && (
                        <div className="info-row">
                          <strong>🏙️ Ville :</strong>
                          <span>{site.ville}{site.quartier && `, ${site.quartier}`}</span>
                        </div>
                      )}
                      
                      {site.client_nom && (
                        <div className="info-row">
                          <strong>🏢 Client :</strong>
                          <span>{site.client_nom}</span>
                        </div>
                      )}
                      
                      <div className="info-row">
                        <strong>📱 Appareils :</strong>
                        <span>{site.nb_appareils || 0}</span>
                      </div>
                      
                      <div className="info-row">
                        <strong>📅 Créé :</strong>
                        <span>{formatDate(site.date_creation)}</span>
                      </div>
                      
                      {site.description && (
                        <div className="info-row">
                          <strong>📝 Description :</strong>
                          <span>{site.description}</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="popup-footer">
                      <button 
                        className="popup-btn primary"
                        onClick={() => handleMarkerClick(site)}
                      >
                        📊 Voir détails
                      </button>
                      
                      {site.map_link && (
                        <button 
                          className="popup-btn secondary"
                          onClick={() => window.open(site.map_link, '_blank')}
                        >
                          🗺️ Carte externe
                        </button>
                      )}
                    </div>
                  </div>
                </Popup>
              </Marker>
            ))}
          
        </MapContainer>
      </div>

      {/* Liste des sites non géocodés */}
      {sitesWithoutCoords.length > 0 && (
        <div className="ungeocode-sites">
          <h3>Sites sans coordonnées</h3>
          <div className="ungeocode-list">
            {sitesWithoutCoords.map(site => (
              <div key={site.id} className="ungeocode-item">
                <div className="site-info">
                  <span className="site-name">{site.nom_site}</span>
                  <span className="site-address">{site.adresse}</span>
                </div>
                <button 
                  className="details-btn"
                  onClick={() => handleMarkerClick(site)}
                >
                  📊 Détails
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SiteMap