import React, { useState } from 'react'
import { useAuth } from '../store/authContext'
import { changePassword } from '../services/authService'
import Button from './Button'
import Input from './Input'
import './Modal.css'

const ChangePasswordModal = ({ onClose }) => {
  const { token } = useAuth()
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  })
  const [errors, setErrors] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)

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
    
    if (!formData.oldPassword) {
      newErrors.oldPassword = 'Ancien mot de passe requis'
    }
    
    if (!formData.newPassword) {
      newErrors.newPassword = 'Nouveau mot de passe requis'
    } else if (formData.newPassword.length < 6) {
      newErrors.newPassword = 'Le mot de passe doit contenir au moins 6 caractères'
    }
    
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Confirmation requise'
    } else if (formData.newPassword !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Les mots de passe ne correspondent pas'
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

    setIsLoading(true)
    setErrors({})

    try {
      await changePassword(formData.oldPassword, formData.newPassword, token)
      setSuccess(true)
      setTimeout(() => {
        onClose()
      }, 2000)
    } catch (error) {
      setErrors({
        general: error.response?.data?.message || 'Erreur lors du changement de mot de passe'
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Changer le mot de passe</h3>
          <button className="modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        {success ? (
          <div className="modal-body">
            <div className="success-message">
              Mot de passe modifié avec succès !
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="modal-body">
              {errors.general && (
                <div className="error-message">
                  {errors.general}
                </div>
              )}

              <Input
                type="password"
                name="oldPassword"
                label="Ancien mot de passe"
                value={formData.oldPassword}
                onChange={handleChange}
                error={errors.oldPassword}
                required
              />

              <Input
                type="password"
                name="newPassword"
                label="Nouveau mot de passe"
                value={formData.newPassword}
                onChange={handleChange}
                error={errors.newPassword}
                required
              />

              <Input
                type="password"
                name="confirmPassword"
                label="Confirmer le nouveau mot de passe"
                value={formData.confirmPassword}
                onChange={handleChange}
                error={errors.confirmPassword}
                required
              />
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
                loading={isLoading}
              >
                Modifier
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

export default ChangePasswordModal