import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import ActivationService from '../../services/activationService'
import Button from '../../components/Button'
import Toast from '../../components/Toast'
import ConfirmModal from '../../components/ConfirmModal'
import './UserManagement.css'
import './PendingAdmins.css'

const PendingAdmins = () => {
  const { isSuperadmin } = useAuth()
  const [pendingAdmins, setPendingAdmins] = useState([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [actionLoading, setActionLoading] = useState({})

  useEffect(() => {
    if (isSuperadmin()) {
      loadPendingAdmins()
    }
  }, [])

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const loadPendingAdmins = async () => {
    try {
      setLoading(true)
      const response = await ActivationService.listerAdminsEnAttente()
      setPendingAdmins(response.data.data)
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors du chargement des administrateurs en attente',
        'error'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleResendActivation = async (adminId, adminName) => {
    setConfirmAction({
      title: 'Renvoyer l\'email d\'activation',
      message: `Êtes-vous sûr de vouloir renvoyer l'email d'activation à ${adminName} ?`,
      onConfirm: () => resendActivationEmail(adminId),
      confirmText: 'Renvoyer',
      confirmVariant: 'primary'
    })
  }

  const resendActivationEmail = async (adminId) => {
    try {
      setActionLoading(prev => ({ ...prev, [adminId]: true }))
      
      await ActivationService.regenererTokenActivation(adminId)
      
      showToast('Email d\'activation renvoyé avec succès', 'success')
      
      // Recharger la liste pour mettre à jour les informations
      await loadPendingAdmins()
      
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors de l\'envoi de l\'email',
        'error'
      )
    } finally {
      setActionLoading(prev => ({ ...prev, [adminId]: false }))
      setConfirmAction(null)
    }
  }

  const handleSendNewPassword = async (adminId, adminName) => {
    setConfirmAction({
      title: 'Envoyer un nouveau mot de passe',
      message: `Êtes-vous sûr de vouloir générer et envoyer un nouveau mot de passe à ${adminName} ?`,
      onConfirm: () => sendNewPassword(adminId),
      confirmText: 'Envoyer',
      confirmVariant: 'warning'
    })
  }

  const sendNewPassword = async (adminId) => {
    try {
      setActionLoading(prev => ({ ...prev, [adminId]: true }))
      
      await ActivationService.envoyerNouveauMotDePasse(adminId)
      
      showToast('Nouveau mot de passe envoyé par email', 'success')
      
      // Recharger la liste
      await loadPendingAdmins()
      
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors de l\'envoi du mot de passe',
        'error'
      )
    } finally {
      setActionLoading(prev => ({ ...prev, [adminId]: false }))
      setConfirmAction(null)
    }
  }

  const formatTimeRemaining = (seconds) => {
    if (seconds <= 0) return 'Expiré'
    
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m restantes`
    }
    return `${minutes}m restantes`
  }

  const getStatusBadge = (admin) => {
    if (!admin.token_info) {
      return <span className="status-badge status-error">Aucun token</span>
    }
    
    if (admin.token_info.temps_restant_secondes <= 0) {
      return <span className="status-badge status-error">Token expiré</span>
    }
    
    return (
      <span className="status-badge status-warning">
        En attente ({formatTimeRemaining(admin.token_info.temps_restant_secondes)})
      </span>
    )
  }

  if (!isSuperadmin()) {
    return (
      <div className="access-denied">
        <h3>Accès refusé</h3>
        <p>Seuls les superadministrateurs peuvent accéder à cette page.</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Chargement des administrateurs en attente...</p>
      </div>
    )
  }

  return (
    <div className="pending-admins-container">
      <div className="page-header">
        <h2>Administrateurs en attente d'activation</h2>
        <p>Gérez les comptes administrateurs qui n'ont pas encore été activés.</p>
        <Button
          variant="secondary"
          onClick={loadPendingAdmins}
          loading={loading}
        >
          🔄 Actualiser
        </Button>
      </div>

      {pendingAdmins.length === 0 ? (
        <div className="empty-state">
          <h3>Aucun administrateur en attente</h3>
          <p>Tous les administrateurs ont activé leur compte.</p>
        </div>
      ) : (
        <div className="pending-admins-list">
          {pendingAdmins.map((admin) => (
            <div key={admin.id} className="pending-admin-card">
              <div className="admin-info">
                <div className="admin-details">
                  <h4>{admin.prenom} {admin.nom}</h4>
                  <p className="admin-email">{admin.email}</p>
                  <p className="admin-client">
                    <strong>Client:</strong> {admin.client_name}
                  </p>
                  <p className="admin-created">
                    <strong>Créé le:</strong> {new Date(admin.date_creation).toLocaleDateString('fr-FR')}
                  </p>
                </div>
                
                <div className="admin-status">
                  {getStatusBadge(admin)}
                </div>
              </div>

              <div className="admin-actions">
                <Button
                  variant="primary"
                  size="small"
                  onClick={() => handleResendActivation(admin.id, `${admin.prenom} ${admin.nom}`)}
                  loading={actionLoading[admin.id]}
                  disabled={actionLoading[admin.id]}
                >
                  📧 Renvoyer activation
                </Button>
                
                <Button
                  variant="warning"
                  size="small"
                  onClick={() => handleSendNewPassword(admin.id, `${admin.prenom} ${admin.nom}`)}
                  loading={actionLoading[admin.id]}
                  disabled={actionLoading[admin.id]}
                >
                  🔑 Nouveau mot de passe
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {confirmAction && (
        <ConfirmModal
          title={confirmAction.title}
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
          confirmText={confirmAction.confirmText}
          confirmVariant={confirmAction.confirmVariant}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}

export default PendingAdmins