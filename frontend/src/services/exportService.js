// services/exportService.js - Service d'export Excel détaillé

import { apiClient } from './authService'

class ExportService {
  /**
   * Export Excel détaillé des données DeviceData
   * @param {string} clientId - ID du client
   * @param {string} startDate - Date de début (YYYY-MM-DD)
   * @param {string} endDate - Date de fin (YYYY-MM-DD)
   * @returns {Promise<Blob>} - Fichier Excel en tant que Blob
   */
  async exportDetailedExcel(clientId, startDate, endDate) {
    try {
      const params = new URLSearchParams({
        client_id: clientId,
        start_date: startDate,
        end_date: endDate
      })

      const response = await apiClient.get(`/api/export/detailed-excel?${params}`, {
        responseType: 'blob'
      })

      return response.data

    } catch (error) {
      console.error('Erreur lors de l\'export Excel:', error)
      throw error
    }
  }

  /**
   * Télécharger le fichier Excel
   * @param {Blob} blob - Fichier Excel en tant que Blob
   * @param {string} filename - Nom du fichier
   */
  downloadExcelFile(blob, filename) {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  /**
   * Export Excel complet avec téléchargement automatique
   * @param {string} clientId - ID du client
   * @param {string} startDate - Date de début (YYYY-MM-DD)
   * @param {string} endDate - Date de fin (YYYY-MM-DD)
   * @param {string} clientName - Nom du client (optionnel, pour le nom de fichier)
   */
  async exportAndDownloadExcel(clientId, startDate, endDate, clientName = '') {
    try {
      const blob = await this.exportDetailedExcel(clientId, startDate, endDate)
      
      // Générer le nom du fichier
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '')
      const clientNameStr = clientName ? `_${clientName.replace(/[^a-zA-Z0-9]/g, '_')}` : ''
      const filename = `Rapport_Detaillé_${clientId}${clientNameStr}_${dateStr}.xlsx`
      
      this.downloadExcelFile(blob, filename)
      
      return { success: true, filename }
      
    } catch (error) {
      console.error('Erreur lors de l\'export et téléchargement:', error)
      throw error
    }
  }

  /**
   * Vérifier la santé du service d'export
   */
  async checkHealth() {
    try {
      const response = await apiClient.get('/api/export/health')
      return response.data
    } catch (error) {
      console.error('Erreur lors de la vérification de santé:', error)
      throw error
    }
  }
}

export default new ExportService()
