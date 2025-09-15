// src/components/DeviceRealtimeCard.js (ou le chemin où il se trouve)

import React from "react";
import { useDeviceRealtime } from "../../store/realtimeContext";

// Une petite fonction utilitaire pour formater les valeurs
const formatMetric = (value, unit) => {
  if (value == null) return <span className="metric-value-na">—</span>;
  return (
    <>
      <span className="metric-value">{value}</span>
      <span className="metric-unit">{unit}</span>
    </>
  );
};

export default function DeviceRealtimeCard({ device }) {
  // On récupère les données temps réel via le hook
  const rt = useDeviceRealtime(device?.tuya_device_id);

  // Si on n'a pas d'objet device de base, on ne peut rien afficher
  if (!device?.tuya_device_id) {
    return (
      <div className="rt-card-placeholder">
        Informations sur l'appareil non disponibles.
      </div>
    );
  }

  // On détermine le type et la date, avec fallback sur les données initiales
  const type = rt?.type_systeme || device?.type_systeme || "monophase";
  const isTri = type === "triphase";
  const date = rt?.horodatage ? new Date(rt.horodatage) : null;

  // Pour le monophasé, on utilise le fallback pour un affichage immédiat
  const tension = rt?.tension ?? device?.tension;
  const courant = rt?.courant ?? device?.courant;
  const puissance = rt?.puissance ?? device?.puissance;

  return (
    // On utilise des classes BEM-like (Block__Element--Modifier) pour une meilleure clarté
    <div className="rt-card">
      <div className="rt-card__header">
        <div className="rt-card__title">
          {isTri ? "Système Triphasé" : "Système Monophasé"}
        </div>
        <div className={`rt-card__live-indicator ${rt ? 'active' : ''}`}>
          ● LIVE
        </div>
      </div>
      
      <div className="rt-card__timestamp">
        {date ? `Dernière mise à jour: ${date.toLocaleTimeString('fr-FR')}` : "En attente de données temps réel..."}
      </div>

      <div className="rt-card__body">
        {isTri ? (
          // --- Affichage Triphasé ---
          <div className="rt-metrics-grid rt-metrics-grid--triphase">
            {/* Phase L1 */}
            <div className="rt-metric rt-metric--phase">
              <div className="rt-metric__label">Phase L1</div>
              <div className="rt-metric__values">
                {formatMetric(rt?.tension_l1, "V")} | {formatMetric(rt?.courant_l1, "A")} | {formatMetric(rt?.puissance_l1, "W")}
              </div>
            </div>
            {/* Phase L2 */}
            <div className="rt-metric rt-metric--phase">
              <div className="rt-metric__label">Phase L2</div>
              <div className="rt-metric__values">
                {formatMetric(rt?.tension_l2, "V")} | {formatMetric(rt?.courant_l2, "A")} | {formatMetric(rt?.puissance_l2, "W")}
              </div>
            </div>
            {/* Phase L3 */}
            <div className="rt-metric rt-metric--phase">
              <div className="rt-metric__label">Phase L3</div>
              <div className="rt-metric__values">
                {formatMetric(rt?.tension_l3, "V")} | {formatMetric(rt?.courant_l3, "A")} | {formatMetric(rt?.puissance_l3, "W")}
              </div>
            </div>
            {/* Puissance Totale */}
            <div className="rt-metric rt-metric--total">
              <div className="rt-metric__label">Puissance Totale</div>
              <div className="rt-metric__values">
                {formatMetric(rt?.puissance_totale, "W")}
              </div>
            </div>
          </div>
        ) : (
          // --- Affichage Monophasé ---
          <div className="rt-metrics-grid">
            <div className="rt-metric">
              <div className="rt-metric__label">Tension</div>
              <div className="rt-metric__values">{formatMetric(tension, "V")}</div>
            </div>
            <div className="rt-metric">
              <div className="rt-metric__label">Courant</div>
              <div className="rt-metric__values">{formatMetric(courant, "A")}</div>
            </div>
            <div className="rt-metric">
              <div className="rt-metric__label">Puissance</div>
              <div className="rt-metric__values">{formatMetric(puissance, "W")}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
