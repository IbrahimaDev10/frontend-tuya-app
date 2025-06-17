import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import UserModal from './UserModal'
import ClientModal from './ClientModal'
import ConfirmModal from '../../components/ConfirmModal'
import Toast from '../../components/Toast'
import './UserManagement.css'

const UserManagement = () => {
  const { isSuperadmin, isAdmin } = useAuth()
  const [users, setUsers] = useState([])
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedTab, setSelectedTab] = useState('users')
  const [showUserModal, setShowUserModal] = useState(false)
  const [showClientModal, setShowClientModal] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [selectedClient, setSelectedClient] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [stats, setStats] = useState({})
  const [toast, setToast] = useState(null)

  const Layout = isSuperadmin() ? SuperAdminLayout : AdminLayout

  useEffect(() => {
    loadData()
  }, [selectedTab])

  const loadData = async () => {
    try {
      setLoading(true)
      
      if (selectedTab === 'users') {
        const [usersResponse, statsResponse] = await Promise.all([
          UserService.listerUtilisateurs(),
          UserService.obtenirStatistiques()
        ])
        setUsers(usersResponse.data.data)
        setStats(statsResponse.data.data)
      } else if (selectedTab === 'clients' && isSuperadmin()) {
        const clientsResponse = await UserService.listerClients()
        setClients(clientsResponse.data.data)
      }
    } catch (error) {
      showToast('Erreur lors du chargement des données', 'error')
    } finally {
      setLoading(false)
    }
  }

  const showToast = (message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const handleSearch = async (term) => {
    if (term.length < 2) {
      loadData()
      return
    }

    try {
      const response = await UserService.rechercherUtilisateurs(term)
      setUsers(response.data.data)
    } catch (error) {
      showToast('Erreur lors de la recherche', 'error')
    }
  }

  const handleCreateUser = () => {
    setSelectedUser(null)
    setShowUserModal(true)
  }

  const handleEditUser = (user) => {
    setSelectedUser(user)
    setShowUserModal(true)
  }

  const handleCreateClient = () => {
    setSelectedClient(null)
    setShowClientModal(true)
  }

  const handleEditClient = (client) => {
    setSelectedClient(client)
    setShowClientModal(true)
  }

  const handleUserSaved = () => {
    setShowUserModal(false)
    loadData()
    showToast('Utilisateur sauvegardé avec succès', 'success')
  }

  const handleClientSaved = () => {
    setShowClientModal(false)
    loadData()
    showToast('Client sauvegardé avec succès', 'success')
  }

  const handleDeleteUser = (user) => {
    setConfirmAction({
      type: 'deleteUser',
      user,
      title: 'Supprimer l\'utilisateur',
      message: `Êtes-vous sûr de vouloir supprimer ${user.nom_complet} ?`,
      confirmText: 'Supprimer',
      onConfirm: () => confirmDeleteUser(user.id)
    })
  }

  const handleDeactivateUser = (user) => {
    const action = user.actif ? 'désactiver' : 'réactiver'
    setConfirmAction({
      type: 'toggleUser',
      user,
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} l'utilisateur`,
      message: `Êtes-vous sûr de vouloir ${action} ${user.nom_complet} ?`,
      confirmText: action.charAt(0).toUpperCase() + action.slice(1),
      onConfirm: () => toggleUserStatus(user)
    })
  }

  const confirmDeleteUser = async (userId) => {
    try {
      await UserService.supprimerUtilisateur(userId)
      loadData()
      showToast('Utilisateur supprimé avec succès', 'success')
    } catch (error) {
      showToast(error.response?.data?.error || 'Erreur lors de la suppression', 'error')
    }
    setConfirmAction(null)
  }

  const toggleUserStatus = async (user) => {
    try {
      if (user.actif) {
        await UserService.desactiverUtilisateur(user.id)
      } else {
        await UserService.reactiverUtilisateur(user.id)
      }
      loadData()
      showToast(`Utilisateur ${user.actif ? 'désactivé' : 'réactivé'} avec succès`, 'success')
    } catch (error) {
      showToast(error.response?.data?.error || 'Erreur lors de l\'opération', 'error')
    }
    setConfirmAction(null)
  }

  const generatePassword = async (userId, userName) => {
    try {
      const response = await UserService.genererMotDePasse(userId)
      const password = response.data.mot_de_passe_temporaire
      
      // Copier dans le presse-papier
      await navigator.clipboard.writeText(password)
      
      showToast(`Mot de passe généré pour ${userName}: ${password} (copié dans le presse-papier)`, 'success')
    } catch (error) {
      showToast('Erreur lors de la génération du mot de passe', 'error')
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Chargement...</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="user-management">
        <div className="user-management-header">
          <h1>Gestion des Utilisateurs</h1>
          <div className="header-actions">
            <Input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                handleSearch(e.target.value)
              }}
              className="search-input"
            />
            <Button
              variant="primary"
              onClick={selectedTab === 'users' ? handleCreateUser : handleCreateClient}
            >
              + {selectedTab === 'users' ? 'Nouvel utilisateur' : 'Nouveau client'}
            </Button>
          </div>
        </div>

        {/* Statistiques */}
        <div className="stats-grid">
          {isSuperadmin() ? (
            <>
              <div className="stat-card">
                <div className="stat-icon">👥</div>
                <div className="stat-content">
                  <h3>Total Utilisateurs</h3>
                  <div className="stat-number">{stats.total_utilisateurs || 0}</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">🏢</div>
                <div className="stat-content">
                  <h3>Total Clients</h3>
                  <div className="stat-number">{stats.total_clients || 0}</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">👑</div>
                <div className="stat-content">
                  <h3>Admins</h3>
                  <div className="stat-number">{stats.total_admins || 0}</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">❌</div>
                <div className="stat-content">
                  <h3>Inactifs</h3>
                  <div className="stat-number">{stats.utilisateurs_inactifs || 0}</div>
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="stat-card">
                <div className="stat-icon">👥</div>
                <div className="stat-content">
                  <h3>Utilisateurs</h3>
                  <div className="stat-number">{stats.utilisateurs_client || 0}</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">✅</div>
                <div className="stat-content">
                  <h3>Actifs</h3>
                  <div className="stat-number">{stats.users_client || 0}</div>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">❌</div>
                <div className="stat-content">
                  <h3>Inactifs</h3>
                  <div className="stat-number">{stats.utilisateurs_inactifs_client || 0}</div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Onglets */}
        {isSuperadmin() && (
          <div className="tabs">
            <button
              className={`tab ${selectedTab === 'users' ? 'active' : ''}`}
              onClick={() => setSelectedTab('users')}
            >
              Utilisateurs
            </button>
            <button
              className={`tab ${selectedTab === 'clients' ? 'active' : ''}`}
              onClick={() => setSelectedTab('clients')}
            >
              Clients
            </button>
          </div>
        )}

        {/* Contenu des onglets */}
        {selectedTab === 'users' ? (
          <UsersTable
            users={users}
            onEdit={handleEditUser}
            onDelete={handleDeleteUser}
            onToggleStatus={handleDeactivateUser}
            onGeneratePassword={generatePassword}
            isSuperadmin={isSuperadmin()}
          />
        ) : (
          <ClientsTable
            clients={clients}
            onEdit={handleEditClient}
            onDelete={() => {}}
            isSuperadmin={isSuperadmin()}
          />
        )}

        {/* Modals */}
        {showUserModal && (
          <UserModal
            user={selectedUser}
            onClose={() => setShowUserModal(false)}
            onSave={handleUserSaved}
          />
        )}

        {showClientModal && (
          <ClientModal
            client={selectedClient}
            onClose={() => setShowClientModal(false)}
            onSave={handleClientSaved}
          />
        )}

        {confirmAction && (
          <ConfirmModal
            title={confirmAction.title}
            message={confirmAction.message}
            confirmText={confirmAction.confirmText}
            onConfirm={confirmAction.onConfirm}
            onCancel={() => setConfirmAction(null)}
          />
        )}

        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </div>
    </Layout>
  )
}

// Composant tableau des utilisateurs
const UsersTable = ({ users, onEdit, onDelete, onToggleStatus, onGeneratePassword, isSuperadmin }) => (
  <div className="table-container">
    <table className="data-table">
      <thead>
        <tr>
          <th>Nom</th>
          <th>Email</th>
          <th>Rôle</th>
          {isSuperadmin && <th>Client</th>}
          <th>Statut</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map(user => (
          <tr key={user.id}>
            <td>{user.nom_complet}</td>
            <td>{user.email}</td>
            <td>
              <span className={`role-badge role-${user.role}`}>
                {user.role}
              </span>
            </td>
            {isSuperadmin && (
              <td>{user.client?.nom_entreprise || 'N/A'}</td>
            )}
            <td>
              <span className={`status-badge ${user.actif ? 'active' : 'inactive'}`}>
                {user.actif ? 'Actif' : 'Inactif'}
              </span>
            </td>
            <td>
              <div className="action-buttons">
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onEdit(user)}
                >
                  ✏️
                </Button>
                <Button
                  variant="secondary"
                  size="small"
                  onClick={() => onToggleStatus(user)}
                >
                  {user.actif ? '❌' : '✅'}
                </Button>
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onGeneratePassword(user.id, user.nom_complet)}
                  title="Générer mot de passe"
                >
                  🔑
                </Button>
                <Button
                  variant="secondary"
                  size="small"
                  onClick={() => onDelete(user)}
                >
                  🗑️
                </Button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

// Composant tableau des clients
const ClientsTable = ({ clients, onEdit, onDelete, isSuperadmin }) => (
  <div className="table-container">
    <table className="data-table">
      <thead>
        <tr>
          <th>Entreprise</th>
          <th>Contact</th>
          <th>Téléphone</th>
          <th>Statut</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {clients.map(client => (
          <tr key={client.id}>
            <td>{client.nom_entreprise}</td>
            <td>{client.email_contact}</td>
            <td>{client.telephone || 'N/A'}</td>
            <td>
              <span className={`status-badge ${client.actif ? 'active' : 'inactive'}`}>
                {client.actif ? 'Actif' : 'Inactif'}
              </span>
            </td>
            <td>
              <div className="action-buttons">
                <Button
                  variant="outline"
                  size="small"
                  onClick={() => onEdit(client)}
                >
                  ✏️
                </Button>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)

export default UserManagement