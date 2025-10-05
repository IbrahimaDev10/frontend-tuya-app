import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../../contexts/AuthContext';
import Button from '../Button';
import Input from '../Input';
import deviceService from '../../services/deviceService';
import userService from '../../services/userService';
import './ExportModal.css';

const ExportModal = ({ isOpen, onClose, onExport, clientId, clientName }) => {
  const { user } = useContext(AuthContext);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [selectedClient, setSelectedClient] = useState(clientId || '');
  const [selectedDevice, setSelectedDevice] = useState('');
  const [clients, setClients] = useState([]);
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [exportFormat, setExportFormat] = useState('pdf');
  const [includeGraphs, setIncludeGraphs] = useState(true);
  const [includeConsumption, setIncludeConsumption] = useState(true);
  const [includeVoltage, setIncludeVoltage] = useState(true);
  const [includeCurrent, setIncludeCurrent] = useState(true);

  const isSuperAdmin = user && user.role === 'superadmin';

  useEffect(() => {
    if (isOpen) {
      // Initialiser les dates par défaut (7 derniers jours)
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 7);
      
      setStartDate(start.toISOString().split('T')[0]);
      setEndDate(end.toISOString().split('T')[0]);
      
      // Charger les clients si superadmin
      if (isSuperAdmin) {
        loadClients();
      } else {
        // Pour les autres rôles, charger les appareils du client
        if (clientId) {
          setSelectedClient(clientId);
          loadDevices(clientId);
        }
      }
    }
  }, [isOpen, isSuperAdmin, clientId]);

  useEffect(() => {
    if (selectedClient) {
      loadDevices(selectedClient);
    } else {
      setDevices([]);
      setSelectedDevice('');
    }
  }, [selectedClient]);

  const loadClients = async () => {
    try {
      setLoading(true);
      const response = await userService.listerClients();
      if (response.data.success) {
        setClients(response.data.clients || []);
      }
    } catch (error) {
      console.error('Erreur chargement clients:', error);
      setError('Erreur lors du chargement des clients');
    } finally {
      setLoading(false);
    }
  };

  const loadDevices = async (clientId) => {
    try {
      setLoading(true);
      const response = await deviceService.listerAppareilsClient(clientId);
      if (response.data.success) {
        setDevices(response.data.appareils || []);
      }
    } catch (error) {
      console.error('Erreur chargement appareils:', error);
      setError('Erreur lors du chargement des appareils');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    
    if (!selectedClient) {
      setError('Veuillez sélectionner un client');
      return;
    }
    
    if (!startDate || !endDate) {
      setError('Veuillez spécifier les dates de début et de fin');
      return;
    }
    
    try {
      setLoading(true);
      
      // Préparer les options d'export
      const exportOptions = {
        clientId: selectedClient,
        deviceId: selectedDevice || undefined,
        startDate,
        endDate,
        format: exportFormat,
        includeGraphs,
        includeConsumption,
        includeVoltage,
        includeCurrent
      };
      
      // Appeler la fonction d'export fournie par le parent
      if (onExport) {
        await onExport(exportOptions);
        setSuccess('Rapport généré avec succès');
      }
    } catch (error) {
      console.error('Erreur génération rapport:', error);
      setError('Erreur lors de la génération du rapport');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="export-modal">
        <div className="modal-header">
          <h3>Générer un rapport</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}
            
            {/* Sélection du client (uniquement pour superadmin) */}
            {isSuperAdmin && (
              <div className="form-group">
                <label>Client:</label>
                <select 
                  value={selectedClient} 
                  onChange={(e) => setSelectedClient(e.target.value)}
                  disabled={loading}
                  required
                >
                  <option value="">Sélectionner un client</option>
                  {clients.map(client => (
                    <option key={client.id} value={client.id}>
                      {client.nom}
                    </option>
                  ))}
                </select>
              </div>
            )}
            
            {/* Sélection de l'appareil (optionnel) */}
            <div className="form-group">
              <label>Appareil (optionnel):</label>
              <select 
                value={selectedDevice} 
                onChange={(e) => setSelectedDevice(e.target.value)}
                disabled={loading || !selectedClient}
              >
                <option value="">Tous les appareils</option>
                {devices.map(device => (
                  <option key={device.id} value={device.id}>
                    {device.nom_appareil}
                  </option>
                ))}
              </select>
            </div>
            
            {/* Période */}
            <div className="form-group date-range">
              <div>
                <label>Date de début:</label>
                <Input 
                  type="date" 
                  value={startDate} 
                  onChange={(e) => setStartDate(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
              <div>
                <label>Date de fin:</label>
                <Input 
                  type="date" 
                  value={endDate} 
                  onChange={(e) => setEndDate(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
            </div>
            
            {/* Format d'export */}
            <div className="form-group">
              <label>Format:</label>
              <div className="format-options">
                <label className={`format-option ${exportFormat === 'pdf' ? 'selected' : ''}`}>
                  <input 
                    type="radio" 
                    name="format" 
                    value="pdf" 
                    checked={exportFormat === 'pdf'} 
                    onChange={() => setExportFormat('pdf')}
                  />
                  <span className="format-icon">📄</span>
                  <span>PDF</span>
                </label>
                <label className={`format-option ${exportFormat === 'excel' ? 'selected' : ''}`}>
                  <input 
                    type="radio" 
                    name="format" 
                    value="excel" 
                    checked={exportFormat === 'excel'} 
                    onChange={() => setExportFormat('excel')}
                  />
                  <span className="format-icon">📊</span>
                  <span>Excel</span>
                </label>
                <label className={`format-option ${exportFormat === 'csv' ? 'selected' : ''}`}>
                  <input 
                    type="radio" 
                    name="format" 
                    value="csv" 
                    checked={exportFormat === 'csv'} 
                    onChange={() => setExportFormat('csv')}
                  />
                  <span className="format-icon">📋</span>
                  <span>CSV</span>
                </label>
              </div>
            </div>
            
            {/* Options pour PDF uniquement */}
            {exportFormat === 'pdf' && (
              <div className="form-group">
                <label>Options PDF:</label>
                <div className="checkbox-group">
                  <label>
                    <input 
                      type="checkbox" 
                      checked={includeGraphs} 
                      onChange={(e) => setIncludeGraphs(e.target.checked)}
                    />
                    Inclure les graphiques
                  </label>
                  {includeGraphs && (
                    <>
                      <label>
                        <input 
                          type="checkbox" 
                          checked={includeConsumption} 
                          onChange={(e) => setIncludeConsumption(e.target.checked)}
                        />
                        Consommation
                      </label>
                      <label>
                        <input 
                          type="checkbox" 
                          checked={includeVoltage} 
                          onChange={(e) => setIncludeVoltage(e.target.checked)}
                        />
                        Tension
                      </label>
                      <label>
                        <input 
                          type="checkbox" 
                          checked={includeCurrent} 
                          onChange={(e) => setIncludeCurrent(e.target.checked)}
                        />
                        Courant
                      </label>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <div className="modal-footer">
            <Button 
              type="button" 
              variant="outline" 
              onClick={onClose}
              disabled={loading}
            >
              Annuler
            </Button>
            <Button 
              type="submit" 
              variant="primary" 
              loading={loading}
            >
              Générer
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ExportModal;