// components/ExportModal.jsx - Version auto-détection du rôle

import React, { useState, useEffect } from 'react'
import Button from './Button'
import Input from './Input'
import exportService from '../services/exportService'
import deviceService from '../services/deviceService'
import userService from '../services/userService'
import { useAuth } from '../store/authContext' // récupérer l'utilisateur
import './ExportModal.css'

const ExportModal = ({ 
  isOpen, 
  onClose
}) => {
  const { user } = useAuth() // Récupération automatique de l'utilisateur

  // Détection automatique du rôle et du client
  const userRole = user?.role || 'user'
  const currentClientId = user?.client_id || null

  // États de base
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Pour SuperAdmin : liste et sélection de clients
  const [clients, setClients] = useState([])
  const [loadingClients, setLoadingClients] = useState(false)
  const [selectedClientId, setSelectedClientId] = useState(currentClientId || '')
  const [selectedClientName, setSelectedClientName] = useState('')

  // Chargement des appareils
  const [devices, setDevices] = useState([])
  const [loadingDevices, setLoadingDevices] = useState(false)
  const [selectedDeviceId, setSelectedDeviceId] = useState('all')
  
  // Formats et options
  const [selectedFormats, setSelectedFormats] = useState(['excel'])
  const [pdfOptions, setPdfOptions] = useState({
    includePower: true,
    includeVoltage: true,
    includeCurrent: true,
    includeSummary: true,
    chartStyle: 'line',
    pageOrientation: 'landscape',
    showGrid: true,
    showLegend: true
  })

  const [activeTab, setActiveTab] = useState('basic')

  // Initialisation à l'ouverture
  useEffect(() => {
    if (isOpen) {
      initializeDates()
      
      if (userRole === 'superadmin') {
        // SuperAdmin : charger la liste des clients
        loadClients()
      } else if (currentClientId) {
        // Admin ou User : charger directement les appareils
        setSelectedClientId(currentClientId)
        setSelectedClientName(user?.nom_complet || '')
        loadDevices(currentClientId)
      }
    }
  }, [isOpen, userRole, currentClientId])

  // Charger les clients (SuperAdmin uniquement)
  const loadClients = async () => {
  setLoadingClients(true)
  setError('')
  
  try {
    const response = await userService.listerClients()
    
    // ✅ Debugging pour voir la structure exacte
    console.log('Response complète:', response)
    console.log('Response.data:', response.data)
    
    // ✅ Extraire les clients selon différentes structures possibles
    let clientsList = []
    
    if (Array.isArray(response)) {
      clientsList = response
    } else if (response.data) {
      if (Array.isArray(response.data)) {
        clientsList = response.data
      } else if (response.data.data && Array.isArray(response.data.data)) {
        clientsList = response.data.data
      } else if (response.data.clients && Array.isArray(response.data.clients)) {
        clientsList = response.data.clients
      }
    }
    
    console.log('Liste clients extraite:', clientsList)
    
    setClients(clientsList)
    
    if (clientsList.length === 0) {
      setError('Aucun client disponible')
    }
  } catch (err) {
    console.error('Erreur chargement clients:', err)
    setError('Impossible de charger la liste des clients')
    setClients([])
  } finally {
    setLoadingClients(false)
  }
}

  // Quand le SuperAdmin sélectionne un client
  const handleClientChange = (clientId) => {
    setSelectedClientId(clientId)
    setDevices([])
    setSelectedDeviceId('all')
    setError('')
    
    // Trouver le nom du client
    const client = clients.find(c => c.id === clientId)
    setSelectedClientName(client ? client.nom_entreprise : '')
    
    if (clientId) {
      loadDevices(clientId)
    }
  }

  // Charger les appareils du client
  const loadDevices = async (clientId) => {
    if (!clientId) return
    
    setLoadingDevices(true)
    setError('')
    
    try {
      const clientDevices = await deviceService.listerAppareilsPourClient(clientId)
      setDevices(clientDevices)
      
      if (clientDevices.length === 0) {
        setError('Aucun appareil trouvé pour ce client')
      }
    } catch (err) {
      console.error('Erreur chargement appareils:', err)
      setError('Impossible de charger les appareils du client')
      setDevices([])
    } finally {
      setLoadingDevices(false)
    }
  }

  const initializeDates = () => {
    const today = new Date()
    const thirtyDaysAgo = new Date(today.getTime() - (30 * 24 * 60 * 60 * 1000))
    
    setEndDate(today.toISOString().split('T')[0])
    setStartDate(thirtyDaysAgo.toISOString().split('T')[0])
    setError('')
    setSuccess('')
    setSelectedDeviceId('all')
    setSelectedFormats(['excel'])
  }

  const toggleFormat = (format) => {
    setSelectedFormats(prev => 
      prev.includes(format) ? prev.filter(f => f !== format) : [...prev, format]
    )
  }

  const updatePdfOption = (key, value) => {
    setPdfOptions(prev => ({ ...prev, [key]: value }))
  }

  const applyPdfPreset = (presetName) => {
    const presets = exportService.getPDFPresets()
    if (presets[presetName]) {
      setPdfOptions(presets[presetName])
    }
  }

  const validate = () => {
    if (userRole === 'superadmin' && !selectedClientId) {
      setError('Veuillez sélectionner un client')
      return false
    }

    if (!startDate || !endDate) {
      setError('Veuillez sélectionner les dates de début et de fin')
      return false
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('La date de début doit être antérieure à la date de fin')
      return false
    }

    if (selectedFormats.length === 0) {
      setError('Veuillez sélectionner au moins un format d\'export')
      return false
    }

    return true
  }

  const handleExport = async () => {
    if (!validate()) return

    try {
      setLoading(true)
      setError('')
      setSuccess('')

      const options = {
        clientId: selectedClientId,
        startDate,
        endDate,
        ...(selectedDeviceId !== 'all' && { deviceId: selectedDeviceId }),
        ...pdfOptions
      }

      const selectedDevice = devices.find(d => d.id === selectedDeviceId)
      const deviceName = selectedDevice ? selectedDevice.nom_appareil : ''
      const clientName = selectedClientName || 'Client'

      if (selectedFormats.length === 1) {
        const format = selectedFormats[0]
        switch (format) {
          case 'csv':
            await exportService.exportAndDownloadCSV(options, clientName, deviceName)
            break
          case 'excel':
            await exportService.exportAndDownloadExcel(options, clientName, deviceName)
            break
          case 'pdf':
            await exportService.exportAndDownloadPDF(options, clientName, deviceName)
            break
          default:
            throw new Error(`Format non supporté: ${format}`)
        }
        setSuccess(`Export ${format.toUpperCase()} réussi !`)
      } else {
        const result = await exportService.exportMultiple(
          selectedFormats, 
          options, 
          clientName, 
          deviceName
        )
        
        if (result.success) {
          setSuccess(`${result.results.length} fichier(s) exporté(s)`)
        } else {
          setError(`${result.errors.length} erreur(s) lors de l'export`)
        }
      }

      setTimeout(() => onClose(), 2000)
      
    } catch (error) {
      console.error('Erreur export:', error)
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
      <div className="export-modal export-modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="export-modal-header">
          <h3>Exporter les données</h3>
          <button 
            className="export-modal-close" 
            onClick={handleClose}
            disabled={loading}
          >
            ×
          </button>
        </div>

        <div className="export-modal-content">
          {/* Info utilisateur */}
          <div className="export-info">
            <p>
              <strong>Client:</strong> {
                userRole === 'superadmin' 
                  ? (selectedClientName || 'Sélectionnez un client')
                  : (user?.nom_complet || 'N/A')
              }
            </p>
            {loadingClients && <p className="loading-text">Chargement des clients...</p>}
            {loadingDevices && <p className="loading-text">Chargement des appareils...</p>}
            {!loadingDevices && devices.length > 0 && (
              <p className="info-text">{devices.length} appareil(s) disponible(s)</p>
            )}
          </div>

          {/* Onglets */}
          <div className="export-tabs">
            <button 
              className={`export-tab ${activeTab === 'basic' ? 'active' : ''}`}
              onClick={() => setActiveTab('basic')}
            >
              Configuration de base
            </button>
            <button 
              className={`export-tab ${activeTab === 'advanced' ? 'active' : ''}`}
              onClick={() => setActiveTab('advanced')}
              disabled={!selectedFormats.includes('pdf')}
            >
              Options PDF avancées
            </button>
          </div>

          {activeTab === 'basic' ? (
            <div className="export-tab-content">
              {/* Sélection de client (SuperAdmin uniquement) */}
              {userRole === 'superadmin' && (
                <div className="form-group">
                  <label htmlFor="clientSelect">Client *</label>
                  <select
                    id="clientSelect"
                    className="input"
                    value={selectedClientId}
                    onChange={(e) => handleClientChange(e.target.value)}
                    disabled={loading || loadingClients}
                  >
                    <option value="">Sélectionnez un client</option>
                    {clients.map(client => (
                      <option key={client.id} value={client.id}>
                        {client.nom_entreprise}
                      </option>
                    ))}
                  </select>
                  {clients.length === 0 && !loadingClients && (
                    <p className="help-text">Aucun client disponible</p>
                  )}
                </div>
              )}

              {/* Sélection d'appareil */}
              <div className="form-group">
                <label htmlFor="deviceSelect">Appareil</label>
                <select
                  id="deviceSelect"
                  className="input"
                  value={selectedDeviceId}
                  onChange={(e) => setSelectedDeviceId(e.target.value)}
                  disabled={loading || loadingDevices || (userRole === 'superadmin' && !selectedClientId)}
                >
                  <option value="all">
                    Tous les appareils {devices.length > 0 && `(${devices.length})`}
                  </option>
                  {devices.map(device => (
                    <option key={device.id} value={device.id}>
                      {device.nom_appareil} ({device.type_systeme})
                    </option>
                  ))}
                </select>
                {userRole === 'superadmin' && !selectedClientId && (
                  <p className="help-text">Sélectionnez d'abord un client</p>
                )}
                {devices.length === 0 && !loadingDevices && selectedClientId && (
                  <p className="help-text">Aucun appareil assigné à ce client</p>
                )}
              </div>

              {/* Dates */}
              <div className="form-row">
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

              {/* Formats */}
              <div className="form-group">
                <label>Formats d'export *</label>
                <div className="format-checkboxes">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedFormats.includes('csv')}
                      onChange={() => toggleFormat('csv')}
                      disabled={loading}
                    />
                    <span>CSV (Données brutes)</span>
                  </label>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedFormats.includes('excel')}
                      onChange={() => toggleFormat('excel')}
                      disabled={loading}
                    />
                    <span>Excel (Tableau détaillé)</span>
                  </label>
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedFormats.includes('pdf')}
                      onChange={() => toggleFormat('pdf')}
                      disabled={loading}
                    />
                    <span>PDF (Graphiques visuels)</span>
                  </label>
                </div>
              </div>

              {/* Aperçu */}
              <div className="export-preview">
                <h4>Contenu du rapport :</h4>
                <ul>
                  <li>Horodatage de chaque mesure</li>
                  <li>Informations de l'appareil (ID, nom, type)</li>
                  {selectedDeviceId === 'all' && devices.length > 0 && (
                    <li>Données de {devices.length} appareil(s)</li>
                  )}
                  <li>Données monophasées et triphasées</li>
                  <li>Tensions, courants, puissances, énergies</li>
                  <li>Données environnementales (T°, humidité)</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="export-tab-content">
              <div className="pdf-options">
                {/* Presets */}
                <div className="form-group">
                  <label>Presets rapides</label>
                  <div className="preset-buttons">
                    <button 
                      className="btn btn-small btn-outline"
                      onClick={() => applyPdfPreset('minimal')}
                      disabled={loading}
                    >
                      Minimal
                    </button>
                    <button 
                      className="btn btn-small btn-outline"
                      onClick={() => applyPdfPreset('standard')}
                      disabled={loading}
                    >
                      Standard
                    </button>
                    <button 
                      className="btn btn-small btn-outline"
                      onClick={() => applyPdfPreset('detailed')}
                      disabled={loading}
                    >
                      Détaillé
                    </button>
                    <button 
                      className="btn btn-small btn-outline"
                      onClick={() => applyPdfPreset('presentation')}
                      disabled={loading}
                    >
                      Présentation
                    </button>
                  </div>
                </div>

                {/* Graphiques à inclure */}
                <div className="form-group">
                  <label>Graphiques à inclure</label>
                  <div className="checkbox-grid">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.includePower}
                        onChange={(e) => updatePdfOption('includePower', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Puissance</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.includeVoltage}
                        onChange={(e) => updatePdfOption('includeVoltage', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Tension</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.includeCurrent}
                        onChange={(e) => updatePdfOption('includeCurrent', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Courant</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.includeSummary}
                        onChange={(e) => updatePdfOption('includeSummary', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Page de résumé</span>
                    </label>
                  </div>
                </div>

                {/* Style de graphique */}
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="chartStyle">Style de graphique</label>
                    <select
                      id="chartStyle"
                      className="input"
                      value={pdfOptions.chartStyle}
                      onChange={(e) => updatePdfOption('chartStyle', e.target.value)}
                      disabled={loading}
                    >
                      <option value="line">Ligne</option>
                      <option value="area">Aires remplies</option>
                      <option value="bar">Barres</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="pageOrientation">Orientation</label>
                    <select
                      id="pageOrientation"
                      className="input"
                      value={pdfOptions.pageOrientation}
                      onChange={(e) => updatePdfOption('pageOrientation', e.target.value)}
                      disabled={loading}
                    >
                      <option value="landscape">Paysage</option>
                      <option value="portrait">Portrait</option>
                    </select>
                  </div>
                </div>

                {/* Options d'affichage */}
                <div className="form-group">
                  <label>Options d'affichage</label>
                  <div className="checkbox-grid">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.showGrid}
                        onChange={(e) => updatePdfOption('showGrid', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Afficher la grille</span>
                    </label>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={pdfOptions.showLegend}
                        onChange={(e) => updatePdfOption('showLegend', e.target.checked)}
                        disabled={loading}
                      />
                      <span>Afficher la légende</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          {error && (
            <div className="export-message export-error">
              <span className="message-icon">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="export-message export-success">
              <span className="message-icon">✅</span>
              <span>{success}</span>
            </div>
          )}
        </div>

        {/* Footer */}
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
            disabled={
              !startDate || 
              !endDate || 
              selectedFormats.length === 0 || 
              loadingDevices ||
              (userRole === 'superadmin' && !selectedClientId)
            }
          >
            {loading ? 'Export en cours...' : `Exporter (${selectedFormats.length})`}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ExportModal