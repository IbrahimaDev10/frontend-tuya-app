import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import SuperAdminLayout from '../../layouts/SuperAdminLayout'
import AdminLayout from '../../layouts/AdminLayout'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import UserModal from './UserModal'
import ClientModal from './ClientModal'
import PendingAdmins from './PendingAdmins'
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

  const [roleFilter, setRoleFilter] = useState('')
  const [clientFilter, setClientFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [statusClientFilter, setStatusClientFilter] = useState('')

  const Layout = isSuperadmin() ? SuperAdminLayout : AdminLayout

  useEffect(() => {
    loadData()
      // Réinitialise les filtres quand on change d'onglet
  setSearchTerm('')
  setRoleFilter('')
  setClientFilter('')
  setStatusFilter('')
  setStatusClientFilter('') 
  }, [selectedTab])

  const loadData = async () => {
    try {
      setLoading(true)
  
      if (selectedTab === 'users') {
        const [usersResponse, statsResponse, clientsResponse] = await Promise.all([
          UserService.listerUtilisateurs(),
          UserService.obtenirStatistiques(),
          isSuperadmin() ? UserService.listerClients() : Promise.resolve({ data: { data: [] } })
        ])
        setUsers(usersResponse.data.data)
        setStats(statsResponse.data.data)
        if (isSuperadmin()) {
          setClients(clientsResponse.data.data)
        }
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

  const handleDeactivateClient = (client) => {
    const action = client.actif ? 'désactiver' : 'réactiver'
    setConfirmAction({
      type: 'toggleClient',
      client,
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} le client`,
      message: `Êtes-vous sûr de vouloir ${action} ${client.nom_entreprise} ?`,
      confirmText: action.charAt(0).toUpperCase() + action.slice(1),
      onConfirm: () => toggleClientStatus(client)
    })
  }

  const toggleClientStatus = async (client) => {
  try {
    if (client.actif) {
      await UserService.desactiverClient(client.id)
    } else {
      await UserService.reactiverClient(client.id)
    }
    loadData()
    showToast(`Client ${client.actif ? 'désactivé' : 'réactivé'} avec succès`, 'success')
  } catch (error) {
    showToast(error.response?.data?.error || 'Erreur lors de l\'opération', 'error')
  }
  setConfirmAction(null)
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
      
      showToast(`Mot de passe généré pour ${userName}`, 'success')
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

  const getFilteredUsers = () => {
    return users.filter(user => {
      const matchRole = roleFilter ? user.role === roleFilter : true
      const matchClient = clientFilter
  ? String(user.client_id) === String(clientFilter)
  : true

  const matchStatus = statusFilter
  ? String(user.actif) === (statusFilter === 'actif' ? 'true' : 'false')
  : true


      return matchRole && matchClient && matchStatus
    })
  }
  const getFilteredClients = () => {
    return clients.filter(client => {
      const matchStatus =
        statusClientFilter === ''
          ? true
          : statusClientFilter === 'actif'
          ? client.actif === true
          : client.actif === false;
  
      return matchStatus;
    });
  };
  
  

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

                {selectedTab === 'users' && (
                <div className="filter-bar">
                    <select onChange={(e) => setRoleFilter(e.target.value)} value={roleFilter}>
                    <option value="">Tous les rôles</option>
                    <option value="superadmin">Superadmin</option>
                    <option value="admin">Admin</option>
                    <option value="user">Utilisateur</option>
                    </select>

                    {isSuperadmin() && (
                    <select onChange={(e) => setClientFilter(e.target.value)} value={clientFilter}>
                        <option value="">Tous les clients</option>
                        {clients.map(client => (
                        <option key={client.id} value={client.id}>{client.nom_entreprise}</option>
                        ))}
                    </select>
                    )}

                    <select onChange={(e) => setStatusFilter(e.target.value)} value={statusFilter}>
                    <option value="">Tous</option>
                    <option value="actif">Actifs</option>
                    <option value="inactif">Inactifs</option>
                    </select>
                </div>
                )}

                {selectedTab === 'clients' && (
                <div className="filter-bar">
                    <select onChange={(e) => setStatusClientFilter(e.target.value)} value={statusClientFilter}>
                    <option value="">Tous</option>
                    <option value="actif">Actifs</option>
                    <option value="inactif">Inactifs</option>
                    </select>
                </div>
                )}

            {selectedTab !== 'pending' && (
              <Button
                variant="primary"
                onClick={selectedTab === 'users' ? handleCreateUser : handleCreateClient}
              >
                + {selectedTab === 'users' ? 'Nouvel utilisateur' : 'Nouveau client'}
              </Button>
            )}
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
            <button
              className={`tab ${selectedTab === 'pending' ? 'active' : ''}`}
              onClick={() => setSelectedTab('pending')}
            >
              Admins en attente
            </button>
          </div>
        )}

        {/* Contenu des onglets */}
        {selectedTab === 'users' ? (
          <UsersTable
          users={getFilteredUsers()}
          onEdit={handleEditUser}
          onDelete={handleDeleteUser}
          onToggleStatus={handleDeactivateUser}
          onGeneratePassword={generatePassword}
          isSuperadmin={isSuperadmin()}
        />
        
        ) : selectedTab === 'clients' ? (
            <ClientsTable
                clients={getFilteredClients()}
                onEdit={handleEditClient}
                onDelete={() => {}}
                isSuperadmin={isSuperadmin()}
                onToggleStatus={handleDeactivateClient}
                />
        ) : selectedTab === 'pending' ? (
          <PendingAdmins />
        ) : null}

        {/* Modals */}
        {showUserModal && (
                <UserModal
                    user={selectedUser}
                    onClose={() => setShowUserModal(false)}
                    onSave={handleUserSaved}
                    clients={clients} // ✅ envoie les clients ici
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
              <td>{user.client_nom || 'N/A'}</td>

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
const ClientsTable = ({ clients, onEdit, onDelete, isSuperadmin, onToggleStatus }) => (

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
                <Button
                    variant="secondary"
                    size="small"
                    onClick={() => onToggleStatus(client)}
                    >
                    {client.actif ? '❌' : '✅'}
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