import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../Button'
import Input from '../Input'
import './DeviceProtection.css'

const ProtectionModal = ({ device, onClose, onSave }) => {
  const [protectionConfig, setProtectionConfig] = useState({
    enabled: true,
    tension_protection: {
      enabled: true,
      min_threshold: 200.0,
      max_threshold: 250.0,
      auto_shutdown: true,
      restart_delay_minutes: 1,
      max_retries: 3
    },
    courant_protection: {
      enabled: true,
      max_threshold: 20.0,
      auto_shutdown: true,
      restart_delay_minutes: 5,
      max_retries: 2
    },
    temperature_protection: {
      enabled: true,
      max_threshold: 60.0,
      auto_shutdown: true,
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
        const config = response.data.protection_config
        if (config) {
          setProtectionConfig(prev => ({
            ...prev,
            ...config,
            enabled: response.data.protection_active
          }))
        }
      }
    } catch (error) {
      console.error('Erreur chargement protection:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigChange = (section, field, value) => {
    setProtectionConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }))
  }

  const handleMainToggle = (enabled) => {
    setProtectionConfig(prev => ({
      ...prev,
      enabled
    }))
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setErrors({})
      
      const response = await DeviceService.configurerProtectionAutomatique(
      device.id || device.tuya_device_id,
      protectionConfig // Cet objet sera encapsulé par DeviceService.js
    )
      
      if (response.data.success) {
        onSave()
      } else {
        setErrors({ general: response.data.error || 'Erreur lors de la sauvegarde' })
      }
    } catch (error) {
      setErrors({ 
        general: error.response?.data?.error || 'Erreur lors de la sauvegarde' 
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Configuration Protection</h3>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Chargement de la configuration...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

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
                  checked={protectionConfig.enabled}
                  onChange={(e) => handleMainToggle(e.target.checked)}
                />
                <label htmlFor="protection-enabled">
                  Protection automatique {protectionConfig.enabled ? 'activée' : 'désactivée'}
                </label>
              </div>
            </div>
          </div>

          {protectionConfig.enabled && (
            <>
              {/* Protection tension */}
              <div className="protection-section">
                <div className="section-header">
                  <h4>⚡ Protection Tension</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="tension-enabled"
                      checked={protectionConfig.tension_protection.enabled}
                      onChange={(e) => handleConfigChange('tension_protection', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="tension-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.tension_protection.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Tension min (V)"
                        value={protectionConfig.tension_protection.min_threshold}
                        onChange={(e) => handleConfigChange('tension_protection', 'min_threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                      <Input
                        type="number"
                        label="Tension max (V)"
                        value={protectionConfig.tension_protection.max_threshold}
                        onChange={(e) => handleConfigChange('tension_protection', 'max_threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="tension-auto-shutdown"
                          checked={protectionConfig.tension_protection.auto_shutdown}
                          onChange={(e) => handleConfigChange('tension_protection', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="tension-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.tension_protection.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('tension_protection', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.tension_protection.max_retries}
                          onChange={(e) => handleConfigChange('tension_protection', 'max_retries', parseInt(e.target.value))}
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
                      checked={protectionConfig.courant_protection.enabled}
                      onChange={(e) => handleConfigChange('courant_protection', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="courant-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.courant_protection.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Courant max (A)"
                        value={protectionConfig.courant_protection.max_threshold}
                        onChange={(e) => handleConfigChange('courant_protection', 'max_threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="courant-auto-shutdown"
                          checked={protectionConfig.courant_protection.auto_shutdown}
                          onChange={(e) => handleConfigChange('courant_protection', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="courant-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.courant_protection.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('courant_protection', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.courant_protection.max_retries}
                          onChange={(e) => handleConfigChange('courant_protection', 'max_retries', parseInt(e.target.value))}
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
                      checked={protectionConfig.temperature_protection.enabled}
                      onChange={(e) => handleConfigChange('temperature_protection', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="temp-enabled">Activée</label>
                  </div>
                </div>

                {protectionConfig.temperature_protection.enabled && (
                  <div className="protection-config">
                    <div className="config-grid">
                      <Input
                        type="number"
                        label="Température max (°C)"
                        value={protectionConfig.temperature_protection.max_threshold}
                        onChange={(e) => handleConfigChange('temperature_protection', 'max_threshold', parseFloat(e.target.value))}
                        step="0.1"
                        min="0"
                      />
                    </div>
                    
                    <div className="config-options">
                      <div className="checkbox-group">
                        <input
                          type="checkbox"
                          id="temp-auto-shutdown"
                          checked={protectionConfig.temperature_protection.auto_shutdown}
                          onChange={(e) => handleConfigChange('temperature_protection', 'auto_shutdown', e.target.checked)}
                        />
                        <label htmlFor="temp-auto-shutdown">Extinction automatique</label>
                      </div>
                      
                      <div className="restart-config">
                        <Input
                          type="number"
                          label="Délai redémarrage (min)"
                          value={protectionConfig.temperature_protection.restart_delay_minutes}
                          onChange={(e) => handleConfigChange('temperature_protection', 'restart_delay_minutes', parseInt(e.target.value))}
                          min="1"
                          max="60"
                        />
                        <Input
                          type="number"
                          label="Tentatives max"
                          value={protectionConfig.temperature_protection.max_retries}
                          onChange={(e) => handleConfigChange('temperature_protection', 'max_retries', parseInt(e.target.value))}
                          min="0"
                          max="10"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>

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

export default ProtectionModal
