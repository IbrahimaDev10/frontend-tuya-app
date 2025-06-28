import React, { useState } from 'react'
import ChartContainer from './ChartContainer'
import Button from '../../components/Button'
import './DeviceCharts.css'

const MultiChartView = ({ device, onClose }) => {
  const [activeCharts, setActiveCharts] = useState(['tension'])
  const [viewMode, setViewMode] = useState('tabs') // 'tabs' ou 'grid'

  const chartTypes = [
    { key: 'tension', label: 'Tension (V)', icon: '⚡', color: '#ff6384' },
    { key: 'courant', label: 'Courant (A)', icon: '🔌', color: '#36a2eb' },
    { key: 'puissance', label: 'Puissance (W)', icon: '💡', color: '#ffcd56' }
  ]

  const toggleChart = (chartType) => {
    setActiveCharts(prev => 
      prev.includes(chartType)
        ? prev.filter(type => type !== chartType)
        : [...prev, chartType]
    )
  }

  const showAllCharts = () => {
    setActiveCharts(chartTypes.map(ct => ct.key))
  }

  const hideAllCharts = () => {
    setActiveCharts([])
  }

  return (
    <div className="multi-chart-view">
      <div className="multi-chart-header">
        <div className="chart-device-info">
          <h2>📊 Graphiques - {device.nom_appareil}</h2>
          <p>ID: {device.tuya_device_id}</p>
        </div>
        <Button variant="outline" onClick={onClose}>
          ✕ Fermer
        </Button>
      </div>

      <div className="chart-controls-panel">
        <div className="chart-selector">
          <h4>Graphiques à afficher :</h4>
          <div className="chart-toggle-buttons">
            {chartTypes.map(chartType => (
              <Button
                key={chartType.key}
                variant={activeCharts.includes(chartType.key) ? 'primary' : 'outline'}
                size="small"
                onClick={() => toggleChart(chartType.key)}
                style={activeCharts.includes(chartType.key) ? {
                  backgroundColor: chartType.color,
                  borderColor: chartType.color
                } : {}}
              >
                {chartType.icon} {chartType.label}
              </Button>
            ))}
          </div>
          
          <div className="chart-bulk-actions">
            <Button variant="outline" size="small" onClick={showAllCharts}>
              Tout afficher
            </Button>
            <Button variant="outline" size="small" onClick={hideAllCharts}>
              Tout masquer
            </Button>
          </div>
        </div>

        <div className="view-mode-selector">
          <h4>Mode d'affichage :</h4>
          <div className="view-mode-buttons">
            <Button
              variant={viewMode === 'tabs' ? 'primary' : 'outline'}
              size="small"
              onClick={() => setViewMode('tabs')}
            >
              📑 Onglets
            </Button>
            <Button
              variant={viewMode === 'grid' ? 'primary' : 'outline'}
              size="small"
              onClick={() => setViewMode('grid')}
            >
              ⊞ Grille
            </Button>
          </div>
        </div>
      </div>

      {activeCharts.length === 0 ? (
        <div className="no-charts-selected">
          <div className="empty-icon">📊</div>
          <h3>Aucun graphique sélectionné</h3>
          <p>Sélectionnez un ou plusieurs types de graphiques à afficher.</p>
          <Button variant="primary" onClick={showAllCharts}>
            Afficher tous les graphiques
          </Button>
        </div>
      ) : viewMode === 'tabs' ? (
        <TabsView 
          device={device} 
          activeCharts={activeCharts} 
          chartTypes={chartTypes}
        />
      ) : (
        <GridView 
          device={device} 
          activeCharts={activeCharts} 
          chartTypes={chartTypes}
        />
      )}
    </div>
  )
}

// Composant vue en onglets
const TabsView = ({ device, activeCharts, chartTypes }) => {
  const [activeTab, setActiveTab] = useState(activeCharts[0])

  React.useEffect(() => {
    if (!activeCharts.includes(activeTab)) {
      setActiveTab(activeCharts[0])
    }
  }, [activeCharts, activeTab])

  return (
    <div className="charts-tabs-view">
      <div className="chart-tabs">
        {activeCharts.map(chartType => {
          const config = chartTypes.find(ct => ct.key === chartType)
          return (
            <button
              key={chartType}
              className={`chart-tab ${activeTab === chartType ? 'active' : ''}`}
              onClick={() => setActiveTab(chartType)}
              style={activeTab === chartType ? {
                borderBottomColor: config.color
              } : {}}
            >
              {config.icon} {config.label}
            </button>
          )
        })}
      </div>

      <div className="chart-tab-content">
        {activeTab && (
          <ChartContainer
            device={device}
            chartType={activeTab}
            onClose={() => {}}
          />
        )}
      </div>
    </div>
  )
}

// Composant vue en grille
const GridView = ({ device, activeCharts, chartTypes }) => {
  return (
    <div className={`charts-grid-view grid-${activeCharts.length}`}>
      {activeCharts.map(chartType => (
        <div key={chartType} className="chart-grid-item">
          <ChartContainer
            device={device}
            chartType={chartType}
            onClose={() => {}}
          />
        </div>
      ))}
    </div>
  )
}

export default MultiChartView
