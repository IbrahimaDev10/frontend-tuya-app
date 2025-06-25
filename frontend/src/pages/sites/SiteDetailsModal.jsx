import React, { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import SiteService from '../../services/siteService'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import 'leaflet/dist/leaflet.css'
import './SiteModal.css'

const SiteDetailsModal = ({ site, onClose, onEdit }) => {
  const [siteDetails, setSiteDetails] = useState(null)
  const [siteDevices, setSiteDevices] = useState([])
  const [nearbySites, setNearbySites] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  const [loadingNearby, setLoadingNearby] = useState(false)

  useEffect(() => {
    if (site) {
      loadSiteDetails()
      loadSiteDevices()
    }
  }, [site])

  const loadSiteDetails = async () => {
    try {
      const response = await SiteService.obtenirSite(site.id)
      if (response.data.success) {
        setSiteDetails(response.data.data)
      }
    } catch (error) {
      console.error('Erreur chargement détails:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSiteDevices = async () => {
    try {
      const response = await DeviceService.listerAppareils(site.id)
      if (response.data.success) {
        setSiteDevices(response.data.data || [])
      }
    } catch (error) {
      console.error('Erreur chargement appareils:', error)
    }
  }

  const loadNearbySites = async (radius = 10) => {
    if (!site.latitude || !site.longitude) return
    
    setLoadingNearby(true)
    try {
      const response = await SiteService.sitesProches(site.id, radius)
      if (response.data.success) {
        setNearbySites(response.data.sites_proches || [])
      }
    } catch (error) {
      console.error('Erreur chargement sites proches:', error)
    } finally {
      setLoadingNearby(false)
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('fr-FR')
  }

  const hasCoordinates = site?.latitude && site?.longitude

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content extra-large" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Détails du site</h3>
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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content extra-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{site?.nom_site}</h3>
          <div className="header-actions">
            <Button
              variant="primary"
              size="small"
              onClick={onEdit}
            >
              ✏️ Modifier
            </Button>
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
            className={`modal-tab ${activeTab === 'devices' ? 'active' : ''}`}
            onClick={() => setActiveTab('devices')}
          >
            📱 Appareils ({siteDevices.length})
          </button>
          <button
            className={`modal-tab ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => setActiveTab('map')}
          >
            🗺️ Carte & Proximité
          </button>
          <button
            className={`modal-tab ${activeTab === 'contact' ? 'active' : ''}`}
            onClick={() => setActiveTab('contact')}
          >
            👤 Contact & Accès
          </button>
        </div>

        <div className="modal-body">
          {/* Vue d'ensemble */}
          {activeTab === 'overview' && (
            <div className="overview-content">
              {/* Statut et badges */}
              <div className="status-cards">
                <div className="status-card">
                  <h4>Statut</h4>
                  <div className={`status-indicator ${site.actif ? 'active' : 'inactive'}`}>
                    {site.actif ? '✅ Actif' : '❌ Inactif'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Géolocalisation</h4>
                  <div className={`status-indicator ${hasCoordinates ? 'geocoded' : 'not-geocoded'}`}>
                    {hasCoordinates ? '📍 Géocodé' : '❓ Non géocodé'}
                  </div>
                </div>
                <div className="status-card">
                  <h4>Appareils</h4>
                  <div className="status-indicator">
                    📱 {siteDevices.length} appareil{siteDevices.length !== 1 ? 's' : ''}
                  </div>
                </div>
              </div>

              {/* Informations principales */}
              <div className="info-section">
                <h4>Informations générales</h4>
                <div className="info-grid">
                  <div className="info-item">
                    <label>Nom du site:</label>
                    <span>{site.nom_site}</span>
                  </div>
                  <div className="info-item">
                    <label>Client:</label>
                    <span>{site.client_nom || 'N/A'}</span>
                  </div>
                  <div className="info-item">
                    <label>Créé le:</label>
                    <span>{formatDate(site.date_creation)}</span>
                  </div>
                  <div className="info-item">
                    <label>Dernière modif:</label>
                    <span>{formatDate(site.date_modification)}</span>
                  </div>
                </div>
              </div>

              {/* Adresse */}
              <div className="info-section">
                <h4>Adresse</h4>
                <div className="address-display">
                  <div className="address-main">{site.adresse}</div>
                  {site.ville && (
                    <div className="address-secondary">
                      {site.ville}{site.quartier && `, ${site.quartier}`}
                      {site.code_postal && ` - ${site.code_postal}`}
                    </div>
                  )}
                  {hasCoordinates && (
                    <div className="coordinates">
                      📍 {site.latitude.toFixed(6)}, {site.longitude.toFixed(6)}
                    </div>
                  )}
                  {site.map_link && (
                    <Button
                      variant="outline"
                      size="small"
                      onClick={() => window.open(site.map_link, '_blank')}
                      className="map-link-btn"
                    >
                      🗺️ Voir sur la carte
                    </Button>
                  )}
                </div>
              </div>



              {/* Statistiques rapides des appareils */}
              {siteDevices.length > 0 && (
                <div className="devices-summary">
                  <h4>Résumé des appareils</h4>
                  <div className="devices-stats">
                    <div className="device-stat">
                      <span className="stat-label">En ligne:</span>
                      <span className="stat-value">
                        {siteDevices.filter(d => d.en_ligne).length}
                      </span>
                    </div>
                    <div className="device-stat">
                      <span className="stat-label">Actifs:</span>
                      <span className="stat-value">
                        {siteDevices.filter(d => d.etat_switch).length}
                      </span>
                    </div>
                    <div className="device-stat">
                      <span className="stat-label">Types:</span>
                      <span className="stat-value">
                        {new Set(siteDevices.map(d => d.type_appareil)).size}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Appareils */}
          {activeTab === 'devices' && (
            <div className="devices-content">
              <div className="devices-header">
                <h4>Appareils du site ({siteDevices.length})</h4>
                <Button
                  variant="outline"
                  size="small"
                  onClick={loadSiteDevices}
                >
                  🔄 Actualiser
                </Button>
              </div>
              
              {siteDevices.length > 0 ? (
                <div className="devices-grid">
                  {siteDevices.map(device => (
                    <div key={device.id} className="device-card-mini">
                      <div className="device-header">
                        <h5>{device.nom_appareil}</h5>
                        <div className="device-badges">
                          <span className={`status-badge ${device.en_ligne ? 'online' : 'offline'}`}>
                            {device.en_ligne ? '🟢' : '🔴'}
                          </span>
                          <span className={`state-badge ${device.etat_switch ? 'on' : 'off'}`}>
                            {device.etat_switch ? 'ON' : 'OFF'}
                          </span>
                        </div>
                      </div>
                      <div className="device-info">
                        <p><strong>Type:</strong> {device.type_appareil}</p>
                        <p><strong>ID:</strong> <code>{device.tuya_device_id}</code></p>
                        {device.emplacement && (
                          <p><strong>Emplacement:</strong> {device.emplacement}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-icon">📱</div>
                  <h4>Aucun appareil</h4>
                  <p>Ce site n'a pas encore d'appareils assignés.</p>
                </div>
              )}
            </div>
          )}

          {/* Carte et proximité */}
          {activeTab === 'map' && (
            <div className="map-content">
              {hasCoordinates ? (
                <>
                  <div className="map-section">
                    <h4>Localisation</h4>
                    <MapContainer
                      center={[site.latitude, site.longitude]}
                      zoom={15}
                      style={{ height: '400px', width: '100%' }}
                      className="site-detail-map"
                    >
                      <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      />
                      <Marker position={[site.latitude, site.longitude]}>
                        <Popup>
                          <div className="popup-content">
                            <strong>{site.nom_site}</strong><br />
                            {site.adresse}<br />
                            📱 {siteDevices.length} appareil{siteDevices.length !== 1 ? 's' : ''}
                          </div>
                        </Popup>
                      </Marker>
                    </MapContainer>
                  </div>

                  <div className="nearby-section">
                    <div className="nearby-header">
                      <h4>Sites à proximité</h4>
                      <div className="proximity-controls">
                        <select 
                          onChange={(e) => loadNearbySites(parseInt(e.target.value))}
                          defaultValue="10"
                        >
                          <option value="5">5 km</option>
                          <option value="10">10 km</option>
                          <option value="25">25 km</option>
                          <option value="50">50 km</option>
                        </select>
                        <Button
                          variant="outline"
                          size="small"
                          onClick={() => loadNearbySites(10)}
                          loading={loadingNearby}
                        >
                          🔍 Rechercher
                        </Button>
                      </div>
                    </div>

                    {nearbySites.length > 0 ? (
                      <div className="nearby-sites">
                        {nearbySites.map(nearbySite => (
                          <div key={nearbySite.id} className="nearby-site-item">
                            <div className="nearby-site-info">
                              <h5>{nearbySite.nom_site}</h5>
                              <p>{nearbySite.adresse}</p>
                              <small>📍 {nearbySite.distance_km.toFixed(2)} km</small>
                            </div>
                            <div className="nearby-site-stats">
                              <span>📱 {nearbySite.nb_appareils || 0}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-state">
                        <p>Aucun site trouvé à proximité</p>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="no-coordinates">
                  <div className="empty-icon">📍</div>
                  <h4>Pas de coordonnées</h4>
                  <p>Ce site n'a pas encore été géocodé.</p>
                  <Button
                    variant="primary"
                    onClick={() => {
                      // Lancer le géocodage
                      SiteService.geocoderSite(site.id).then(() => {
                        loadSiteDetails()
                      })
                    }}
                  >
                    🌍 Géocoder maintenant
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Contact et accès */}
          {activeTab === 'contact' && (
            <div className="contact-content">
              {/* Contact */}
              {(site.contact_site || site.telephone_site) && (
                <div className="info-section">
                  <h4>Contact sur site</h4>
                  <div className="contact-info">
                    {site.contact_site && (
                      <div className="contact-item">
                        <span className="contact-icon">👤</span>
                        <span>{site.contact_site}</span>
                      </div>
                    )}
                    {site.telephone_site && (
                      <div className="contact-item">
                        <span className="contact-icon">📞</span>
                        <a href={`tel:${site.telephone_site}`}>{site.telephone_site}</a>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Liens utiles */}
              <div className="info-section">
                <h4>Liens utiles</h4>
                <div className="useful-links">
                  {hasCoordinates && site.map_link && (
                    <Button
                      variant="outline"
                      onClick={() => window.open(site.map_link, '_blank')}
                    >
                      🗺️ Voir sur Google Maps
                    </Button>
                  )}
                  {hasCoordinates && (
                    <Button
                      variant="outline"
                      onClick={() => window.open(
                        `https://www.google.com/maps/dir/?api=1&destination=${site.latitude},${site.longitude}`,
                        '_blank'
                      )}
                    >
                      🧭 Itinéraire Google Maps
                    </Button>
                  )}
                </div>
              </div>

              {/* Message si aucune info */}
              {!site.contact_site && !site.telephone_site  && (
                <div className="empty-state">
                  <div className="empty-icon">👤</div>
                  <h4>Aucune information de contact</h4>
                  <p>Les informations de contact et d'accès n'ont pas encore été renseignées.</p>
                  <Button variant="primary" onClick={onEdit}>
                    ✏️ Ajouter des informations
                  </Button>
                </div>
              )}
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
          <Button
            type="button"
            variant="primary"
            onClick={onEdit}
          >
            ✏️ Modifier le site
          </Button>
        </div>
      </div>
    </div>
  )
}

export default SiteDetailsModal