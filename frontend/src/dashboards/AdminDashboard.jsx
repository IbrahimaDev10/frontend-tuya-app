import React, { useState, useEffect } from 'react';
import AdminLayout from '../layouts/AdminLayout';
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

const AdminDashboard = () => {
  const { user } = useAuth();
  const [consumptionData, setConsumptionData] = useState([]);
  const [energyStats, setEnergyStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [chartTimeRange, setChartTimeRange] = useState('24h');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Récupération des statistiques pour l'admin (limité à sa structure)
        const statsResponse = await DeviceService.obtenirStatsDashboardAdmin();
        if (statsResponse.data.success) {
          setEnergyStats(statsResponse.data.stats);
        }

        // Récupération des données de consommation pour le graphique
        const chartResponse = await DeviceService.obtenirGraphiqueStructurePuissance(
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
        console.error("Erreur de chargement du dashboard admin", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [chartTimeRange]);

  return (
    <AdminLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de bord Énergétique</h1>
          <p>Gestion de votre structure</p>
        </div>

        <div className="dashboard-content">
          <div className="welcome-card">
            <div className="welcome-icon">🛠️</div>
            <div className="welcome-text">
              <h2>Bienvenue, {user?.nom_complet}</h2>
              <p>
                Vous pouvez gérer les clients de votre structure, 
                suivre l'inventaire des appareils et planifier la maintenance.
              </p>
            </div>
          </div>

          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">💡</div>
              <div className="stat-content">
                <h3>Consommation Actuelle</h3>
                <div className="stat-number">{formatPower(energyStats.current_total_power)}</div>
                <p>Puissance totale de la structure</p>
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

         
          </div>
          
          {/* Graphique de consommation pour la structure */}
          <GlobalConsumptionChart 
            data={consumptionData} 
            onTimeRangeChange={setChartTimeRange}
            isLoading={loading}
          />
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminDashboard;