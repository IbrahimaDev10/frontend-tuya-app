import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Toast from '../../components/Toast'
import ConfirmModal from '../../components/ConfirmModal'
import './UserManagement.css'
import './PendingAdmins.css' // ✅ Utilise le même CSS que PendingAdmins

const PendingUsers = ({ users, onDelete, onResendActivation, isSuperadmin }) => {
  const [toast, setToast] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [actionLoading, setActionLoading] = useState({})

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const handleResendActivation = async (userId, userName) => {
    setConfirmAction({
      title: 'Renvoyer l\'email d\'activation',
      message: `Êtes-vous sûr de vouloir renvoyer l'email d'activation à ${userName} ?`,
      onConfirm: () => resendActivationEmail(userId, userName),
      confirmText: 'Renvoyer',
      confirmVariant: 'primary'
    })
  }

  const resendActivationEmail = async (userId, userName) => {
    try {
      setActionLoading(prev => ({ ...prev, [userId]: true }))
      
      await UserService.creerActivationUtilisateur(userId)
      
      showToast('Email d\'activation renvoyé avec succès', 'success')
      
      // Callback vers le parent pour recharger
      if (onResendActivation) {
        onResendActivation(userId, userName)
      }
      
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors de l\'envoi de l\'email',
        'error'
      )
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }))
      setConfirmAction(null)
    }
  }

  const handleDelete = (user) => {
    setConfirmAction({
      title: 'Supprimer l\'utilisateur en attente',
      message: `Êtes-vous sûr de vouloir supprimer ${user.nom_complet} qui est en attente d'activation ?`,
      onConfirm: () => deleteUser(user),
      confirmText: 'Supprimer',
      confirmVariant: 'danger'
    })
  }

  const deleteUser = async (user) => {
    try {
      setActionLoading(prev => ({ ...prev, [user.id]: true }))
      
      await UserService.supprimerUtilisateurEnAttente(user.id)
      
      showToast('Utilisateur supprimé avec succès', 'success')
      
      // Callback vers le parent pour recharger
      if (onDelete) {
        onDelete(user)
      }
      
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors de la suppression',
        'error'
      )
    } finally {
      setActionLoading(prev => ({ ...prev, [user.id]: false }))
      setConfirmAction(null)
    }
  }

  const handleSendNewPassword = async (userId, userName) => {
    setConfirmAction({
      title: 'Envoyer un nouveau mot de passe',
      message: `Êtes-vous sûr de vouloir générer et envoyer un nouveau mot de passe à ${userName} ?`,
      onConfirm: () => sendNewPassword(userId, userName),
      confirmText: 'Envoyer',
      confirmVariant: 'warning'
    })
  }

  const sendNewPassword = async (userId, userName) => {
    try {
      setActionLoading(prev => ({ ...prev, [userId]: true }))
      
      await UserService.envoyerNouveauMotDePasse(userId)
      
      showToast('Nouveau mot de passe envoyé par email', 'success')
      
    } catch (error) {
      showToast(
        error.response?.data?.error || 'Erreur lors de l\'envoi du mot de passe',
        'error'
      )
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }))
      setConfirmAction(null)
    }
  }

  const getStatusBadge = (user) => {
    if (!user.has_activation_token) {
      return <span className="status-badge status-error">Aucun token</span>
    }
    
    return (
      <span className="status-badge status-warning">
        En attente
        {user.nb_tokens_actifs > 1 && (
          <span> ({user.nb_tokens_actifs} tokens)</span>
        )}
      </span>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Inconnue'
    return new Date(dateString).toLocaleDateString('fr-FR')
  }

  const getDisplayRole = (role) => {
    const roles = {
      'admin': 'Administrateur',
      'user': 'Utilisateur',
      'superadmin': 'Super Administrateur'
    }
    return roles[role] || role
  }

  if (users.length === 0) {
    return (
      <div className="pending-admins-container">
        <div className="page-header">
          <div>
            <h2>Utilisateurs en attente d'activation</h2>
            <p>
              {isSuperadmin 
                ? 'Gérez les utilisateurs de tous les clients qui n\'ont pas encore été activés.'
                : 'Gérez vos utilisateurs qui n\'ont pas encore été activés.'
              }
            </p>
          </div>
        </div>

        <div className="empty-state">
          <h3>Aucun utilisateur en attente</h3>
          <p>
            {isSuperadmin 
              ? 'Tous les utilisateurs de tous les clients ont activé leur compte.'
              : 'Tous vos utilisateurs ont activé leur compte.'
            }
          </p>
        </div>

        {toast && <Toast message={toast.message} type={toast.type} />}
      </div>
    )
  }

  return (
    <div className="pending-admins-container">
      <div className="page-header">
        <div>
          <h2>Utilisateurs en attente d'activation</h2>
          <p>
            {isSuperadmin 
              ? 'Gérez les utilisateurs de tous les clients qui n\'ont pas encore été activés.'
              : 'Gérez vos utilisateurs qui n\'ont pas encore été activés.'
            }
          </p>
        </div>
      </div>

      <div className="pending-admins-list">
        {users.map((user) => (
          <div key={user.id} className="pending-admin-card">
            <div className="admin-info">
              <div className="admin-details">
                <h4>{user.nom_complet}</h4>
                <p className="admin-email">{user.email}</p>
                <p className="admin-client">
                  <strong>Rôle:</strong> {getDisplayRole(user.role)}
                </p>
                {isSuperadmin && user.entreprise && (
                  <p className="admin-client">
                    <strong>Client:</strong> {user.entreprise}
                  </p>
                )}
                <p className="admin-created">
                  <strong>Créé le:</strong> {formatDate(user.date_creation)}
                  {user.jours_depuis_creation !== undefined && (
                    <span style={{ marginLeft: '10px', fontSize: '12px', color: '#95a5a6' }}>
                      ({user.jours_depuis_creation === 0 ? 'Aujourd\'hui' : 
                        user.jours_depuis_creation === 1 ? 'Hier' :
                        `${user.jours_depuis_creation} jours`})
                    </span>
                  )}
                </p>
                {user.telephone && (
                  <p className="admin-created">
                    <strong>Téléphone:</strong> {user.telephone}
                  </p>
                )}
              </div>
              
              <div className="admin-status">
                {getStatusBadge(user)}
              </div>
            </div>

            <div className="admin-actions">
              <Button
                variant="primary"
                size="small"
                onClick={() => handleResendActivation(user.id, user.nom_complet)}
                loading={actionLoading[user.id]}
                disabled={actionLoading[user.id]}
              >
                📧 Renvoyer activation
              </Button>
              
              <Button
                variant="warning"
                size="small"
                onClick={() => handleSendNewPassword(user.id, user.nom_complet)}
                loading={actionLoading[user.id]}
                disabled={actionLoading[user.id]}
              >
                🔑 Nouveau mot de passe
              </Button>

              <Button
                variant="danger"
                size="small"
                onClick={() => handleDelete(user)}
                loading={actionLoading[user.id]}
                disabled={actionLoading[user.id]}
              >
                🗑️ Supprimer
              </Button>

              {/* Badge scope pour admin client */}
              {!isSuperadmin && user.dans_mon_scope === false && (
                <div style={{ 
                  marginTop: '8px', 
                  padding: '4px 8px', 
                  background: '#fff3cd', 
                  color: '#856404', 
                  borderRadius: '4px', 
                  fontSize: '11px',
                  textAlign: 'center'
                }}>
                  🚫 Hors périmètre
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      

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

export default PendingUsers