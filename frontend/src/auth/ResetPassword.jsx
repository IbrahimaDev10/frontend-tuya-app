import React, { useState, useEffect } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { resetPasswordConfirm, verifyResetToken } from '../services/authService'
import Button from '../components/Button'
import Input from '../components/Input'
import './Auth.css'

const ResetPassword = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')

  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: ''
  })
  
  const [tokenInfo, setTokenInfo] = useState(null)
  const [timeRemaining, setTimeRemaining] = useState(0)
  const [errors, setErrors] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [isVerifyingToken, setIsVerifyingToken] = useState(true)
  const [message, setMessage] = useState('')
  const [tokenValid, setTokenValid] = useState(false)

  // ✅ NOUVEAU : Vérifier le token au chargement
  useEffect(() => {
    if (!token) {
      setErrors({ general: 'Token de réinitialisation manquant dans l\'URL' })
      setIsVerifyingToken(false)
      return
    }

    verifyTokenValidity()
  }, [token])

  // ✅ NOUVEAU : Countdown timer
  useEffect(() => {
    if (timeRemaining <= 0) return

    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          setTokenValid(false)
          setErrors({ general: 'Le lien de réinitialisation a expiré' })
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [timeRemaining])

  const verifyTokenValidity = async () => {
    try {
      setIsVerifyingToken(true)
      const response = await verifyResetToken(token)
      
      if (response.data.success) {
        setTokenInfo(response.data.data)
        setTimeRemaining(response.data.data.seconds_remaining)
        setTokenValid(true)
      } else {
        setErrors({ general: 'Token de réinitialisation invalide' })
        setTokenValid(false)
      }
    } catch (error) {
      setErrors({ 
        general: error.response?.data?.error || 'Token invalide ou expiré' 
      })
      setTokenValid(false)
    } finally {
      setIsVerifyingToken(false)
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

  // ✅ AMÉLIORÉ : Validation renforcée
  const validateForm = () => {
    const newErrors = {}

    // Validation mot de passe
    if (!formData.password) {
      newErrors.password = 'Mot de passe requis'
    } else if (formData.password.length < 8) {
      newErrors.password = 'Le mot de passe doit contenir au moins 8 caractères'
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password = 'Le mot de passe doit contenir au moins une majuscule, une minuscule et un chiffre'
    }

    // Validation confirmation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Confirmation requise'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Les mots de passe ne correspondent pas'
    }

    return newErrors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!tokenValid || timeRemaining <= 0) {
      setErrors({ general: 'Le token a expiré, veuillez faire une nouvelle demande' })
      return
    }

    const newErrors = validateForm()
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    setIsLoading(true)
    setErrors({})

    try {
      // ✅ NOUVEAU : Utilise la nouvelle route avec confirmation
      await resetPasswordConfirm(token, formData.password, formData.confirmPassword)
      
      setMessage('🎉 Mot de passe réinitialisé avec succès!')
      
      // Redirection après 3 secondes
      setTimeout(() => {
        navigate('/login', { 
          state: { 
            message: 'Vous pouvez maintenant vous connecter avec votre nouveau mot de passe' 
          }
        })
      }, 3000)
      
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Erreur lors de la réinitialisation'
      setErrors({ general: errorMessage })
      
      // Si le token est invalide/expiré, proposer de refaire une demande
      if (errorMessage.includes('expiré') || errorMessage.includes('invalide')) {
        setTokenValid(false)
      }
    } finally {
      setIsLoading(false)
    }
  }

  // ✅ NOUVEAU : Formater le temps restant
  const formatTimeRemaining = (seconds) => {
    if (seconds <= 0) return 'Expiré'
    
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`
    }
    return `${remainingSeconds}s`
  }

  // ✅ NOUVEAU : Indicateur de force du mot de passe
  const getPasswordStrength = (password) => {
    if (!password) return { level: 0, text: '', color: '' }
    
    let score = 0
    
    if (password.length >= 8) score++
    if (/[a-z]/.test(password)) score++
    if (/[A-Z]/.test(password)) score++
    if (/\d/.test(password)) score++
    if (/[^a-zA-Z0-9]/.test(password)) score++
    
    const levels = [
      { level: 0, text: '', color: '' },
      { level: 1, text: 'Très faible', color: '#dc3545' },
      { level: 2, text: 'Faible', color: '#fd7e14' },
      { level: 3, text: 'Moyen', color: '#ffc107' },
      { level: 4, text: 'Fort', color: '#20c997' },
      { level: 5, text: 'Très fort', color: '#28a745' }
    ]
    
    return levels[score] || levels[0]
  }

  const passwordStrength = getPasswordStrength(formData.password)

  // Loading de vérification du token
  if (isVerifyingToken) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="logo-placeholder">
              <span>🔄</span>
            </div>
            <h2>Vérification en cours...</h2>
            <p>Validation de votre lien de réinitialisation</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo-placeholder">
            <span>{tokenValid ? '🔐' : '❌'}</span>
          </div>
          <h2>
            {tokenValid ? 'Nouveau mot de passe' : 'Lien invalide'}
          </h2>
          <p>
            {tokenValid 
              ? 'Choisissez un nouveau mot de passe sécurisé' 
              : 'Ce lien de réinitialisation n\'est pas valide'
            }
          </p>
        </div>

        {/* ✅ NOUVEAU : Informations du token */}
        {tokenValid && tokenInfo && (
          <div className="token-info" style={{
            padding: '15px',
            backgroundColor: timeRemaining > 60 ? '#d4edda' : '#fff3cd',
            border: `1px solid ${timeRemaining > 60 ? '#c3e6cb' : '#ffd700'}`,
            borderRadius: '8px',
            margin: '0 20px 20px',
            fontSize: '14px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>📧 {tokenInfo.email}</span>
              <span style={{ 
                fontWeight: 'bold',
                color: timeRemaining > 60 ? '#155724' : '#856404'
              }}>
                ⏰ {formatTimeRemaining(timeRemaining)}
              </span>
            </div>
          </div>
        )}

        {tokenValid ? (
          <form onSubmit={handleSubmit} className="auth-form">
            {errors.general && (
              <div className="error-message">
                {errors.general}
              </div>
            )}

            {message && (
              <div className="success-message">
                {message}
                <div style={{ fontSize: '14px', marginTop: '8px', opacity: 0.8 }}>
                  Redirection automatique vers la connexion...
                </div>
              </div>
            )}

            <div className="input-container">
              <Input
                type="password"
                name="password"
                placeholder="Nouveau mot de passe (min. 8 caractères)"
                value={formData.password}
                onChange={handleChange}
                error={errors.password}
                required
              />
              
              {/* ✅ NOUVEAU : Indicateur de force */}
              {formData.password && (
                <div className="password-strength" style={{
                  marginTop: '5px',
                  fontSize: '12px',
                  color: passwordStrength.color,
                  fontWeight: 'bold'
                }}>
                  Force: {passwordStrength.text}
                </div>
              )}
            </div>

            <Input
              type="password"
              name="confirmPassword"
              placeholder="Confirmer le nouveau mot de passe"
              value={formData.confirmPassword}
              onChange={handleChange}
              error={errors.confirmPassword}
              required
            />

            {/* ✅ NOUVEAU : Conseils de sécurité */}
            <div className="security-tips" style={{
              fontSize: '12px',
              color: '#6c757d',
              backgroundColor: '#f8f9fa',
              padding: '10px',
              borderRadius: '5px',
              margin: '10px 0'
            }}>
              💡 <strong>Conseils :</strong> Utilisez au moins 8 caractères avec majuscules, minuscules et chiffres
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              loading={isLoading}
              disabled={timeRemaining <= 0}
            >
              {isLoading ? 'Réinitialisation...' : 'Réinitialiser le mot de passe'}
            </Button>
          </form>
        ) : (
          <div className="auth-form">
            {errors.general && (
              <div className="error-message">
                {errors.general}
              </div>
            )}
            
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <p style={{ marginBottom: '20px', color: '#6c757d' }}>
                Le lien de réinitialisation est invalide ou a expiré.
              </p>
              
              <Link to="/forgot-password">
                <Button variant="primary" fullWidth>
                  Demander un nouveau lien
                </Button>
              </Link>
            </div>
          </div>
        )}

        <div className="auth-footer">
          <Link to="/login" className="back-link">
            ← Retour à la connexion
          </Link>
          
          {/* ✅ NOUVEAU : Lien vers forgot password si token invalide */}
          {!tokenValid && (
            <>
              <span style={{ margin: '0 10px', color: '#dee2e6' }}>|</span>
              <Link to="/forgot-password" className="back-link">
                Mot de passe oublié ?
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

export default ResetPassword