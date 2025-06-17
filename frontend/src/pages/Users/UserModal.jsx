import React, { useState, useEffect } from 'react'
import { useAuth } from '../../store/authContext'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import Swal from 'sweetalert2';
import './UserModal.css'

const UserModal = ({ user, onClose, onSave }) => {
  const { isSuperadmin } = useAuth()
  const [formData, setFormData] = useState({
    prenom: '',
    nom: '',
    email: '',
    telephone: '',
    role: 'user',
    client_id: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [clients, setClients] = useState([]);


  const isEdit = !!user

  useEffect(() => {
    if (isEdit && user) {
      setFormData({
        prenom: user.prenom || '',
        nom: user.nom || '',
        email: user.email || '',
        telephone: user.telephone || '',
        role: user.role || 'user',
        client_id: user.client_id || ''
      });
    }
  
    if (isSuperadmin()) {
      UserService.listerClients()
        .then(response => {
          const data = response.data;
          // Adapte ici selon la structure réelle de ta réponse
          setClients(Array.isArray(data) ? data : data.clients || []);
        })
        .catch(err => {
          console.error('Erreur chargement clients:', err);
          setClients([]);
        });
    }
  }, [user]);
  

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

    if (isSuperadmin() && !formData.client_id && formData.role !== 'superadmin') {
      newErrors.client_id = 'Client requis pour les rôles admin/user'
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
      if (isEdit) {
        await UserService.modifierUtilisateur(user.id, formData)
      } else {
        const response = await UserService.creerUtilisateur(formData)
        if (response.data.mot_de_passe_temporaire) {
          // Copier dans le presse-papier
          await navigator.clipboard.writeText(response.data.mot_de_passe_temporaire)
          // Ajouter un message de succès           
          Swal.fire({
            title: 'Utilisateur créé avec succès!',
            text: `Mot de passe temporaire: ${response.data.mot_de_passe_temporaire}\n\n(copié dans le presse-papier) Veuillez noter ce mot de passe.`,
            icon: 'success'
          })
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

            {isSuperadmin() && (
              <>
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

                {formData.role !== 'superadmin' && (
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
                                {client.nom}
                            </option>
                            ))}

                    </select>
                    {errors.client_id && (
                      <span className="input-error-message">{errors.client_id}</span>
                    )}
                  </div>
                )}
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
