import React, { useState, useEffect } from 'react';
import { useAuth } from '../../store/authContext';
import AdminLayout from '../../layouts/AdminLayout';
import AlertPanel from '../../components/Alerts/AlertPanel';
import AlertIndicator from '../../components/Alerts/AlertIndicator';
import AlertService from '../../services/alertService';
import deviceService from '../../services/deviceService';
import Button from '../../components/Button';
import './AlertsPage.css';

const AlertsPage = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showAlertPanel, setShowAlertPanel] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    device: '',
    severity: 'all',
    status: 'all',
    timeRange: '24'
  });
  const [alerts, setAlerts] = useState([]);
  const [alertsLoading, setAlertsLoading] = useState(false);

  useEffect(() => {
    loadDevices();
    // Charger toutes les alertes au chargement initial
    loadAlerts();
  }, [user]);

  useEffect(() => {
    loadAlerts();
  }, [filters]);

  const loadDevices = async () => {
    try {
      setLoading(true);
      const response = await deviceService.listerAppareils();
      if (response.data.success) {
        setDevices(response.data.appareils || []);
      }
    } catch (error) {
      console.error('Erreur chargement appareils:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAlerts = async () => {
    try {
      setAlertsLoading(true);
      let allAlerts = [];
      
      if (filters.device) {
        // Si un appareil spécifique est sélectionné, charger ses alertes
        const response = await AlertService.obtenirAlertesAppareil(
          filters.device,
          parseInt(filters.timeRange),
          50
        );
        
        if (response.data.success) {
          allAlerts = response.data.alertes || [];
        }
      } else {
        // Si aucun appareil n'est sélectionné, charger les alertes pour chaque appareil
        for (const device of devices) {
          try {
            const response = await AlertService.obtenirAlertesAppareil(
              device.id,
              parseInt(filters.timeRange),
              50
            );
            
            if (response.data.success) {
              allAlerts = [...allAlerts, ...(response.data.alertes || [])];
            }
          } catch (error) {
            console.error(`Erreur chargement alertes pour appareil ${device.id}:`, error);
          }
        }
      }
      
      // Filtrer par gravité
      if (filters.severity !== 'all') {
        allAlerts = allAlerts.filter(alert => 
          alert.gravite === parseInt(filters.severity)
        );
      }
      
      // Filtrer par statut
      if (filters.status !== 'all') {
        const isResolved = filters.status === 'resolved';
        allAlerts = allAlerts.filter(alert => 
          (alert.resolu === isResolved)
        );
      }
      
      setAlerts(allAlerts);
    } catch (error) {
      console.error('Erreur chargement alertes:', error);
    } finally {
      setAlertsLoading(false);
    }
  };

  const handleDeviceChange = (e) => {
    setFilters({...filters, device: e.target.value});
  };

  const handleSeverityChange = (e) => {
    setFilters({...filters, severity: e.target.value});
  };

  const handleStatusChange = (e) => {
    setFilters({...filters, status: e.target.value});
  };

  const handleTimeRangeChange = (e) => {
    setFilters({...filters, timeRange: e.target.value});
  };

  const handleViewDetails = (device) => {
    setSelectedDevice(device);
    setShowAlertPanel(true);
  };

  const handleClosePanel = () => {
    setShowAlertPanel(false);
    setSelectedDevice(null);
    // Recharger les alertes après fermeture du panel
    loadAlerts();
  };

  const handleResolveAlert = async (alertId) => {
    try {
      const response = await AlertService.resoudreAlerte(alertId, 'Résolu depuis la page d\'alertes');
      if (response.data.success) {
        // Actualiser la liste des alertes
        loadAlerts();
      }
    } catch (error) {
      console.error('Erreur résolution alerte:', error);
    }
  };

  const handleMarkAsSeen = async (alertId) => {
    try {
      const response = await AlertService.marquerAlertesVues([alertId]);
      if (response.data.success) {
        // Actualiser la liste des alertes
        loadAlerts();
      }
    } catch (error) {
      console.error('Erreur marquage alerte comme vue:', error);
    }
  };

  const getAlertSeverityClass = (severity) => {
    switch (severity) {
      case 1: return 'severity-low';
      case 2: return 'severity-medium';
      case 3: return 'severity-high';
      default: return '';
    }
  };

  const getAlertSeverityText = (severity) => {
    switch (severity) {
      case 1: return 'Faible';
      case 2: return 'Moyenne';
      case 3: return 'Élevée';
      default: return 'Inconnue';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <AdminLayout>
      <div className="alerts-page">
        <div className="alerts-header">
          <h1>Gestion des Alertes</h1>
          <div className="filter-controls">
            <div className="filter-group">
              <label>Appareil:</label>
              <select 
                className="filter-select"
                value={filters.device}
                onChange={handleDeviceChange}
              >
                <option value="">Tous les appareils</option>
                {devices.map(device => (
                  <option key={device.id} value={device.id}>
                    {device.nom || device.tuya_device_id}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="filter-group">
              <label>Gravité:</label>
              <select 
                className="filter-select"
                value={filters.severity}
                onChange={handleSeverityChange}
              >
                <option value="all">Toutes</option>
                <option value="1">Faible</option>
                <option value="2">Moyenne</option>
                <option value="3">Élevée</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label>Statut:</label>
              <select 
                className="filter-select"
                value={filters.status}
                onChange={handleStatusChange}
              >
                <option value="all">Tous</option>
                <option value="active">Actives</option>
                <option value="resolved">Résolues</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label>Période:</label>
              <select 
                className="filter-select"
                value={filters.timeRange}
                onChange={handleTimeRangeChange}
              >
                <option value="24">24 heures</option>
                <option value="48">48 heures</option>
                <option value="72">72 heures</option>
                <option value="168">7 jours</option>
              </select>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement des appareils...</p>
          </div>
        ) : alertsLoading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Chargement des alertes...</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="no-alerts">
            <p>Aucune alerte trouvée pour les filtres sélectionnés.</p>
          </div>
        ) : (
          <div className="alerts-table-container">
            <table className="alerts-table">
              <thead>
                <tr>
                  <th>Appareil</th>
                  <th>Type</th>
                  <th>Message</th>
                  <th>Gravité</th>
                  <th>Date</th>
                  <th>Statut</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map(alert => {
                  const device = devices.find(d => d.id === alert.appareil_id);
                  return (
                    <tr key={alert.id} className={alert.vu ? '' : 'unread-alert'}>
                      <td>{device ? (device.nom || device.tuya_device_id) : alert.appareil_id}</td>
                      <td>{alert.type}</td>
                      <td>{alert.message}</td>
                      <td>
                        <span className={`severity-badge ${getAlertSeverityClass(alert.gravite)}`}>
                          {getAlertSeverityText(alert.gravite)}
                        </span>
                      </td>
                      <td>{formatDate(alert.date_creation)}</td>
                      <td>
                        <span className={`status-badge ${alert.resolu ? 'status-resolved' : 'status-active'}`}>
                          {alert.resolu ? 'Résolu' : 'Actif'}
                        </span>
                      </td>
                      <td>
                        <div className="action-buttons">
                          {!alert.resolu && (
                            <Button 
                              variant="primary" 
                              size="small"
                              onClick={() => handleResolveAlert(alert.id)}
                            >
                              Résoudre
                            </Button>
                          )}
                          
                          {!alert.vu && (
                            <Button 
                              variant="outline" 
                              size="small"
                              onClick={() => handleMarkAsSeen(alert.id)}
                            >
                              Marquer comme vu
                            </Button>
                          )}
                          
                          {device && (
                            <Button 
                              variant="secondary" 
                              size="small"
                              onClick={() => handleViewDetails(device)}
                            >
                              Détails
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        
        {showAlertPanel && selectedDevice && (
          <div className="alert-panel-overlay">
            <div className="alert-panel-container">
              <AlertPanel 
                device={selectedDevice} 
                onClose={handleClosePanel} 
              />
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
};

export default AlertsPage;