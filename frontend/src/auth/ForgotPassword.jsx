import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../services/authService'
import Button from '../components/Button'
import Input from '../components/Input'
import './Auth.css'

const ForgotPassword = () => {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!email) {
      setError('Email requis')
      return
    }

    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Format email invalide')
      return
    }

    setIsLoading(true)
    setError('')
    setMessage('')

    try {
      await forgotPassword(email)
      setMessage('Un email de réinitialisation a été envoyé à votre adresse.')
    } catch (error) {
      setError(error.response?.data?.message || 'Erreur lors de l\'envoi')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="logo-placeholder">
            <span>LOGO</span>
          </div>
          <h2>Mot de passe oublié</h2>
          <p>Entrez votre email pour recevoir un lien de réinitialisation</p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          {message && (
            <div className="success-message">
              {message}
            </div>
          )}

          <Input
            type="email"
            name="email"
            placeholder="Adresse email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={error && !email ? 'Email requis' : ''}
            required
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            loading={isLoading}
          >
            Envoyer le lien
          </Button>
        </form>

        <div className="auth-footer">
          <Link to="/login" className="back-link">
            ← Retour à la connexion
          </Link>
        </div>
      </div>
    </div>
  )
}

export default ForgotPassword