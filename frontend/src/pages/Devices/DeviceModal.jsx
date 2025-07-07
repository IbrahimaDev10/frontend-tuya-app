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
  // MODIFICATION 1: Utiliser deviceData pour stocker les détails complets de l'appareil, y compris l'état Tuya
  const [deviceData, setDeviceData] = useState(null) 
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
      // MODIFICATION 2: Charger les données complètes de l'appareil au lieu de seulement le statut
      loadFullDeviceData() 
    }
  }, [device, mode])

  // MODIFICATION 3: Nouvelle fonction pour charger toutes les données de l'appareil
  const loadFullDeviceData = async () => {
    if (!device) return
    
    try {
      setRefreshing(true)
      // Utiliser device.id car c'est l'ID interne de votre DB, plus fiable pour obtenir les détails
      const response = await DeviceService.obtenirAppareil(device.id) 
      if (response.data.success) {
        setDeviceData(response.data.data) // Stocker toutes les données de l'appareil
      }
    } catch (error) {
      console.error('Erreur chargement données appareil:', error)
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

      // MODIFICATION 4: Utiliser device.id pour modifier l'appareil
      const response = await DeviceService.modifierAppareil(
        device.id, // Utilisez device.id ici
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

  // MODIFICATION 5: Adapter handleToggleDevice pour passer la valeur booléenne
  const handleToggleDevice = async () => {
    if (!deviceData) return; // S'assurer que les données de l'appareil sont chargées

    try {
      // Déterminer le nouvel état souhaité (inverse de l'état actuel)
      const targetState = !deviceData.etat_actuel_tuya; 
      const result = await DeviceService.toggleAppareil(device.tuya_device_id, targetState); // Passer la valeur
      
      if (result.success) {
        // MODIFICATION 6: Mettre à jour l'état local du modal avec le nouvel état
        setDeviceData(prev => ({
          ...prev,
          etat_actuel_tuya: result.newState // result.newState vient du backend
        }));
      } else {
        console.error('Erreur toggle:', result.message);
      }
    } catch (error) {
      console.error('Erreur toggle:', error);
    }
  }

  // MODIFICATION 7: Adapter handleCollectData pour rafraîchir les données complètes
  const handleCollectData = async () => {
    try {
      await DeviceService.collecterDonnees(device.id || device.tuya_device_id)
      await loadFullDeviceData() // Recharger toutes les données pour la mise à jour
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
                  onClick={loadFullDeviceData} // MODIFICATION 8: Appeler loadFullDeviceData
                  loading={refreshing}
                >
                  🔄 Actualiser
                </Button>
                {/* MODIFICATION 9: Utiliser deviceData pour vérifier le statut d'assignation */}
                {deviceData?.statut_assignation === 'assigne' && ( 
                  <>
                    <Button
                      variant="outline"
                      size="small"
                      onClick={handleToggleDevice}
                    >
                      {/* MODIFICATION 10: Utiliser deviceData.etat_actuel_tuya pour l'affichage du bouton */}
                      {deviceData?.etat_actuel_tuya ? '⏸️ OFF' : '▶️ ON'} 
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
            {/* MODIFICATION 11: Utiliser deviceData pour l'affichage des informations */}
            {deviceData && ( 
              <div className="device-info-card">
                <h4>📱 Informations de l'appareil</h4>
                <div className="device-details">
                  <div className="info-grid">
                    <div className="info-item">
                      <label>ID Tuya:</label>
                      <span className="code">{deviceData.tuya_device_id}</span>
                    </div>
                    <div className="info-item">
                      <label>Type:</label>
                      <span>{deviceData.type_appareil}</span>
                    </div>
                    <div className="info-item">
                      <label>Modèle:</label>
                      <span>{deviceData.tuya_modele}</span>
                    </div>
                    <div className="info-item">
                      <label>État:</label>
                      {/* MODIFICATION 12: Utiliser deviceData.etat_actuel_tuya pour l'affichage de l'état */}
                      <span className={`state-badge ${deviceData.etat_actuel_tuya ? 'on' : 'off'}`}>
                        {deviceData.etat_actuel_tuya ? 'ON' : 'OFF'}
                      </span>
                    </div>
                    <div className="info-item">
                      <label>En ligne:</label>
                      {/* MODIFICATION 13: Utiliser deviceData.en_ligne pour l'affichage en ligne */}
                      <span className={`online-badge ${deviceData.en_ligne ? 'online' : 'offline'}`}>
                        {deviceData.en_ligne ? '🟢 Oui' : '🔴 Non'}
                      </span>
                    </div>
                    <div className="info-item">
                      <label>Client:</label>
                      <span>{deviceData.client?.nom_entreprise || 'Non assigné'}</span>
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
