// services/exportService.js - Service d'export complet modulable

import { apiClient } from './authService'

class ExportService {
  /**
   * Export CSV
   * @param {Object} options - Options d'export
   * @param {string} options.clientId - ID du client (requis)
   * @param {string} options.deviceId - ID de l'appareil (optionnel)
   * @param {string} options.startDate - Date de début YYYY-MM-DD (requis)
   * @param {string} options.endDate - Date de fin YYYY-MM-DD (requis)
   */
  async exportCSV(options) {
    try {
      const params = this._buildParams(options)
      
      const response = await apiClient.get(`/export/csv?${params}`, {
        responseType: 'blob'
      })

      return response.data

    } catch (error) {
      console.error('Erreur export CSV:', error)
      throw this._handleError(error)
    }
  }

  /**
   * Export Excel
   * @param {Object} options - Options d'export (mêmes que CSV)
   */
  async exportExcel(options) {
    try {
      const params = this._buildParams(options)
      
      const response = await apiClient.get(`/export/excel?${params}`, {
        responseType: 'blob'
      })

      return response.data

    } catch (error) {
      console.error('Erreur export Excel:', error)
      throw this._handleError(error)
    }
  }

  /**
   * Export PDF avec graphiques personnalisables
   * @param {Object} options - Options d'export
   * @param {string} options.clientId - ID du client (requis)
   * @param {string} options.deviceId - ID de l'appareil (optionnel)
   * @param {string} options.startDate - Date de début (requis)
   * @param {string} options.endDate - Date de fin (requis)
   * @param {boolean} options.includePower - Inclure graphique puissance (défaut: true)
   * @param {boolean} options.includeVoltage - Inclure graphique tension (défaut: true)
   * @param {boolean} options.includeCurrent - Inclure graphique courant (défaut: true)
   * @param {boolean} options.includeSummary - Inclure page de résumé (défaut: true)
   * @param {string} options.chartStyle - Style: 'line', 'area', 'bar' (défaut: 'line')
   * @param {string} options.pageOrientation - 'portrait' ou 'landscape' (défaut: 'landscape')
   * @param {boolean} options.showGrid - Afficher la grille (défaut: true)
   * @param {boolean} options.showLegend - Afficher la légende (défaut: true)
   */
  async exportPDF(options) {
    try {
      const params = this._buildParams(options, true)
      
      const response = await apiClient.get(`/export/pdf-graphique?${params}`, {
        responseType: 'blob'
      })

      return response.data

    } catch (error) {
      console.error('Erreur export PDF:', error)
      throw this._handleError(error)
    }
  }

  /**
   * Construire les paramètres URL
   * @private
   */
  _buildParams(options, isPDF = false) {
    const params = new URLSearchParams()

    // Paramètres obligatoires
    params.append('client_id', options.clientId)
    params.append('start_date', options.startDate)
    params.append('end_date', options.endDate)

    // Paramètre optionnel: device_id
    if (options.deviceId) {
      params.append('device_id', options.deviceId)
    }

    // Paramètres spécifiques PDF
    if (isPDF) {
      if (options.includePower !== undefined) {
        params.append('include_power', options.includePower)
      }
      if (options.includeVoltage !== undefined) {
        params.append('include_voltage', options.includeVoltage)
      }
      if (options.includeCurrent !== undefined) {
        params.append('include_current', options.includeCurrent)
      }
      if (options.includeSummary !== undefined) {
        params.append('include_summary', options.includeSummary)
      }
      if (options.chartStyle) {
        params.append('chart_style', options.chartStyle)
      }
      if (options.pageOrientation) {
        params.append('page_orientation', options.pageOrientation)
      }
      if (options.showGrid !== undefined) {
        params.append('show_grid', options.showGrid)
      }
      if (options.showLegend !== undefined) {
        params.append('show_legend', options.showLegend)
      }
    }

    return params
  }

  /**
   * Télécharger un fichier
   * @param {Blob} blob - Fichier en Blob
   * @param {string} filename - Nom du fichier
   */
  downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
    
    // Nettoyage
    setTimeout(() => {
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    }, 100)
  }

  /**
   * Générer un nom de fichier
   * @private
   */
  _generateFilename(type, clientName = '', deviceName = '') {
    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    const timeStr = new Date().toTimeString().slice(0, 5).replace(/:/g, '')
    
    let scope = 'All'
    if (deviceName) {
      scope = deviceName.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20)
    } else if (clientName) {
      scope = clientName.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 20)
    }

    const extensions = {
      csv: 'csv',
      excel: 'xlsx',
      pdf: 'pdf'
    }

    return `Rapport_${type}_${scope}_${dateStr}_${timeStr}.${extensions[type]}`
  }

  /**
   * Export CSV avec téléchargement automatique
   */
  async exportAndDownloadCSV(options, clientName = '', deviceName = '') {
  const blob = await this.exportCSV(options)
  const filename = this._generateFilename('csv', clientName, deviceName)
  this.downloadFile(blob, filename)
  
  return { success: true, filename }
}
  /**
   * Export Excel avec téléchargement automatique
   */
  async exportAndDownloadExcel(options, clientName = '', deviceName = '') {
  const blob = await this.exportExcel(options)
  const filename = this._generateFilename('excel', clientName, deviceName)
  this.downloadFile(blob, filename)
  
  return { success: true, filename }
}

  /**
   * Export PDF avec téléchargement automatique
   */
  async exportAndDownloadPDF(options, clientName = '', deviceName = '') {
  const blob = await this.exportPDF(options)
  const filename = this._generateFilename('pdf', clientName, deviceName)
  this.downloadFile(blob, filename)
  
  return { success: true, filename }
}

  /**
   * Export multiple formats en une fois
   * @param {Array<string>} formats - ['csv', 'excel', 'pdf']
   * @param {Object} options - Options d'export
   */
  async exportMultiple(formats, options, clientName = '', deviceName = '') {
    const results = []
    const errors = []

    for (const format of formats) {
      try {
        let result
        switch (format) {
          case 'csv':
            result = await this.exportAndDownloadCSV(options, clientName, deviceName)
            break
          case 'excel':
            result = await this.exportAndDownloadExcel(options, clientName, deviceName)
            break
          case 'pdf':
            result = await this.exportAndDownloadPDF(options, clientName, deviceName)
            break
          default:
            throw new Error(`Format non supporté: ${format}`)
        }
        results.push({ format, ...result })
      } catch (error) {
        errors.push({ format, error: error.message })
      }
    }

    return { results, errors, success: errors.length === 0 }
  }

  /**
   * Valider les options d'export
   * @param {Object} options - Options à valider
   * @returns {Object} - { valid: boolean, errors: string[] }
   */
  validateOptions(options) {
    const errors = []

    if (!options.clientId) {
      errors.push('client_id est requis')
    }

    if (!options.startDate) {
      errors.push('start_date est requis')
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(options.startDate)) {
      errors.push('start_date doit être au format YYYY-MM-DD')
    }

    if (!options.endDate) {
      errors.push('end_date est requis')
    } else if (!/^\d{4}-\d{2}-\d{2}$/.test(options.endDate)) {
      errors.push('end_date doit être au format YYYY-MM-DD')
    }

    if (options.startDate && options.endDate && options.startDate > options.endDate) {
      errors.push('start_date doit être antérieure à end_date')
    }

    if (options.chartStyle && !['line', 'area', 'bar'].includes(options.chartStyle)) {
      errors.push('chart_style doit être "line", "area" ou "bar"')
    }

    if (options.pageOrientation && !['portrait', 'landscape'].includes(options.pageOrientation)) {
      errors.push('page_orientation doit être "portrait" ou "landscape"')
    }

    return {
      valid: errors.length === 0,
      errors
    }
  }

  /**
   * Gérer les erreurs
   * @private
   */
  _handleError(error) {
    if (error.response) {
      // Le serveur a répondu avec un code d'erreur
      const status = error.response.status
      const data = error.response.data

      switch (status) {
        case 400:
          return new Error(data.error || 'Paramètres invalides')
        case 401:
          return new Error('Authentification requise')
        case 403:
          return new Error('Accès non autorisé à ces données')
        case 404:
          return new Error(data.error || 'Aucune donnée trouvée pour la période spécifiée')
        case 500:
          return new Error('Erreur serveur lors de la génération du rapport')
        default:
          return new Error(`Erreur ${status}: ${data.error || 'Erreur inconnue'}`)
      }
    } else if (error.request) {
      // Pas de réponse du serveur
      return new Error('Impossible de contacter le serveur')
    } else {
      // Erreur lors de la configuration de la requête
      return new Error(error.message || 'Erreur lors de la préparation de l\'export')
    }
  }

  /**
   * Vérifier la santé du service d'export
   */
  async checkHealth() {
    try {
      const response = await apiClient.get('/export/health')
      return response.data
    } catch (error) {
      console.error('Erreur vérification santé:', error)
      throw error
    }
  }

  /**
   * Obtenir les presets d'options PDF
   */
  getPDFPresets() {
    return {
      minimal: {
        includePower: true,
        includeVoltage: false,
        includeCurrent: false,
        includeSummary: false,
        chartStyle: 'line',
        pageOrientation: 'landscape',
        showGrid: false,
        showLegend: false
      },
      standard: {
        includePower: true,
        includeVoltage: true,
        includeCurrent: true,
        includeSummary: true,
        chartStyle: 'line',
        pageOrientation: 'landscape',
        showGrid: true,
        showLegend: true
      },
      detailed: {
        includePower: true,
        includeVoltage: true,
        includeCurrent: true,
        includeSummary: true,
        chartStyle: 'area',
        pageOrientation: 'portrait',
        showGrid: true,
        showLegend: true
      },
      presentation: {
        includePower: true,
        includeVoltage: true,
        includeCurrent: false,
        includeSummary: true,
        chartStyle: 'area',
        pageOrientation: 'landscape',
        showGrid: false,
        showLegend: true
      }
    }
  }
}

export default new ExportService()