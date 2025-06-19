import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import './DeviceModal.css'

const DeviceModal = ({ device, onClose, onSuccess, mode = 'edit' }) => {
  const [formData, setFormData] = useState({
    nom_appareil: '',
    emplacement: '',
    description: '',
    seuil_tension_min: '',
    seuil_tension_max: '',
    seuil_courant_max: '',
    seuil_puissance_max: '',
    actif: true
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [deviceStatus, setDeviceStatus] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    if (device && mode === 'edit') {
      setFormData({
        nom_appareil: device.nom_appareil || '',
        emplacement: device.emplacement || '',
        description: device.description || '',
        seuil_tension_min: device.seuil_tension_min || '',
        seuil_tension_max: device.seuil_tension_max || '',
        seuil_courant_max: device.seuil_courant_max || '',
        seuil_puissance_max: device.seuil_puissance_max || '',
        actif: device.actif !== false
      })
      loadDeviceStatus()
    }
  }, [device, mode])

  const loadDeviceStatus = async () => {
    if (!device) return
    
    try {
      setRefreshing(true)
      const response = await DeviceService.obtenirAppareil(device.id || device.tuya_device_id)
      if (response.data.success) {
        setDeviceStatus(response.data.data)
      }
    } catch (error) {
      console.error('Erreur chargement statut:', error)
    } finally {
      setRefreshing(false)
    }
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
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

    if (!formData.nom_appareil.trim()) {
      newErrors.nom_appareil = 'Nom de l\'appareil requis'
    }

    // Validation des seuils numériques
    const numericFields = ['seuil_tension_min', 'seuil_tension_max', 'seuil_courant_max', 'seuil_puissance_max']
    numericFields.forEach(field => {
      if (formData[field] && isNaN(parseFloat(formData[field]))) {
        newErrors[field] = 'Valeur numérique requise'
      }
    })

    // Validation logique des seuils
    if (formData.seuil_tension_min && formData.seuil_tension_max) {
      const min = parseFloat(formData.seuil_tension_min)
      const max = parseFloat(formData.seuil_tension_max)
      if (min >= max) {
        newErrors.seuil_tension_max = 'Le seuil max doit être supérieur au seuil min'
      }
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
      // Préparer les données pour l'API
      const updateData = {
        ...formData,
        seuil_tension_min: formData.seuil_tension_min ? parseFloat(formData.seuil_tension_min) : null,
        seuil_tension_max: formData.seuil_tension_max ? parseFloat(formData.seuil_tension_max) : null,
        seuil_courant_max: formData.seuil_courant_max ? parseFloat(formData.seuil_courant_max) : null,
        seuil_puissance_max: formData.seuil_puissance_max ? parseFloat(formData.seuil_puissance_max) : null
      }

      const response = await DeviceService.modifierAppareil(
        device.id || device.tuya_device_id,
        updateData
      )

      if (response.data.success) {
        onSuccess()
      } else {
        setErrors({
          general: response.data.message || 'Erreur lors de la modification'
        })
      }
    } catch (error) {
      setErrors({
        general: error.response?.data?.error || 'Erreur lors de la modification'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleToggleDevice = async () => {
    try {
      const response = await DeviceService.toggleAppareil(device.id || device.tuya_device_id)
      if (response.data.success) {
        await loadDeviceStatus()
      }
    } catch (error) {
      console.error('Erreur toggle:', error)
    }
  }

  const handleCollectData = async () => {
    try {
      await DeviceService.collecterDonnees(device.id || device.tuya_device_id)
      await loadDeviceStatus()
    } catch (error) {
      console.error('Erreur collecte:', error)
    }
  }

  const formatValue = (value, unit = '') => {
    if (value === null || value === undefined) return 'N/A'
    if (typeof value === 'number') {
      return `${value.toFixed(2)} ${unit}`.trim()
    }
    return value
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            {mode === 'edit' ? 'Modifier l\'appareil' : 'Nouvel appareil'}
          </h3>
          <div className="header-actions">
            {device && (
              <>
                <Button
                  variant="outline"
                  size="small"
                  onClick={loadDeviceStatus}
                  loading={refreshing}
                >
                  🔄 Actualiser
                </Button>
                {device.statut_assignation === 'assigne' && (
                  <>
                    <Button
                      variant="outline"
                      size="small"
                      onClick={handleToggleDevice}
                    >
                      {deviceStatus?.etat_switch ? '⏸️ OFF' : '▶️ ON'}
                    </Button>
                    <Button
                      variant="outline"
                      size="small"
                      onClick={handleCollectData}
                    >
                      📊 Collecter
                    </Button>
                  </>
                )}
              </>
            )}
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            {/* Informations de l'appareil */}
            {device && (
              <div className="device-info-card">
                <h4>📱 Informations de l'appareil</h4>
                <div className="device-details">
                  <div className="info-grid">
                    <div className="info-item">
                      <label>ID Tuya:</label>
                      <span className="code">{device.tuya_device_id}</span>
                    </div>
                    <div className="info-item">
                      <label>Type:</label>
                      <span>{device.type_appareil}</span>
                    </div>
                    <div className="info-item">
                      <label>Modèle:</label>
                      <span>{device.tuya_modele}</span>
                    </div>
                    <div className="info-item">
                      <label>État:</label>
                      <span className={`state-badge ${deviceStatus?.etat_switch ? 'on' : 'off'}`}>
                        {deviceStatus?.etat_switch ? 'ON' : 'OFF'}
                      </span>
                    </div>
                    <div className="info-item">
                      <label>En ligne:</label>
                      <span className={`online-badge ${deviceStatus?.en_ligne ? 'online' : 'offline'}`}>
                        {deviceStatus?.en_ligne ? '🟢 Oui' : '🔴 Non'}
                      </span>
                    </div>
                    <div className="info-item">
                      <label>Client:</label>
                      <span>{device.client?.nom_entreprise || 'Non assigné'}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Configuration générale */}
            <div className="form-section">
              <h4>⚙️ Configuration générale</h4>
              
              <Input
                type="text"
                name="nom_appareil"
                label="Nom de l'appareil *"
                value={formData.nom_appareil}
                onChange={handleChange}
                error={errors.nom_appareil}
                placeholder="Ex: Prise Bureau 1"
                required
              />

              <Input
                type="text"
                name="emplacement"
                label="Emplacement"
                value={formData.emplacement}
                onChange={handleChange}
                placeholder="Ex: Bureau direction, Salle serveur..."
              />

              <div className="form-group">
                <label className="input-label">Description</label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  className="input textarea"
                  rows="3"
                  placeholder="Description optionnelle de l'appareil..."
                />
              </div>

              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="actif"
                    checked={formData.actif}
                    onChange={handleChange}
                  />
                  <span className="checkbox-text">Appareil actif</span>
                </label>
              </div>
            </div>

            {/* Seuils d'alerte */}
            <div className="form-section">
              <h4>⚠️ Seuils d'alerte</h4>
              
              <div className="form-row">
                <Input
                  type="number"
                  name="seuil_tension_min"
                  label="Tension minimale (V)"
                  value={formData.seuil_tension_min}
                  onChange={handleChange}
                  error={errors.seuil_tension_min}
                  placeholder="Ex: 220"
                  step="0.1"
                />
                <Input
                  type="number"
                  name="seuil_tension_max"
                  label="Tension maximale (V)"
                  value={formData.seuil_tension_max}
                  onChange={handleChange}
                  error={errors.seuil_tension_max}
                  placeholder="Ex: 240"
                  step="0.1"
                />
              </div>

              <div className="form-row">
                <Input
                  type="number"
                  name="seuil_courant_max"
                  label="Courant maximal (A)"
                  value={formData.seuil_courant_max}
                  onChange={handleChange}
                  error={errors.seuil_courant_max}
                  placeholder="Ex: 16"
                  step="0.01"
                />
                <Input
                  type="number"
                  name="seuil_puissance_max"
                  label="Puissance maximale (W)"
                  value={formData.seuil_puissance_max}
                  onChange={handleChange}
                  error={errors.seuil_puissance_max}
                  placeholder="Ex: 3500"
                  step="1"
                />
              </div>
            </div>

            <div className="info-box">
              <strong>Note:</strong> Les seuils d'alerte permettent de détecter automatiquement 
              les anomalies et de générer des alertes en temps réel.
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
              {mode === 'edit' ? 'Modifier' : 'Créer'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default DeviceModal