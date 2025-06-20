import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import ActivationService from '../services/activationService'
import Button from '../components/Button'
import Input from '../components/Input'
import Toast from '../components/Toast'
import './Auth.css'

const AdminActivation = () => {
  const { token } = useParams()
  const navigate = useNavigate()
  
  const [formData, setFormData] = useState({
    motDePasse: '',
    confirmMotDePasse: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [validatingToken, setValidatingToken] = useState(true)
  const [tokenValid, setTokenValid] = useState(false)
  const [adminInfo, setAdminInfo] = useState(null)
  const [toast, setToast] = useState(null)
  const [activationSuccess, setActivationSuccess] = useState(false)

  useEffect(() => {
    if (token) {
      validateToken()
    }
  }, [token])

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  const validateToken = async () => {
    try {
      setValidatingToken(true)
      const response = await ActivationService.validerTokenActivation(token)
      
      if (response.data.valid) {
        setTokenValid(true)
        setAdminInfo(response.data.admin_info)
      } else {
        setTokenValid(false)
        showToast('Token d\'activation invalide ou expiré', 'error')
      }
    } catch (error) {
      setTokenValid(false)
      showToast(
        error.response?.data?.error || 'Erreur lors de la validation du token',
        'error'
      )
    } finally {
      setValidatingToken(false)
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
    
    if (!formData.motDePasse) {
      newErrors.motDePasse = 'Mot de passe requis'
    } else if (formData.motDePasse.length < 8) {
      newErrors.motDePasse = 'Le mot de passe doit contenir au moins 8 caractères'
    }
    
    if (!formData.confirmMotDePasse) {
      newErrors.confirmMotDePasse = 'Confirmation du mot de passe requise'
    } else if (formData.motDePasse !== formData.confirmMotDePasse) {
      newErrors.confirmMotDePasse = 'Les mots de passe ne correspondent pas'
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
      const response = await ActivationService.activerAdmin(
        token,
        formData.motDePasse,
        formData.confirmMotDePasse
      )
      
      setActivationSuccess(true)
      showToast('Compte activé avec succès ! Vous pouvez maintenant vous connecter.', 'success')
      
      // Rediriger vers la page de connexion après 3 secondes
      setTimeout(() => {
        navigate('/login')
      }, 3000)
      
    } catch (error) {
      setErrors({
        general: error.response?.data?.error || 'Erreur lors de l\'activation'
      })
    } finally {
      setLoading(false)
    }
  }

  if (validatingToken) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="logo-placeholder">
              <img src="/assets/images/sertec_logo.jpeg" alt="Logo" />
            </div>
            <h2>Validation du token...</h2>
            <div className="loading-spinner"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!tokenValid) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="logo-placeholder">
              <img src="/assets/images/sertec_logo.jpeg" alt="Logo" />
            </div>
            <h2>Token invalide</h2>
            <p>Le lien d'activation est invalide ou a expiré.</p>
          </div>
          <div className="auth-actions">
            <Link to="/login" className="btn btn-primary">
              Retour à la connexion
            </Link>
          </div>
        </div>
        {toast && <Toast message={toast.message} type={toast.type} />}
      </div>
    )
  }

  if (activationSuccess) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="logo-placeholder">
              <img src="/assets/images/sertec_logo.jpeg" alt="Logo" />
            </div>
            <h2>✅ Activation réussie !</h2>
            <p>Votre compte administrateur a été activé avec succès.</p>
            <p>Vous allez être redirigé vers la page de connexion...</p>
          </div>
          <div className="auth-actions">
            <Link to="/login" className="btn btn-primary">
              Se connecter maintenant
            </Link>
          </div>
        </div>
        {toast && <Toast message={toast.message} type={toast.type} />}
      </div>
    )
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo-placeholder">
            <img src="/assets/images/sertec_logo.jpeg" alt="Logo" />
          </div>
          <h2>Activation du compte administrateur</h2>
          {adminInfo && (
            <div className="admin-info">
              <p>Bonjour <strong>{adminInfo.prenom} {adminInfo.nom}</strong></p>
              <p>Client: <strong>{adminInfo.client_name}</strong></p>
              <p>Définissez votre mot de passe pour activer votre compte.</p>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {errors.general && (
            <div className="error-message general-error">
              {errors.general}
            </div>
          )}

          <Input
            type="password"
            name="motDePasse"
            placeholder="Nouveau mot de passe"
            value={formData.motDePasse}
            onChange={handleChange}
            error={errors.motDePasse}
            required
          />

          <Input
            type="password"
            name="confirmMotDePasse"
            placeholder="Confirmer le mot de passe"
            value={formData.confirmMotDePasse}
            onChange={handleChange}
            error={errors.confirmMotDePasse}
            required
          />

          <div className="password-requirements">
            <small>
              Le mot de passe doit contenir au moins 8 caractères.
            </small>
          </div>

          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={loading}
            disabled={loading}
          >
            Activer mon compte
          </Button>
        </form>

        <div className="auth-footer">
          <Link to="/login">Retour à la connexion</Link>
        </div>
      </div>
      
      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}

export default AdminActivation