import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import UserService from '../../services/userService'
import SiteService from '../../services/siteService'
import Button from '../../components/Button'
import './AssignModal.css'

const AssignModal = ({ device, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    client_id: '',
    site_id: ''
  })
  const [clients, setClients] = useState([])
  const [sites, setSites] = useState([])
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [loadingSites, setLoadingSites] = useState(false)

  useEffect(() => {
    loadClients()
  }, [])

  useEffect(() => {
    if (formData.client_id) {
      loadSites(formData.client_id)
    } else {
      setSites([])
    }
  }, [formData.client_id])

  const loadClients = async () => {
    try {
      const response = await UserService.listerClients()
      setClients(response.data.data || [])
    } catch (error) {
      console.error('Erreur lors du chargement des clients:', error)
    }
  }

  const loadSites = async (clientId) => {
    try {
      setLoadingSites(true)
      const response = await SiteService.listerSites(clientId)
      setSites(response.data.data || [])
    } catch (error) {
      console.error('Erreur lors du chargement des sites:', error)
      setSites([])
    } finally {
      setLoadingSites(false)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))

    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }

    if (name === 'client_id') {
      setFormData(prev => ({
        ...prev,
        site_id: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.client_id) {
      newErrors.client_id = 'Client requis'
    }

    if (!formData.site_id) {
      newErrors.site_id = 'Site requis'
    }

    return newErrors
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
      const response = await DeviceService.assignerAppareil(
        device.tuya_device_id,
        formData.client_id,
        formData.site_id
      )

      if (response.data.success) {
        onSuccess()
      } else {
        setErrors({
          general: response.data.message || 'Erreur lors de l\'assignation'
        })
      }
    } catch (error) {
      setErrors({
        general: error.response?.data?.error || 'Erreur lors de l\'assignation'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Assigner l'appareil</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            {/* Informations de l'appareil */}
            <div className="device-info-card">
              <h4>📱 Appareil à assigner</h4>
              <div className="device-details">
                <p><strong>ID Tuya:</strong> {device?.tuya_device_id}</p>
                <p><strong>Nom original:</strong> {device?.tuya_nom_original}</p>
                <p><strong>Type:</strong> {device?.type_appareil}</p>
                <p><strong>Modèle:</strong> {device?.tuya_modele}</p>
                <p><strong>En ligne:</strong> 
                  <span className={`online-badge ${device?.en_ligne ? 'online' : 'offline'}`}>
                    {device?.en_ligne ? '🟢 Oui' : '🔴 Non'}
                  </span>
                </p>
              </div>
            </div>

            {/* Formulaire d'assignation */}
            <div className="form-section">
              <h4>🏢 Assignation</h4>

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

              <div className="form-group">
                <label className="input-label">Site *</label>
                <select
                  name="site_id"
                  value={formData.site_id}
                  onChange={handleChange}
                  className={`input ${errors.site_id ? 'input-error' : ''}`}
                  disabled={!formData.client_id || loadingSites}
                  required
                >
                  <option value="">
                    {loadingSites ? 'Chargement...' : 'Sélectionner un site'}
                  </option>
                  {sites.map(site => (
                    <option key={site.id} value={site.id}>
                      {site.nom_site} - {site.adresse}
                    </option>
                  ))}
                </select>
                {errors.site_id && (
                  <span className="input-error-message">{errors.site_id}</span>
                )}
              </div>
            </div>

            <div className="info-box">
              <strong>Note:</strong> Une fois assigné, cet appareil sera visible par le client 
              sélectionné et commencera à collecter des données.
            </div>
          </div>

          <div className="modal-footer">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={loading}
            >
              Assigner l'appareil
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default AssignModal
