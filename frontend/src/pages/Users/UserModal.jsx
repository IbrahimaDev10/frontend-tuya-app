import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import UserService from '../../services/userService'
import SiteService from '../../services/siteService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import Swal from 'sweetalert2';
import './UserModal.css'

const UserModal = ({ user, onClose, onSave, clients = [] }) => {
  const { isSuperadmin, isAdmin, user: currentUser } = useAuth() // <-- AJOUTEZ currentUser pour son client_id
  const [formData, setFormData] = useState({
    prenom: '',
    nom: '',
    email: '',
    telephone: '',
    role: 'user',
    client_id: '', // Sera pré-rempli pour les admins
    site_id: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [sitesForClient, setSitesForClient] = useState([]) // État pour les sites du client sélectionné/courant

  const isEdit = !!user

  // Initialisation du formulaire
  useEffect(() => {
    if (isEdit && user) {
      // Mode édition: pré-remplir avec les données de l'utilisateur à modifier
      setFormData({
        prenom: user.prenom || '',
        nom: user.nom || '',
        email: user.email || '',
        telephone: user.telephone || '',
        role: user.role || 'user',
        client_id: user.client_id || '',
        site_id: user.site_id || ''
      })
    } else {
      // Mode création:
      // Si l'utilisateur connecté est un admin, pré-remplir client_id avec son propre client_id
      if (isAdmin() && currentUser?.client_id) {
        setFormData(prev => ({
          ...prev,
          client_id: currentUser.client_id,
          role: 'user' // Un admin ne peut créer que des utilisateurs simples
        }))
      }
    }
  }, [user, isEdit, isAdmin, currentUser])

  // Effet pour charger les sites quand client_id change
  useEffect(() => {
    const fetchSites = async () => {
      const clientIdToFetch = formData.client_id;

      if (clientIdToFetch) {
        try {
          // Si l'utilisateur connecté est un admin, il ne peut lister que les sites de son client
          // Si c'est un superadmin, il peut lister les sites de n'importe quel client_id
          const response = await SiteService.listerSites(clientIdToFetch);
          setSitesForClient(response.data.data || []);
        } catch (error) {
          console.error("Erreur lors du chargement des sites pour le client:", error);
          setSitesForClient([]);
        }
      } else {
        setSitesForClient([]);
      }
    };
    fetchSites();
  }, [formData.client_id]);
  
  // Réinitialiser site_id si le rôle ou le client change de manière incompatible
  useEffect(() => {
    // Si le rôle n'est pas 'user', le site_id doit être vide
    if (formData.role !== 'user' && formData.site_id) {
      setFormData(prev => ({ ...prev, site_id: '' }));
    }
    // Si le client_id change, et que le site_id actuel n'appartient pas au nouveau client, réinitialiser
    // Cette vérification est importante après le chargement des sitesForClient
    if (formData.site_id && sitesForClient.length > 0 && !sitesForClient.some(site => site.id === formData.site_id)) {
      setFormData(prev => ({ ...prev, site_id: '' }));
    }
  }, [formData.role, formData.client_id, sitesForClient]);


  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))

    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.prenom.trim()) {
      newErrors.prenom = 'Prénom requis'
    }

    if (!formData.nom.trim()) {
      newErrors.nom = 'Nom requis'
    }

    if (!formData.email.trim()) {
      newErrors.email = 'Email requis'
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Format email invalide'
    }

    // Validation du client_id
    // Si l'utilisateur connecté est Superadmin
    if (isSuperadmin()) {
      if (formData.role !== 'superadmin' && !formData.client_id) {
        newErrors.client_id = 'Client requis pour les rôles admin/utilisateur'
      }
    } 
    // Si l'utilisateur connecté est Admin (client_id est pré-rempli, mais on peut vérifier qu'il n'est pas vide)
    else if (isAdmin()) {
      if (!formData.client_id) { // Devrait toujours être pré-rempli par currentUser.client_id
        newErrors.client_id = 'Client requis'
      }
    }

    // Validation pour site_id
    if (formData.role === 'user' && !formData.site_id) {
      newErrors.site_id = 'Site requis pour les utilisateurs simples'
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
      // Préparer les données à envoyer
      const dataToSend = { ...formData };
      // Si l'utilisateur connecté est admin, le rôle est forcé à 'user'
      if (isAdmin()) {
        dataToSend.role = 'user';
      }

      if (isEdit) {
        await UserService.modifierUtilisateur(user.id, dataToSend)
      } else {
        const response = await UserService.creerUtilisateur(dataToSend)
        if (response.data.mot_de_passe_temporaire) {
          await navigator.clipboard.writeText(response.data.mot_de_passe_temporaire)
          
        } else if (response.data.lien_activation) {
          
        } else {
          
        }
      }

      onSave()
    } catch (error) {
      setErrors({
        general: error.response?.data?.error || 'Erreur lors de la sauvegarde'
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? 'Modifier l\'utilisateur' : 'Nouvel utilisateur'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            <Input
              type="text"
              name="prenom"
              label="Prénom"
              value={formData.prenom}
              onChange={handleChange}
              error={errors.prenom}
              required
            />

            <Input
              type="text"
              name="nom"
              label="Nom"
              value={formData.nom}
              onChange={handleChange}
              error={errors.nom}
              required
            />

            <Input
              type="email"
              name="email"
              label="Email"
              value={formData.email}
              onChange={handleChange}
              error={errors.email}
              required
            />

            <Input
              type="tel"
              name="telephone"
              label="Téléphone"
              value={formData.telephone}
              onChange={handleChange}
              error={errors.telephone}
            />

            {/* Champ Rôle : Visible uniquement pour les Superadmins */}
            {isSuperadmin() && (
              <div className="form-group">
                <label className="input-label">Rôle</label>
                <select
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="input"
                >
                  <option value="user">Utilisateur</option>
                  <option value="admin">Administrateur</option>
                  <option value="superadmin">Super Admin</option>
                </select>
              </div>
            )}

            {/* Champ Client :
                - Visible pour les Superadmins (sauf si rôle = superadmin)
                - Masqué pour les Admins (client_id est pré-rempli et non modifiable)
            */}
            {isSuperadmin() && formData.role !== 'superadmin' && (
              <div className="form-group">
                <label className="input-label">
                  Client
                  <span className="required">*</span>
                </label>
                <select
                  name="client_id"
                  value={formData.client_id}
                  onChange={handleChange}
                  className={`input ${errors.client_id ? 'input-error' : ''}`}
                >
                  <option value="">Sélectionner un client</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>
                        {client.nom_entreprise || client.nom}
                    </option>
                    ))}
                </select>
                {errors.client_id && (
                  <span className="input-error-message">{errors.client_id}</span>
                )}
              </div>
            )}   
            {/* Champ Site :
                - Visible si le rôle est 'user'
                - Visible pour les Superadmins (si client_id sélectionné)
                - Visible pour les Admins (si client_id pré-rempli)
            */}
            {formData.role === 'user' && formData.client_id && (
              <div className="form-group">
                <label className="input-label">
                  Site
                  <span className="required">*</span>
                </label>
                <select
                  name="site_id"
                  value={formData.site_id}
                  onChange={handleChange}
                  className={`input ${errors.site_id ? 'input-error' : ''}`}
                >
                  <option value="">Sélectionner un site</option>
                  {sitesForClient.map(site => (
                    <option key={site.id} value={site.id}>
                      {site.nom_site}
                    </option>
                  ))}
                </select>
                {errors.site_id && (
                  <span className="input-error-message">{errors.site_id}</span>
                )}
              </div>
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
              type="submit"
              variant="primary"
              loading={loading}
            >
              {isEdit ? 'Modifier' : 'Créer'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default UserModal
