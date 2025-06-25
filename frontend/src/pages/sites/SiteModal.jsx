import React, { useState, useEffect } from 'react'
import SiteService from '../../services/siteService'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import './SiteModal.css'

const SiteModal = ({ site, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    nom_site: '',
    adresse: '',
    ville: '',
    quartier: '',
    client_id: '', 
    contact_site: '',
    telephone_site: '',
    

  })
  const [clients, setClients] = useState([])
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [testingGeocode, setTestingGeocode] = useState(false)
  const [geocodeResults, setGeocodeResults] = useState(null)

  const isEdit = !!site

  useEffect(() => {
    if (isEdit) {
      setFormData({
        nom_site: site.nom_site || '',
        adresse: site.adresse || '',
        ville: site.ville || '',
        quartier: site.quartier || '',
        client_id: site.client_id || '',    
        contact_site: site.contact_site || '',
        telephone_site: site.telephone_site || '',
        
      })
    }
    loadClients()
  }, [site])

  const loadClients = async () => {
    try {
      const response = await UserService.listerClients()
      setClients(response.data.data || [])
    } catch (error) {
      console.error('Erreur chargement clients:', error)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))

    // Effacer l'erreur du champ modifié
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.nom_site.trim()) {
      newErrors.nom_site = 'Nom du site requis'
    }

    if (!formData.adresse.trim()) {
      newErrors.adresse = 'Adresse requise'
    }

    if (!formData.client_id) {
      newErrors.client_id = 'Client requis'
    }



    return newErrors
  }

  const handleTestGeocode = async () => {
    if (!formData.adresse.trim()) {
      setErrors({ adresse: 'Veuillez saisir une adresse pour tester le géocodage' })
      return
    }

    setTestingGeocode(true)
    try {
      const adresseComplete = `${formData.adresse}, ${formData.ville}, ${formData.quartier}`.replace(/,\s*,/g, ',').replace(/^,|,$/g, '')
      const response = await SiteService.testerGeocodage(adresseComplete)
      
      if (response.data.success) {
        setGeocodeResults(response.data.resultats_geocodage)
      } else {
        setErrors({ adresse: 'Impossible de géocoder cette adresse' })
      }
    } catch (error) {
      setErrors({ adresse: 'Erreur lors du test de géocodage' })
    } finally {
      setTestingGeocode(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const newErrors = validateForm()
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setLoading(true)
    setErrors({})

    try {
      if (isEdit) {
        await SiteService.modifierSite(site.id, formData)
      } else {
        await SiteService.creerSite(formData)
      }

      onSave()
    } catch (error) {
      setErrors({
        general: error.response?.data?.error || 'Erreur lors de la sauvegarde'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content extra-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? 'Modifier le site' : 'Nouveau site'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            {/* Informations générales */}
            <div className="form-section">
              <h4>🏢 Informations générales</h4>
              
              <div className="form-grid">
                <Input
                  type="text"
                  name="nom_site"
                  label="Nom du site"
                  value={formData.nom_site}
                  onChange={handleChange}
                  error={errors.nom_site}
                  required
                />

                <div className="form-group">
                  <label className="input-label">Client *</label>
                  <select
                    name="client_id"
                    value={formData.client_id}
                    onChange={handleChange}
                    className={`input ${errors.client_id ? 'input-error' : ''}`}
                    required
                  >
                    <option value="">Sélectionner un client</option>
                    {clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.nom_entreprise}
                      </option>
                    ))}
                  </select>
                  {errors.client_id && (
                    <span className="input-error-message">{errors.client_id}</span>
                  )}
                </div>
              </div>
            </div>

            {/* Adresse */}
            <div className="form-section">
              <h4>📍 Adresse</h4>
              
              <div className="address-input-group">
                <Input
                  type="text"
                  name="adresse"
                  label="Adresse complète"
                  value={formData.adresse}
                  onChange={handleChange}
                  error={errors.adresse}
                  placeholder="Ex: 15 Avenue Pasteur"
                  required
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleTestGeocode}
                  loading={testingGeocode}
                  className="geocode-test-btn"
                >
                  🌍 Tester géocodage
                </Button>
              </div>

              <div className="form-grid">
                <Input
                  type="text"
                  name="ville"
                  label="Ville"
                  value={formData.ville}
                  onChange={handleChange}
                  error={errors.ville}
                  placeholder="Ex: Toulouse"
                  required
                />
                <Input
                  type="text"
                  name="quartier"
                  label="Quartier"
                  value={formData.quartier}
                  onChange={handleChange}
                  error={errors.quartier}
                  placeholder="Ex: Quartier du soleil"
                />
              </div>

              {/* Résultats du géocodage */}
              {geocodeResults && (
                <div className="geocode-results">
                  <h5>🌍 Résultats du géocodage :</h5>
                  <div className="geocode-info">
                    <p><strong>Adresse trouvée :</strong> {geocodeResults.adresse_formatee}</p>
                    <p><strong>Coordonnées :</strong> {geocodeResults.latitude}, {geocodeResults.longitude}</p>
                    <p><strong>Précision :</strong> {geocodeResults.precision}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Informations de contact */}
            <div className="form-section">
              <h4>📞 Contact</h4>
              
              <div className="form-grid">
                <Input
                  type="text"
                  name="contact_site"
                  label="Nom du contact"
                  value={formData.contact_site}
                  onChange={handleChange}
                  error={errors.contact_site}
                  placeholder="Ex: Jean Dupont"
                />
                <Input
                  type="tel"
                  name="telephone_site"
                  label="Téléphone"
                  value={formData.telephone_site}
                  onChange={handleChange}
                  error={errors.telephone_site}
                  placeholder="Ex: 05 61 00 00 00"
                />
              </div>
            </div>


          </div>

          <div className="modal-footer">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={loading}
            >
              {isEdit ? 'Modifier' : 'Créer'} le site
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SiteModal
