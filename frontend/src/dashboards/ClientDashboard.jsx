import React, { useState, useEffect } from 'react';
import ClientLayout from '../layouts/ClientLayout';
import { useAuth } from '../store/authContext';
import DeviceService from '../services/deviceService';
import GlobalConsumptionChart from './GlobalConsumptionChart';
import './Dashboard.css';

// Fonction pour formater les grands nombres (ex: 12500 W -> 12.5 kW)
const formatPower = (watts) => {
  if (watts == null || isNaN(watts)) return '--';
  if (watts < 1000) return `${Math.round(watts)} W`;
  return `${(watts / 1000).toFixed(1)} kW`;
};

const ClientDashboard = () => {
  const { user } = useAuth();
  const [consumptionData, setConsumptionData] = useState([]);
  const [energyStats, setEnergyStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [chartTimeRange, setChartTimeRange] = useState('24h');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Récupération des statistiques pour le client (limité à ses appareils)
        const statsResponse = await DeviceService.obtenirStatsDashboardClient();
        if (statsResponse.data.success) {
          setEnergyStats(statsResponse.data.stats);
        }

        // Récupération des données de consommation pour le graphique
        const chartResponse = await DeviceService.obtenirGraphiqueClientPuissance(
          Date.now() - (chartTimeRange === '24h' ? 24 : 7 * 24) * 3600 * 1000,
          Date.now(),
          chartTimeRange === '24h' ? 'hourly' : 'daily'
        );
        
        if (chartResponse.data.success) {
          const formattedData = chartResponse.data.donnees_bdd.map(d => ({
            time: d.timestamp,
            value: d.value
          }));
          setConsumptionData(formattedData);
        }
      } catch (error) {
        console.error("Erreur de chargement du dashboard client", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [chartTimeRange]);

  return (
    <ClientLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de bord Énergétique</h1>
          <p>Suivi de vos appareils</p>
        </div>

        <div className="dashboard-content">
          <div className="welcome-card">
            <div className="welcome-icon">📱</div>
            <div className="welcome-text">
              <h2>Bienvenue, {user?.nom_complet}</h2>
              <p>
                Consultez l'état de vos appareils et suivez votre consommation énergétique en temps réel.
              </p>
            </div>
          </div>

          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">💡</div>
              <div className="stat-content">
                <h3>Consommation Actuelle</h3>
                <div className="stat-number">{formatPower(energyStats.current_total_power)}</div>
                <p>Puissance totale de vos appareils</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">📈</div>
              <div className="stat-content">
                <h3>Pic de Consommation (24h)</h3>
                <div className="stat-number">{formatPower(energyStats.peak_power_24h)}</div>
                <p>Puissance maximale atteinte</p>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">🏆</div>
              <div className="stat-content">
                <h3>Appareil le plus Énergivore</h3>
                <div className="stat-number">{energyStats.most_consuming_device?.name || '--'}</div>
                <p>Consommation : {formatPower(energyStats.most_consuming_device?.power)}</p>
              </div>
            </div>
          </div>
          
          {/* Graphique de consommation pour le client */}
          <GlobalConsumptionChart 
            data={consumptionData} 
            onTimeRangeChange={setChartTimeRange}
            isLoading={loading}
          />
        </div>
      </div>
    </ClientLayout>
  );
};

export default ClientDashboard;