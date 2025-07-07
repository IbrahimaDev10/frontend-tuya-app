import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../Button'
import Input from '../Input'

// Dans ProtectionModal.jsx
import './ProtectionModal.css';




const ProtectionModal = ({ device, onClose, onSave }) => {
  // Initialisation de l'état avec une structure qui correspond à la fois au formulaire
  // et à ce que le backend attend/renvoie.
  // Utilisez les noms de clés du backend pour les sections de protection.
  const [protectionConfig, setProtectionConfig] = useState({
    protection_automatique_active: false, // Correspond à la clé globale du backend
    protection_tension_config: {
      enabled: false,
      threshold_min: 200.0,
      threshold_max: 250.0,
      action: "turn_off",
      cooldown_minutes: 5,
      auto_restart: true,
      restart_delay_minutes: 10,
      max_retries: 3
    },
    protection_courant_config: {
      enabled: false,
      threshold: 20.0,
      action: "turn_off",
      cooldown_minutes: 5,
      auto_restart: true,
      restart_delay_minutes: 10,
      max_retries: 2
    },
    protection_temperature_config: {
      enabled: false,
      threshold: 60.0,
      action: "turn_off",
      cooldown_minutes: 10,
      auto_restart: true,
      restart_delay_minutes: 30,
      max_retries: 1
    },
    protection_desequilibre_config: { // Pour les appareils triphasés
      enabled: false,
      threshold_tension: 2.0,
      threshold_courant: 10.0,
      action: "turn_off",
      cooldown_minutes: 5,
      auto_restart: true,
      restart_delay_minutes: 10,
      max_retries: 1
    }
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})

  useEffect(() => {
    if (device) {
      loadProtectionConfig()
    }
  }, [device])

  const loadProtectionConfig = async () => {
    try {
      setLoading(true)
      const response = await DeviceService.obtenirStatutProtection(device.id || device.tuya_device_id)
      
      if (response.data.success) {
        const backendConfig = response.data // La réponse contient directement les clés
        
        // Mappez la réponse du backend à votre état local
        setProtectionConfig(prev => ({
          ...prev,
          protection_automatique_active: backendConfig.protection_active,
          protection_tension_config: { 
            ...prev.protection_tension_config, 
            ...backendConfig.protection_config.configurations.tension 
          },
          protection_courant_config: { 
            ...prev.protection_courant_config, 
            ...backendConfig.protection_config.configurations.courant 
          },
          protection_temperature_config: { 
            ...prev.protection_temperature_config, 
            ...backendConfig.protection_config.configurations.temperature 
          },
          // N'oubliez pas le déséquilibre si l'appareil est triphasé
          ...(device.type_systeme === 'triphase' && {
            protection_desequilibre_config: {
              ...prev.protection_desequilibre_config,
              ...backendConfig.protection_config.configurations.desequilibre
            }
          })
        }))
      }
    } catch (error) {
      console.error('Erreur chargement protection:', error)
      // Gérer l'erreur, peut-être définir un état d'erreur
    } finally {
      setLoading(false)
    }
  }

  // Fonction générique pour gérer les changements dans les sous-sections de protection
  const handleConfigChange = (sectionKey, field, value) => {
    setProtectionConfig(prev => ({
      ...prev,
      [sectionKey]: {
        ...prev[sectionKey],
        [field]: value
      }
    }))
  }

  // Gérer le toggle principal
  const handleMainToggle = (enabled) => {
    setProtectionConfig(prev => ({
      ...prev,
      protection_automatique_active: enabled
    }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setErrors({})
      
      // Construisez l'objet à envoyer au backend.
      // Le backend attend un objet avec les clés de configuration directement.
      const payload = {
        protection_automatique_active: protectionConfig.protection_automatique_active,
        protection_courant_config: protectionConfig.protection_courant_config,
        protection_puissance_config: protectionConfig.protection_puissance_config,
        protection_temperature_config: protectionConfig.protection_temperature_config,
        protection_tension_config: protectionConfig.protection_tension_config,
        // Inclure le déséquilibre uniquement si l'appareil est triphasé
        ...(device.type_systeme === 'triphase' && {
          protection_desequilibre_config: protectionConfig.protection_desequilibre_config
        })
      };

      // Le backend attend un objet avec les clés de configuration directement.
      // La route POST /devices/{device_id}/protection/config prend directement le payload.
      const response = await DeviceService.configurerProtectionAutomatique(
        device.id || device.tuya_device_id,
        payload // Envoyez le payload directement
      )
      
      if (response.data.success) {
        onSave() // Appeler la fonction de rappel pour fermer le modal et rafraîchir
      } else {
        setErrors({ general: response.data.error || 'Erreur lors de la sauvegarde' })
      }
    } catch (error) {
      setErrors({ 
        general: error.response?.data?.error || 'Erreur lors de la sauvegarde' 
      })
      console.error("Erreur sauvegarde protection:", error);
    } finally {
      setSaving(false)
    }
  }

  // ... (le reste de votre JSX, en ajustant les noms de clés)
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>🛡️ Protection Automatique - {device.nom_appareil}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {errors.general && (
            <div className="error-message">{errors.general}</div>
          )}

          {/* Activation générale */}
          <div className="protection-section">
            <div className="section-header">
              <h4>Activation générale</h4>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="protection-enabled"
                  checked={protectionConfig.protection_automatique_active} // Utilisez la clé du backend
                  onChange={(e) => handleMainToggle(e.target.checked)}
                />
                <label htmlFor="protection-enabled">
                  Protection automatique {protectionConfig.protection_automatique_active ? 'activée' : 'désactivée'}
                </label>
              </div>
            </div>
          </div>

          {protectionConfig.protection_automatique_active && (
            <>
              {/* Protection tension */}
              <div className="protection-section">
                <div className="section-header">
                  <h4>⚡ Protection Tension</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="tension-enabled"
                      checked={protectionConfig.protection_tension_config.enabled}
                      onChange={(e) => handleConfigChange('protection_tension_config', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="tension-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.protection_tension_config.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Tension min (V)"
                        value={protectionConfig.protection_tension_config.threshold_min}
                        onChange={(e) => handleConfigChange('protection_tension_config', 'threshold_min', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                      <Input
                        type="number"
                        label="Tension max (V)"
                        value={protectionConfig.protection_tension_config.threshold_max}
                        onChange={(e) => handleConfigChange('protection_tension_config', 'threshold_max', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="tension-auto-shutdown"
                          checked={protectionConfig.protection_tension_config.auto_shutdown}
                          onChange={(e) => handleConfigChange('protection_tension_config', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="tension-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.protection_tension_config.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('protection_tension_config', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.protection_tension_config.max_retries}
                          onChange={(e) => handleConfigChange('protection_tension_config', 'max_retries', parseInt(e.target.value))}
                          min="0"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Protection courant */}
              <div className="protection-section">
                <div className="section-header">
                  <h4>🔌 Protection Courant</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="courant-enabled"
                      checked={protectionConfig.protection_courant_config.enabled}
                      onChange={(e) => handleConfigChange('protection_courant_config', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="courant-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.protection_courant_config.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Courant max (A)"
                        value={protectionConfig.protection_courant_config.threshold} // Utilisez 'threshold'
                        onChange={(e) => handleConfigChange('protection_courant_config', 'threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="courant-auto-shutdown"
                          checked={protectionConfig.protection_courant_config.auto_shutdown}
                          onChange={(e) => handleConfigChange('protection_courant_config', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="courant-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.protection_courant_config.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('protection_courant_config', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.protection_courant_config.max_retries}
                          onChange={(e) => handleConfigChange('protection_courant_config', 'max_retries', parseInt(e.target.value))}
                          min="0"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Protection température */}
              <div className="protection-section">
                <div className="section-header">
                  <h4>🌡️ Protection Température</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="temp-enabled"
                      checked={protectionConfig.protection_temperature_config.enabled}
                      onChange={(e) => handleConfigChange('protection_temperature_config', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="temp-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.protection_temperature_config.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Température max (°C)"
                        value={protectionConfig.protection_temperature_config.threshold} // Utilisez 'threshold'
                        onChange={(e) => handleConfigChange('protection_temperature_config', 'threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="temp-auto-shutdown"
                          checked={protectionConfig.protection_temperature_config.auto_shutdown}
                          onChange={(e) => handleConfigChange('protection_temperature_config', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="temp-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.protection_temperature_config.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('protection_temperature_config', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.protection_temperature_config.max_retries}
                          onChange={(e) => handleConfigChange('protection_temperature_config', 'max_retries', parseInt(e.target.value))}
                          min="0"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Protection Déséquilibre (afficher uniquement pour les appareils triphasés) */}
              {device.type_systeme === 'triphase' && (
                <div className="protection-section">
                  <div className="section-header">
                    <h4>⚖️ Protection Déséquilibre</h4>
                    <div className="toggle-switch">
                      <input
                        type="checkbox"
                        id="desequilibre-enabled"
                        checked={protectionConfig.protection_desequilibre_config.enabled}
                        onChange={(e) => handleConfigChange('protection_desequilibre_config', 'enabled', e.target.checked)}
                      />
                      <label htmlFor="desequilibre-enabled">Activée</label>
                    </div>
                  </div>

                  {protectionConfig.protection_desequilibre_config.enabled && (
                    <div className="protection-config">
                      <div className="config-grid">
                        <Input
                          type="number"
                          label="Déséquilibre Tension (%)"
                          value={protectionConfig.protection_desequilibre_config.threshold_tension}
                          onChange={(e) => handleConfigChange('protection_desequilibre_config', 'threshold_tension', parseFloat(e.target.value))}
                          step="0.1"
                          min="0"
                        />
                        <Input
                          type="number"
                          label="Déséquilibre Courant (%)"
                          value={protectionConfig.protection_desequilibre_config.threshold_courant}
                          onChange={(e) => handleConfigChange('protection_desequilibre_config', 'threshold_courant', parseFloat(e.target.value))}
                          step="0.1"
                          min="0"
                        />
                      </div>
                      
                      <div className="config-options">
                        <div className="checkbox-group">
                          <input
                            type="checkbox"
                            id="desequilibre-auto-shutdown"
                            checked={protectionConfig.protection_desequilibre_config.auto_shutdown}
                            onChange={(e) => handleConfigChange('protection_desequilibre_config', 'auto_shutdown', e.target.checked)}
                          />
                          <label htmlFor="desequilibre-auto-shutdown">Extinction automatique</label>
                        </div>
                        
                        <div className="restart-config">
                          <Input
                            type="number"
                            label="Délai redémarrage (min)"
                            value={protectionConfig.protection_desequilibre_config.restart_delay_minutes}
                            onChange={(e) => handleConfigChange('protection_desequilibre_config', 'restart_delay_minutes', parseInt(e.target.value))}
                            min="1"
                            max="60"
                          />
                          <Input
                            type="number"
                            label="Tentatives max"
                            value={protectionConfig.protection_desequilibre_config.max_retries}
                            onChange={(e) => handleConfigChange('protection_desequilibre_config', 'max_retries', parseInt(e.target.value))}
                            min="0"
                            max="10"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="info-box">
                <strong>ℹ️ Information :</strong> La protection automatique surveille en temps réel les mesures 
                de l'appareil. En cas de dépassement des seuils configurés, l'appareil sera automatiquement 
                éteint pour éviter les dommages, puis rallumé après le délai configuré si les conditions 
                sont redevenues normales.
              </div>
            </>
          )}
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
            type="button"
            variant="primary"
            onClick={handleSave}
            loading={saving}
          >
            Sauvegarder
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ProtectionModal;
