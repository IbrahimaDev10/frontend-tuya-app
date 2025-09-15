// src/components/Dashboard/ConsumptionBySite.js

import React from 'react';

// Fonction pour formater les grands nombres (ex: 12500 W -> 12.5 kW)
const formatPower = (watts) => {
  if (watts == null) return '--';
  if (watts < 1000) return `${Math.round(watts)} W`;
  return `${(watts / 1000).toFixed(1)} kW`;
};

const ConsumptionBySite = ({ data, isLoading }) => {
  return (
    <div className="dashboard-section">
      <div className="section-header">
        <h2>Consommation Actuelle par Site</h2>
      </div>
      <div className="site-consumption-grid">
        {isLoading ? (
          <p>Chargement...</p>
        ) : (
          data.map(site => (
            <div key={site.id} className="site-card">
              <div className="site-card-header">
                <span className="site-icon">🏢</span>
                <h3>{site.nom_site}</h3>
              </div>
              <div className="site-card-body">
                <div className="site-power">{formatPower(site.total_power)}</div>
                <div className="site-device-count">{site.device_count} appareils en ligne</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ConsumptionBySite;
