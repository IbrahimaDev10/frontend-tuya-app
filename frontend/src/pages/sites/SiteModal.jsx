import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import siteService from '../../services/siteService'
import clientService from '../../services/clientService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import Swal from 'sweetalert2'
import './SiteModal.css'

const SiteModal = ({ site, onClose, onSave }) => {
  const { isSuperadmin } = useAuth()
  const [clients, setClients] = useState([])
  const [formData, setFormData] = useState({
    nom_site: '',
    adresse: '',
    ville: '',
    quartier: '',
    code_postal: '',
    pays: 'Sénégal',
    contact_site: '',
    telephone_site: '',
    client_id: '',
    latitude: '',
    longitude: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (site) {
      setFormData({
        nom_site: site.nom_site || '',
        adresse: site.adresse || '',
        ville: site.ville || '',
        quartier: site.quartier || '',
        code_postal: site.code_postal || '',
        pays: site.pays || 'Sénégal',
        contact_site: site.contact_site || '',
        telephone_site: site.telephone_site || '',
        client_id: site.client_id || '',
        latitude: site.latitude || '',
        longitude: site.longitude || ''
      })
    }

    if (isSuperadmin()) {
      loadClients()
    }
  }, [site])

  const loadClients = async () => {
    try {
      const response = await clientService.listerClients()
      setClients(response.data.clients)
    } catch (error) {
      console.error('Erreur lors du chargement des clients:', error)
      Swal.fire({
        icon: 'error',
        title: 'Erreur',
        text: 'Impossible de charger la liste des clients'
      })
    }
  }

  const validateForm = () => {
    const newErrors = {}
    if (!formData.nom_site) newErrors.nom_site = 'Le nom du site est requis'
    if (!formData.adresse) newErrors.adresse = 'L\'adresse est requise'
    if (isSuperadmin() && !formData.client_id) newErrors.client_id = 'Le client est requis'
    
    // Validation des coordonnées GPS si fournies
    if (formData.latitude && !isValidLatitude(formData.latitude)) {
      newErrors.latitude = 'Latitude invalide (-90 à 90)'
    }
    if (formData.longitude && !isValidLongitude(formData.longitude)) {
      newErrors.longitude = 'Longitude invalide (-180 à 180)'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const isValidLatitude = (lat) => {
    const num = parseFloat(lat)
    return !isNaN(num) && num >= -90 && num <= 90
  }

  const isValidLongitude = (lon) => {
    const num = parseFloat(lon)
    return !isNaN(num) && num >= -180 && num <= 180
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    // Effacer l'erreur quand l'utilisateur commence à taper
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return

    setLoading(true)
    try {
      let response
      if (site) {
        response = await siteService.modifierSite(site.id, formData)
      } else {
        response = await siteService.creerSite(formData)
      }

      Swal.fire({
        icon: 'success',
        title: 'Succès',
        text: site
          ? 'Site modifié avec succès'
          : 'Site créé avec succès'
      })

      if (onSave) onSave(response.data.site)
      onClose()
    } catch (error) {
      console.error('Erreur lors de la sauvegarde:', error)
      Swal.fire({
        icon: 'error',
        title: 'Erreur',
        text: error.response?.data?.error || 'Une erreur est survenue'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{site ? 'Modifier le site' : 'Créer un nouveau site'}</h2>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          <div className="form-grid">
            {/* Informations de base */}
            <div className="form-section full-width">
              <h3>Informations de base</h3>
              {isSuperadmin() && (
                <div className="form-group">
                  <label>Client*</label>
                  <select
                    name="client_id"
                    value={formData.client_id}
                    onChange={handleChange}
                    className={errors.client_id ? 'error' : ''}
                  >
                      <option value="">Sélectionner un client</option>
                      {Array.isArray(clients) && clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.nom_entreprise}
                      </option>
                    ))}

                  </select>
                  {errors.client_id && <span className="error-message">{errors.client_id}</span>}
                </div>
              )}
              <Input
                label="Nom du site*"
                name="nom_site"
                value={formData.nom_site}
                onChange={handleChange}
                error={errors.nom_site}
              />
            </div>

            {/* Adresse */}
            <div className="form-section full-width">
              <h3>Adresse</h3>
              <Input
                label="Adresse*"
                name="adresse"
                value={formData.adresse}
                onChange={handleChange}
                error={errors.adresse}
              />
              <div className="form-row">
                <Input
                  label="Ville"
                  name="ville"
                  value={formData.ville}
                  onChange={handleChange}
                />
                <Input
                  label="Quartier"
                  name="quartier"
                  value={formData.quartier}
                  onChange={handleChange}
                />
              </div>
              <div className="form-row">
                <Input
                  label="Code postal"
                  name="code_postal"
                  value={formData.code_postal}
                  onChange={handleChange}
                />
                <Input
                  label="Pays"
                  name="pays"
                  value={formData.pays}
                  onChange={handleChange}
                />
              </div>
            </div>

            {/* Contact */}
            <div className="form-section full-width">
              <h3>Contact</h3>
              <div className="form-row">
                <Input
                  label="Contact sur site"
                  name="contact_site"
                  value={formData.contact_site}
                  onChange={handleChange}
                />
                <Input
                  label="Téléphone du site"
                  name="telephone_site"
                  value={formData.telephone_site}
                  onChange={handleChange}
                />
              </div>
            </div>

            {/* Coordonnées GPS */}
            <div className="form-section full-width">
              <h3>Coordonnées GPS (optionnel)</h3>
              <div className="form-row">
                <Input
                  label="Latitude"
                  name="latitude"
                  value={formData.latitude}
                  onChange={handleChange}
                  error={errors.latitude}
                  placeholder="Ex: 14.7167"
                />
                <Input
                  label="Longitude"
                  name="longitude"
                  value={formData.longitude}
                  onChange={handleChange}
                  error={errors.longitude}
                  placeholder="Ex: -17.4677"
                />
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <Button
              type="button"
              variant="secondary"
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
              {site ? 'Modifier' : 'Créer'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SiteModal