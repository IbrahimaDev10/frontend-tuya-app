// frontend/src/pages/Devices/DeviceConfigurationPage.jsx

import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom'; // Pour récupérer l'ID de l'appareil depuis l'URL
import DeviceService from '../../services/deviceService';
import AdminLayout from '../../layouts/AdminLayout'; // Ou SuperAdminLayout/ClientLayout selon le rôle
import ProtectionModal from '../../components/DeviceProtection/ProtectionModal'; // Importez vos modaux
import ScheduleModal from '../../components/DeviceProtection/ScheduleModal';
import Button from '../../components/Button';
import Toast from '../../components/Toast'; // Pour les notifications
import './DeviceConfigurationPage.css'; // Nouveau fichier CSS pour cette page

const DeviceConfigurationPage = () => {
  const { deviceId } = useParams(); // Récupère l'ID de l'appareil depuis l'URL (ex: /devices/config/:deviceId)
  const [device, setDevice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showProtectionModal, setShowProtectionModal] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    loadDeviceDetails();
  }, [deviceId]); // Recharge si l'ID de l'appareil change

  const loadDeviceDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await DeviceService.obtenirAppareil(deviceId);
      if (response.data.success) {
        setDevice(response.data.data);
      } else {
        setError(response.data.error || "Erreur lors du chargement de l'appareil.");
      }
    } catch (err) {
      console.error("Erreur chargement appareil:", err);
      setError("Impossible de charger les détails de l'appareil.");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleModalSave = () => {
    // Après la sauvegarde dans un modal, fermez-le et rafraîchissez les détails de l'appareil
    setShowProtectionModal(false);
    setShowScheduleModal(false);
    loadDeviceDetails(); // Recharge les détails pour s'assurer que les statuts sont à jour
    showToast('Configuration sauvegardée avec succès !', 'success');
  };

  if (loading) {
    return (
      <AdminLayout> {/* Adaptez le Layout selon le rôle */}
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Chargement de l'appareil...</p>
        </div>
      </AdminLayout>
    );
  }

  if (error) {
    return (
      <AdminLayout>
        <div className="error-container">
          <p>{error}</p>
          <Button onClick={loadDeviceDetails}>Réessayer</Button>
        </div>
      </AdminLayout>
    );
  }

  if (!device) {
    return (
      <AdminLayout>
        <div className="empty-state">
          <p>Appareil non trouvé.</p>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="device-config-page">
        <h1>Configuration de l'appareil : {device.nom_appareil}</h1>
        <p>ID Tuya : {device.tuya_device_id}</p>
        <p>Client : {device.client?.nom_entreprise || 'N/A'}</p>
        <p>Site : {device.site?.nom_site || 'N/A'}</p>
        {/* Ajoutez d'autres informations pertinentes sur l'appareil */}

        <div className="config-sections">
          {/* Section Protection */}
          <div className="config-card">
            <h2>🛡️ Protection Automatique</h2>
            <p>Statut : {device.protection_automatique_active ? 'Activée' : 'Désactivée'}</p>
            {/* Afficher un résumé des seuils configurés si vous le souhaitez */}
            <Button onClick={() => setShowProtectionModal(true)}>
              Configurer la Protection
            </Button>
          </div>

          {/* Section Programmation */}
          <div className="config-card">
            <h2>⏰ Programmation Horaire</h2>
            <p>Statut : {device.programmation_active ? 'Activée' : 'Désactivée'}</p>
            {/* Afficher un résumé des horaires configurés si vous le souhaitez */}
            <Button onClick={() => setShowScheduleModal(true)}>
              Configurer la Programmation
            </Button>
          </div>

          {/* Ajoutez d'autres sections de configuration ici si nécessaire */}
          {/* Par exemple, pour les seuils monophasés/triphasés, etc. */}
        </div>
      </div>

      {/* Modaux */}
      {showProtectionModal && device && (
        <ProtectionModal
          device={device}
          onClose={() => setShowProtectionModal(false)}
          onSave={handleModalSave}
        />
      )}

      {showScheduleModal && device && (
        <ScheduleModal
          device={device}
          onClose={() => setShowScheduleModal(false)}
          onSave={handleModalSave}
        />
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </AdminLayout>
  );
};

export default DeviceConfigurationPage;
