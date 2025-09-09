import React, { useState } from 'react'
import Button from './Button'
import Input from './Input'
import exportService from '../services/exportService'
import './ExportModal.css'

const ExportModal = ({ isOpen, onClose, clientId, clientName = '' }) => {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Initialiser les dates par défaut (derniers 30 jours)
  React.useEffect(() => {
    if (isOpen) {
      const today = new Date()
      const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000))
      
      setEndDate(today.toISOString().split('T')[0])
      setStartDate(thirtyDaysAgo.toISOString().split('T')[0])
      setError('')
    }
  }, [isOpen])

  const handleExport = async () => {
    if (!startDate || !endDate) {
      setError('Veuillez sélectionner les dates de début et de fin')
      return
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('La date de début doit être antérieure à la date de fin')
      return
    }

    try {
      setLoading(true)
      setError('')

      await exportService.exportAndDownloadExcel(clientId, startDate, endDate, clientName)
      
      // Fermer le modal après succès
      onClose()
      
    } catch (error) {
      console.error('Erreur lors de l\'export:', error)
      setError(error.message || 'Erreur lors de la génération du rapport')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="export-modal-overlay" onClick={handleClose}>
      <div className="export-modal" onClick={(e) => e.stopPropagation()}>
        <div className="export-modal-header">
          <h3>📊 Export Excel Détaillé</h3>
          <button 
            className="export-modal-close" 
            onClick={handleClose}
            disabled={loading}
          >
            ×
          </button>
        </div>

        <div className="export-modal-content">
          <div className="export-info">
            <p>
              <strong>Client:</strong> {clientName || clientId}
            </p>
            <p>
              <strong>Description:</strong> Ce rapport contiendra toutes les mesures 
              électriques (monophasées et triphasées) pour la période sélectionnée.
            </p>
          </div>

          <div className="export-form">
            <div className="form-group">
              <label htmlFor="startDate">Date de début *</label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={loading}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="endDate">Date de fin *</label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                disabled={loading}
                required
              />
            </div>
          </div>

          {error && (
            <div className="export-error">
              <span className="error-icon">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <div className="export-features">
            <h4>📋 Contenu du rapport:</h4>
            <ul>
              <li>✅ Horodatage de chaque mesure</li>
              <li>✅ Informations de l'appareil (ID, nom)</li>
              <li>✅ Type de système (monophasé/triphasé)</li>
              <li>✅ Données monophasées: tension, courant, puissance, énergie</li>
              <li>✅ Données triphasées: tensions L1/L2/L3, courants L1/L2/L3</li>
              <li>✅ Puissance totale et facteur de puissance</li>
              <li>✅ Données environnementales (température, humidité)</li>
              <li>✅ État de l'appareil</li>
            </ul>
          </div>
        </div>

        <div className="export-modal-footer">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={loading}
          >
            Annuler
          </Button>
          <Button
            variant="primary"
            onClick={handleExport}
            loading={loading}
            disabled={!startDate || !endDate}
          >
            {loading ? 'Génération...' : '📊 Exporter Excel'}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ExportModal 