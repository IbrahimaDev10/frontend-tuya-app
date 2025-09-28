import React, { useState, useEffect } from 'react';
import SuperAdminLayout from '../layouts/SuperAdminLayout';
import { useAuth } from '../store/authContext';
import DeviceService from '../services/deviceService';
// On importe uniquement le composant pour le graphique
import GlobalConsumptionChart from './GlobalConsumptionChart';

import './Dashboard.css'; // Le CSS qui va styliser cette nouvelle mise en page

// Fonction pour formater les grands nombres (ex: 12500 W -> 12.5 kW)
const formatPower = (watts) => {
  if (watts == null || isNaN(watts)) return '--';
  if (watts < 1000) return `${Math.round(watts)} W`;
  return `${(watts / 1000).toFixed(1)} kW`;
};

const SuperAdminDashboard = () => {
  const { user } = useAuth();
  const [consumptionData, setConsumptionData] = useState([]);
  const [energyStats, setEnergyStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [chartTimeRange, setChartTimeRange] = useState('24h');

   useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // --- ✅ APPEL RÉEL AUX STATISTIQUES ---
        const statsResponse = await DeviceService.obtenirStatsDashboard();
        if (statsResponse.data.success) {
          setEnergyStats(statsResponse.data.stats);
        }

        // --- ✅ APPEL RÉEL POUR LE GRAPHIQUE ---
        // On peut créer une route dédiée ou utiliser celle existante
        // Ici, utilisons une route fictive pour l'exemple, à créer sur le même modèle
        // que les graphiques par appareil.
        const chartResponse = await DeviceService.obtenirGraphiqueGlobalPuissance( // ✅ Utiliser la nouvelle méthode
            Date.now() - (chartTimeRange === '24h' ? 24 : 7 * 24) * 3600 * 1000,
            Date.now(),
            chartTimeRange === '24h' ? 'hourly' : 'daily'
        );
        
        if (chartResponse.data.success) {
            const formattedData = chartResponse.data.donnees_bdd.map(d => ({
                time: d.timestamp, // Le backend renvoie 'timestamp'
                value: d.value    // Le backend renvoie 'value'
            }));
            setConsumptionData(formattedData);
        }
// ...

      } catch (error) {
        console.error("Erreur de chargement du dashboard", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [chartTimeRange]);

  return (
    <SuperAdminLayout>
      <div className="dashboard">
        <div className="dashboard-header">
          <h1>Tableau de Bord Énergétique</h1>
          <p>Vue d'ensemble de la consommation du système.</p>
        </div>

        <div className="dashboard-content">
          {/* Carte de bienvenue (conservée) */}
          <div className="welcome-card">
            <div className="welcome-icon">⚡</div>
            <div className="welcome-text">
              <h2>Bienvenue, {user?.nom_complet || 'Super Administrateur'}</h2>
              <p>
                Voici un aperçu en temps réel de la consommation énergétique de l'ensemble de vos sites.
              </p>
            </div>
          </div>

          {/* NOUVELLES STAT-CARDS DÉDIÉES À L'ÉNERGIE */}
          <div className="dashboard-stats">
            <div className="stat-card">
              <div className="stat-icon">💡</div>
              <div className="stat-content">
                <h3>Consommation Actuelle</h3>
                <div className="stat-number">{formatPower(energyStats.current_total_power)}</div>
                <p>Puissance totale instantanée</p>
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
                <h3>Site le plus Énergivore</h3>
                <div className="stat-number">{energyStats.most_consuming_site?.name || '--'}</div>
                <p>Consommation : {formatPower(energyStats.most_consuming_site?.power)}</p>
              </div>
            </div>
          </div>
          
          {/* GRAPHIQUE À LA PLACE DES ALERTES */}
          <GlobalConsumptionChart 
            data={consumptionData} 
            onTimeRangeChange={setChartTimeRange}
            isLoading={loading}
          />
        </div>
      </div>
    </SuperAdminLayout>
  );
};

export default SuperAdminDashboard;
