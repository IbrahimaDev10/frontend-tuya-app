import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../Button'
import Input from '../Input'
import './DeviceProtection.css'

const ScheduleModal = ({ device, onClose, onSave }) => {
  const [scheduleConfig, setScheduleConfig] = useState({
    enabled: true,
    timezone: "Africa/Dakar",
    override_protection: false,
    allumage: {
      enabled: true,
      time: "07:00",
      days: [1, 2, 3, 4, 5], // Lundi-Vendredi
      force_on: true
    },
    extinction: {
      enabled: true,
      time: "22:00",
      days: [1, 2, 3, 4, 5, 6, 7], // Tous les jours
      force_off: true
    }
  })
  const [scheduleStatus, setScheduleStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})

  const daysOfWeek = [
    { value: 1, label: 'Lundi' },
    { value: 2, label: 'Mardi' },
    { value: 3, label: 'Mercredi' },
    { value: 4, label: 'Jeudi' },
    { value: 5, label: 'Vendredi' },
    { value: 6, label: 'Samedi' },
    { value: 7, label: 'Dimanche' }
  ]

  useEffect(() => {
    if (device) {
      loadScheduleStatus()
    }
  }, [device])

  const loadScheduleStatus = async () => {
    try {
      setLoading(true)
      const response = await DeviceService.obtenirStatutProgrammation(device.tuya_device_id)
      
      if (response.data.success) {
        setScheduleStatus(response.data)
        const config = response.data.schedule_config
        if (config) {
          setScheduleConfig(prev => ({
            ...prev,
            ...config,
            enabled: response.data.programmation_active
          }))
        }
      }
    } catch (error) {
      console.error('Erreur chargement programmation:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleConfigChange = (section, field, value) => {
    setScheduleConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }))
  }

  const handleMainToggle = (enabled) => {
    setScheduleConfig(prev => ({
      ...prev,
      enabled
    }))
  }

  const handleDayToggle = (section, day) => {
    setScheduleConfig(prev => {
      const currentDays = prev[section].days
      const newDays = currentDays.includes(day)
        ? currentDays.filter(d => d !== day)
        : [...currentDays, day].sort()
      
      return {
        ...prev,
        [section]: {
          ...prev[section],
          days: newDays
        }
      }
    })
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setErrors({})
      
       const response = await DeviceService.configurerProgrammationHoraires(
      device.tuya_device_id,
      scheduleConfig // Cet objet sera envoyé directement par DeviceService.js
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

const handleDisable = async () => {
  try {
    setSaving(true)
    // Envoyer une requête POST à l'endpoint /programmation/config avec l'action 'disable'
    const response = await DeviceService.configurerProgrammationHoraires(
     device.tuya_device_id,
      { action: 'disable' } // Envoyer un objet avec l'action 'disable'
    )
    
    if (response.data.success) {
      onSave()
    } else {
      setErrors({ general: response.data.error || 'Erreur lors de la désactivation' })
    }
  } catch (error) {
    setErrors({ 
      general: error.response?.data?.error || 'Erreur lors de la désactivation' 
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
            <h3>Programmation Horaires</h3>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body">
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Chargement de la programmation...</p>
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
          <h3>⏰ Programmation Horaires - {device.nom_appareil}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {errors.general && (
            <div className="error-message">{errors.general}</div>
          )}

          {/* Activation générale */}
          <div className="schedule-section">
            <div className="section-header">
              <h4>Activation générale</h4>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="schedule-enabled"
                  checked={scheduleConfig.enabled}
                  onChange={(e) => handleMainToggle(e.target.checked)}
                />
                <label htmlFor="schedule-enabled">
                  Programmation {scheduleConfig.enabled ? 'activée' : 'désactivée'}
                </label>
              </div>
            </div>

            {scheduleConfig.enabled && (
              <div className="general-options">
                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="override-protection"
                    checked={scheduleConfig.override_protection}
                    onChange={(e) => handleConfigChange('', 'override_protection', e.target.checked)}
                  />
                  <label htmlFor="override-protection">
                    Ignorer la protection automatique lors des actions programmées
                  </label>
                </div>
              </div>
            )}
          </div>

          {scheduleConfig.enabled && (
            <>
              {/* Programmation allumage */}
              <div className="schedule-section">
                <div className="section-header">
                  <h4>🌅 Allumage automatique</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="allumage-enabled"
                      checked={scheduleConfig.allumage.enabled}
                      onChange={(e) => handleConfigChange('allumage', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="allumage-enabled">Activé</label>
                  </div>
                </div>

                {scheduleConfig.allumage.enabled && (
                  <div className="schedule-config">
                    <div className="time-config">
                      <Input
                        type="time"
                        label="Heure d'allumage"
                        value={scheduleConfig.allumage.time}
                        onChange={(e) => handleConfigChange('allumage', 'time', e.target.value)}
                      />
                    </div>

                    <div className="days-config">
                      <label className="input-label">Jours de la semaine</label>
                      <div className="days-grid">
                        {daysOfWeek.map(day => (
                          <div key={day.value} className="day-checkbox">
                            <input
                              type="checkbox"
                              id={`allumage-day-${day.value}`}
                              checked={scheduleConfig.allumage.days.includes(day.value)}
                              onChange={() => handleDayToggle('allumage', day.value)}
                            />
                            <label htmlFor={`allumage-day-${day.value}`}>
                              {day.label}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="checkbox-group">
                      <input
                        type="checkbox"
                        id="force-on"
                        checked={scheduleConfig.allumage.force_on}
                        onChange={(e) => handleConfigChange('allumage', 'force_on', e.target.checked)}
                      />
                      <label htmlFor="force-on">
                        Forcer l'allumage même si l'appareil est déjà allumé
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Programmation extinction */}
              <div className="schedule-section">
                <div className="section-header">
                  <h4>🌙 Extinction automatique</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="extinction-enabled"
                      checked={scheduleConfig.extinction.enabled}
                      onChange={(e) => handleConfigChange('extinction', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="extinction-enabled">Activée</label>
                  </div>
                </div>

                {scheduleConfig.extinction.enabled && (
                  <div className="schedule-config">
                    <div className="time-config">
                      <Input
                        type="time"
                        label="Heure d'extinction"
                        value={scheduleConfig.extinction.time}
                        onChange={(e) => handleConfigChange('extinction', 'time', e.target.value)}
                      />
                    </div>

                    <div className="days-config">
                      <label className="input-label">Jours de la semaine</label>
                      <div className="days-grid">
                        {daysOfWeek.map(day => (
                          <div key={day.value} className="day-checkbox">
                            <input
                              type="checkbox"
                              id={`extinction-day-${day.value}`}
                              checked={scheduleConfig.extinction.days.includes(day.value)}
                              onChange={() => handleDayToggle('extinction', day.value)}
                            />
                            <label htmlFor={`extinction-day-${day.value}`}>
                              {day.label}
                            </label>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="checkbox-group">
                      <input
                        type="checkbox"
                        id="force-off"
                        checked={scheduleConfig.extinction.force_off}
                        onChange={(e) => handleConfigChange('extinction', 'force_off', e.target.checked)}
                      />
                      <label htmlFor="force-off">
                        Forcer l'extinction même si l'appareil est déjà éteint
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Statut actuel */}
              {scheduleStatus && (
                <div className="schedule-section">
                  <h4>📊 Statut actuel</h4>
                  <div className="status-info">
                    <div className="status-grid">
                      <div className="status-item">
                        <label>Actions actives:</label>
                        <span>{scheduleStatus.active_actions || 0}</span>
                      </div>
                      <div className="status-item">
                        <label>Total actions:</label>
                        <span>{scheduleStatus.total_actions || 0}</span>
                      </div>
                    </div>

                    {scheduleStatus.next_actions && scheduleStatus.next_actions.length > 0 && (
                      <div className="next-actions">
                        <h5>Prochaines actions :</h5>
                        <div className="actions-list">
                          {scheduleStatus.next_actions.slice(0, 3).map((action, index) => (
                            <div key={index} className="action-item">
                              <span className="action-type">
                                {action.action_type === 'turn_on' ? '🌅' : '🌙'} 
                                {action.action_type === 'turn_on' ? 'Allumage' : 'Extinction'}
                              </span>
                              <span className="action-time">
                                {new Date(action.scheduled_time).toLocaleString('fr-FR')}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="info-box">
                <strong>ℹ️ Information :</strong> La programmation horaires permet d'allumer et éteindre 
                automatiquement l'appareil selon les créneaux configurés. Les actions sont exécutées 
                même si l'appareil est en mode manuel, sauf si vous cochez l'option de forçage.
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
          
          {scheduleConfig.enabled && (
            <Button
              type="button"
              variant="danger"
              onClick={handleDisable}
              loading={saving}
            >
              Désactiver tout
            </Button>
          )}
          
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

export default ScheduleModal
