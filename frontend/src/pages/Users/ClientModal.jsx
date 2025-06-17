import React, { useState, useEffect } from 'react'
import UserService from '../../services/userService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import Swal from 'sweetalert2';
import './UserModal.css'

const ClientModal = ({ client, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    nom_entreprise: '',
    email_contact: '',
    telephone: '',
    adresse: '',
    // Données pour l'admin automatique
    prenom_admin: 'Admin',
    nom_admin: '',
    email_admin: '',
    telephone_admin: ''
  })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [useContactEmailForAdmin, setUseContactEmailForAdmin] = useState(true)

  const isEdit = !!client

  useEffect(() => {
    if (isEdit) {
      setFormData({
        nom_entreprise: client.nom_entreprise || '',
        email_contact: client.email_contact || '',
        telephone: client.telephone || '',
        adresse: client.adresse || ''
      })
    }
  }, [client])

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => {
      const newData = {
        ...prev,
        [name]: value
      }

      // Auto-remplissage pour le nom de l'admin
      if (name === 'nom_entreprise') {
        newData.nom_admin = value
      }
      // Auto-remplissage pour l'email admin si option cochée
      if (name === 'email_contact' && useContactEmailForAdmin) {
        newData.email_admin = value
      }

      // Auto-remplissage pour le téléphone admin
      if (name === 'telephone') {
        newData.telephone_admin = value
      }

      return newData
    })

    // Effacer l'erreur du champ modifié
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const handleUseContactEmailChange = (e) => {
    setUseContactEmailForAdmin(e.target.checked)
    if (e.target.checked) {
      setFormData(prev => ({
        ...prev,
        email_admin: prev.email_contact
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}

    if (!formData.nom_entreprise.trim()) {
      newErrors.nom_entreprise = 'Nom d\'entreprise requis'
    }

    if (!formData.email_contact.trim()) {
      newErrors.email_contact = 'Email de contact requis'
    } else if (!/\S+@\S+\.\S+/.test(formData.email_contact)) {
      newErrors.email_contact = 'Format email invalide'
    }

    // Validations pour le nouvel admin (seulement en création)
    if (!isEdit) {
      if (!formData.prenom_admin.trim()) {
        newErrors.prenom_admin = 'Prénom de l\'admin requis'
      }

      if (!formData.nom_admin.trim()) {
        newErrors.nom_admin = 'Nom de l\'admin requis'
      }

      if (!formData.email_admin.trim()) {
        newErrors.email_admin = 'Email de l\'admin requis'
      } else if (!/\S+@\S+\.\S+/.test(formData.email_admin)) {
        newErrors.email_admin = 'Format email admin invalide'
      }
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
        await UserService.modifierClient(client.id, formData)
      } else {
        const response = await UserService.creerClient(formData)
        // Afficher les informations de connexion de l'admin
        if (response.data.data.identifiants_admin) {
          const { email, mot_de_passe } = response.data.data.identifiants_admin
                // Copier dans le presse-papier
                await navigator.clipboard.writeText(mot_de_passe)
          // Ajouter un message de succès           
          Swal.fire({
            title: 'Admin créé avec succès !',
            html: `
              <p><strong>Mot de passe :</strong> ${mot_de_passe}</p>
              <p>(Copié dans le presse-papier)</p>
            `,
            icon: 'success'
          });
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
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{isEdit ? 'Modifier le client' : 'Nouveau client'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.general && (
              <div className="error-message">{errors.general}</div>
            )}

            {/* Informations du client */}
            <div className="form-section">
              <h4>Informations du client</h4>
              
              <Input
                type="text"
                name="nom_entreprise"
                label="Nom de l'entreprise"
                value={formData.nom_entreprise}
                onChange={handleChange}
                error={errors.nom_entreprise}
                required
              />

              <Input
                type="email"
                name="email_contact"
                label="Email de contact"
                value={formData.email_contact}
                onChange={handleChange}
                error={errors.email_contact}
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

              <div className="form-group">
                <label className="input-label">Adresse</label>
                <textarea
                  name="adresse"
                  value={formData.adresse}
                  onChange={handleChange}
                  className="input textarea"
                  rows="3"
                  placeholder="Adresse complète..."
                />
              </div>
            </div>

            {/* Informations de l'admin (seulement en création) */}
            {!isEdit && (
              <div className="form-section">
                <h4>Administrateur du client</h4>
                <p className="section-description">
                  Un compte administrateur sera créé automatiquement pour ce client.
                </p>

                <div className="form-grid">
                  <Input
                    type="text"
                    name="prenom_admin"
                    label="Prénom de l'admin"
                    value={formData.prenom_admin}
                    onChange={handleChange}
                    error={errors.prenom_admin}
                    required
                  />

                  <Input
                    type="text"
                    name="nom_admin"
                    label="Nom de l'admin"
                    value={formData.nom_admin}
                    onChange={handleChange}
                    error={errors.nom_admin}
                    required
                  />
                </div>

                <div className="checkbox-group">
                  <input
                    type="checkbox"
                    id="useContactEmail"
                    checked={useContactEmailForAdmin}
                    onChange={handleUseContactEmailChange}
                  />
                  <label htmlFor="useContactEmail">
                    Utiliser l'email de contact pour l'admin
                  </label>
                </div>

                <Input
                  type="email"
                  name="email_admin"
                  label="Email de l'admin"
                  value={formData.email_admin}
                  onChange={handleChange}
                  error={errors.email_admin}
                  disabled={useContactEmailForAdmin}
                  required
                />

                <Input
                  type="tel"
                  name="telephone_admin"
                  label="Téléphone de l'admin"
                  value={formData.telephone_admin}
                  onChange={handleChange}
                  error={errors.telephone_admin}
                />

                <div className="info-box">
                  <strong>Note:</strong> Un mot de passe temporaire sera généré automatiquement pour l'administrateur. 
                  Il devra le changer lors de sa première connexion.
                </div>
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
              {isEdit ? 'Modifier' : 'Créer le client'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ClientModal