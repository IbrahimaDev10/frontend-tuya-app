import React, { useState, useEffect } from 'react'
import DeviceService from '../../services/deviceService'
import Button from '../Button'
import Input from '../Input'

// Dans ScheduleModal.jsx
import './ScheduleModal.css';


const ScheduleModal = ({ device, onClose, onSave }) => {
  // Initialisation de l'état avec une structure qui correspond à la fois au formulaire
  // et à ce que le backend attend/renvoie.
  // Utilisez les noms de clés du backend pour les sections de programmation.
  const [scheduleConfig, setScheduleConfig] = useState({
    programmation_active: false, // Correspond à la clé globale du backend
    timezone: "Africa/Dakar",
    override_protection: false, // Si cette option existe dans votre backend
    horaires_config: { // L'objet qui contient les configurations d'allumage/extinction
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
    }
  })
  const [scheduleStatus, setScheduleStatus] = useState(null) // Pour afficher des infos de statut
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
      const response = await DeviceService.obtenirStatutProgrammation(device.id || device.tuya_device_id)
      
      if (response.data.success) {
        setScheduleStatus(response.data) // Stocke le statut complet pour affichage
        const backendConfig = response.data // La réponse contient directement les clés
        
        // Mappez la réponse du backend à votre état local
        setScheduleConfig(prev => ({
          ...prev,
          programmation_active: backendConfig.programmation_active,
          timezone: backendConfig.schedule_config?.timezone || prev.timezone, // Utilisez schedule_config
          override_protection: backendConfig.schedule_config?.override_protection || prev.override_protection, // Si applicable
          horaires_config: {
            allumage: {
              ...prev.horaires_config.allumage,
              ...backendConfig.schedule_config?.allumage // Utilisez schedule_config
            },
            extinction: {
              ...prev.horaires_config.extinction,
              ...backendConfig.schedule_config?.extinction // Utilisez schedule_config
            }
          }
        }))
      }
    } catch (error) {
      console.error('Erreur chargement programmation:', error)
      // Gérer l'erreur, peut-être définir un état d'erreur
    } finally {
      setLoading(false)
    }
  }

  // Gère les changements dans les sous-sections (allumage, extinction)
  const handleConfigChange = (sectionKey, field, value) => {
    setScheduleConfig(prev => ({
      ...prev,
      horaires_config: {
        ...prev.horaires_config,
        [sectionKey]: {
          ...prev.horaires_config[sectionKey],
          [field]: value
        }
      }
    }))
  }

  // Gère le toggle principal de la programmation
  const handleMainToggle = (enabled) => {
    setScheduleConfig(prev => ({
      ...prev,
      programmation_active: enabled
    }))
  }

  // Gère le toggle des jours de la semaine
  const handleDayToggle = (sectionKey, day) => {
    setScheduleConfig(prev => {
      const currentDays = prev.horaires_config[sectionKey].days
      const newDays = currentDays.includes(day)
        ? currentDays.filter(d => d !== day)
        : [...currentDays, day].sort((a, b) => a - b) // S'assurer que les jours sont triés
      
      return {
        ...prev,
        horaires_config: {
          ...prev.horaires_config,
          [sectionKey]: {
            ...prev.horaires_config[sectionKey],
            days: newDays
          }
        }
      }
    })
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setErrors({})
      
      // Le payload doit correspondre à ce que le backend attend pour /programmation/config
      // C'est-à-dire un objet avec 'action: configure' et les détails de la configuration
      const payload = {
        programmation_active: scheduleConfig.programmation_active,
        timezone: scheduleConfig.timezone,
        override_protection: scheduleConfig.override_protection,
        allumage: scheduleConfig.horaires_config.allumage,
        extinction: scheduleConfig.horaires_config.extinction
      };

      const response = await DeviceService.configurerProgrammationHoraires(
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
      console.error("Erreur sauvegarde programmation:", error);
    } finally {
      setSaving(false)
    }
  }

  const handleDisable = async () => {
    try {
      setSaving(true)
      setErrors({})
      const response = await DeviceService.desactiverProgrammation(device.id || device.tuya_device_id)
      
      if (response.data.success) {
        onSave() // Appeler la fonction de rappel pour fermer le modal et rafraîchir
      } else {
        setErrors({ general: response.data.error || 'Erreur lors de la désactivation' })
      }
    } catch (error) {
      setErrors({ 
        general: error.response?.data?.error || 'Erreur lors de la désactivation' 
      })
      console.error("Erreur désactivation programmation:", error);
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>Configuration Programmation</h3>
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
          <h3>⏰ Programmation Horaire - {device.nom_appareil}</h3>
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
                  checked={scheduleConfig.programmation_active} // Utilisez la clé du backend
                  onChange={(e) => handleMainToggle(e.target.checked)}
                />
                <label htmlFor="schedule-enabled">
                  Programmation {scheduleConfig.programmation_active ? 'activée' : 'désactivée'}
                </label>
              </div>
            </div>
          </div>

          {scheduleConfig.programmation_active && (
            <>
              {/* Fuseau horaire */}
              <div className="schedule-section">
                <div className="section-header">
                  <h4>🌍 Fuseau Horaire</h4>
                </div>
                <div className="schedule-config">
                  <Input
                    type="text"
                    label="Fuseau Horaire (ex: Africa/Dakar)"
                    value={scheduleConfig.timezone}
                    onChange={(e) => setScheduleConfig(prev => ({ ...prev, timezone: e.target.value }))}
                  />
                </div>
              </div>

              {/* Option d'override protection (si applicable) */}
              {/* <div className="schedule-section">
                <div className="section-header">
                  <h4>Override Protection</h4>
                </div>
                <div className="schedule-config">
                  <div className="checkbox-group">
                    <input
                      type="checkbox"
                      id="override-protection"
                      checked={scheduleConfig.override_protection}
                      onChange={(e) => setScheduleConfig(prev => ({ ...prev, override_protection: e.target.checked }))}
                    />
                    <label htmlFor="override-protection">
                      Ignorer la protection automatique pendant la programmation
                    </label>
                  </div>
                </div>
              </div> */}

              {/* Section Allumage */}
              <div className="schedule-section">
                <div className="section-header">
                  <h4>💡 Allumage</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="allumage-enabled"
                      checked={scheduleConfig.horaires_config.allumage.enabled}
                      onChange={(e) => handleConfigChange('allumage', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="allumage-enabled">Activé</label>
                  </div>
                </div>

                {scheduleConfig.horaires_config.allumage.enabled && (
                  <div className="schedule-config">
                    <Input
                      type="time"
                      label="Heure d'allumage"
                      value={scheduleConfig.horaires_config.allumage.time}
                      onChange={(e) => handleConfigChange('allumage', 'time', e.target.value)}
                    />
                    <div className="days-selector">
                      {daysOfWeek.map(day => (
                        <Button
                          key={day.value}
                          variant={scheduleConfig.horaires_config.allumage.days.includes(day.value) ? 'primary' : 'outline'}
                          size="small"
                          onClick={() => handleDayToggle('allumage', day.value)}
                        >
                          {day.label.substring(0, 3)}
                        </Button>
                      ))}
                    </div>
                    <div className="checkbox-group">
                      <input
                        type="checkbox"
                        id="allumage-force-on"
                        checked={scheduleConfig.horaires_config.allumage.force_on}
                        onChange={(e) => handleConfigChange('allumage', 'force_on', e.target.checked)}
                      />
                      <label htmlFor="allumage-force-on">Forcer l'allumage (même si déjà ON)</label>
                    </div>
                  </div>
                )}
              </div>

              {/* Section Extinction */}
              <div className="schedule-section">
                <div className="section-header">
                  <h4>🌑 Extinction</h4>
                  <div className="toggle-switch">
                    <input
                      type="checkbox"
                      id="extinction-enabled"
                      checked={scheduleConfig.horaires_config.extinction.enabled}
                      onChange={(e) => handleConfigChange('extinction', 'enabled', e.target.checked)}
                    />
                    <label htmlFor="extinction-enabled">Activée</label>
                  </div>
                </div>

                {scheduleConfig.horaires_config.extinction.enabled && (
                  <div className="schedule-config">
                    <Input
                      type="time"
                      label="Heure d'extinction"
                      value={scheduleConfig.horaires_config.extinction.time}
                      onChange={(e) => handleConfigChange('extinction', 'time', e.target.value)}
                    />
                    <div className="days-selector">
                      {daysOfWeek.map(day => (
                        <Button
                          key={day.value}
                          variant={scheduleConfig.horaires_config.extinction.days.includes(day.value) ? 'primary' : 'outline'}
                          size="small"
                          onClick={() => handleDayToggle('extinction', day.value)}
                        >
                          {day.label.substring(0, 3)}
                        </Button>
                      ))}
                    </div>
                    <div className="checkbox-group">
                      <input
                        type="checkbox"
                        id="extinction-force-off"
                        checked={scheduleConfig.horaires_config.extinction.force_off}
                        onChange={(e) => handleConfigChange('extinction', 'force_off', e.target.checked)}
                      />
                      <label htmlFor="extinction-force-off">Forcer l'extinction (même si déjà OFF)</label>
                    </div>
                  </div>
                )}
              </div>

              {/* Informations sur la prochaine action programmée */}
              {scheduleStatus && scheduleStatus.prochaine_action && (
                <div className="info-box">
                  <strong>Prochaine action :</strong> {scheduleStatus.prochaine_action_type === 'turn_on' ? 'Allumage' : 'Extinction'} à {new Date(scheduleStatus.prochaine_action).toLocaleTimeString()}
                  {scheduleStatus.temps_jusqu_execution && ` (dans ${scheduleStatus.temps_jusqu_execution})`}
                </div>
              )}

              <div className="info-box">
                <strong>ℹ️ Information :</strong> La programmation horaire permet de définir des plages 
                d'allumage et d'extinction automatiques pour cet appareil. Les actions seront exécutées 
                selon le fuseau horaire configuré.
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
            variant="danger"
            onClick={handleDisable}
            loading={saving}
            disabled={!scheduleConfig.programmation_active} // Désactiver si déjà inactif
          >
            Désactiver la programmation
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

export default ScheduleModal
