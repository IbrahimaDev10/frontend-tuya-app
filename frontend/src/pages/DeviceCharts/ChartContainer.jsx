import React, { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import 'chartjs-adapter-date-fns'
import DeviceService from '../../services/deviceService'
import Button from '../../components/Button'
import Input from '../../components/Input'
import './DeviceCharts.css'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
)

const ChartContainer = ({ device, chartType = 'tension', onClose }) => {
  const [chartData, setChartData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [timeRange, setTimeRange] = useState('24h')
  const [customRange, setCustomRange] = useState({
    start: '',
    end: ''
  })
  const [showCustomRange, setShowCustomRange] = useState(false)

  useEffect(() => {
    loadChartData()
  }, [device, chartType, timeRange])

  const getTimeRangeTimestamps = () => {
    const now = new Date()
    let startTime, endTime = now.getTime()

    switch (timeRange) {
      case '1h':
        startTime = now.getTime() - (1 * 60 * 60 * 1000)
        break
      case '6h':
        startTime = now.getTime() - (6 * 60 * 60 * 1000)
        break
      case '24h':
        startTime = now.getTime() - (24 * 60 * 60 * 1000)
        break
      case '7d':
        startTime = now.getTime() - (7 * 24 * 60 * 60 * 1000)
        break
      case '30d':
        startTime = now.getTime() - (30 * 24 * 60 * 60 * 1000)
        break
      case 'custom':
        if (customRange.start && customRange.end) {
          startTime = new Date(customRange.start).getTime()
          endTime = new Date(customRange.end).getTime()
        } else {
          startTime = now.getTime() - (24 * 60 * 60 * 1000)
        }
        break
      default:
        startTime = now.getTime() - (24 * 60 * 60 * 1000)
    }

    return { startTime, endTime }
  }

  const loadChartData = async () => {
    try {
      setLoading(true)
      setError(null)

      const { startTime, endTime } = getTimeRangeTimestamps()
      let response

      switch (chartType) {
        case 'tension':
          response = await DeviceService.obtenirGraphiqueTension(
            device.tuya_device_id,
            startTime,
            endTime
          )
          break
        case 'courant':
          response = await DeviceService.obtenirGraphiqueCourant(
            device.id || device.tuya_device_id,
            startTime,
            endTime
          )
          break
        case 'puissance':
          response = await DeviceService.obtenirGraphiquePuissance(
            device.id || device.tuya_device_id,
            startTime,
            endTime
          )
          break
        default:
          throw new Error('Type de graphique non supporté')
      }

      if (response.data.success) {
        setChartData(formatChartData(response.data, chartType))
      } else {
        setError('Erreur lors du chargement des données')
      }
    } catch (error) {
      console.error('Erreur chargement graphique:', error)
      setError(error.response?.data?.error || 'Erreur lors du chargement')
    } finally {
      setLoading(false)
    }
  }

  const formatChartData = (data, type) => {
    const { donnees_bdd = [], donnees_tuya = [] } = data

    // Vérifier si l'appareil est triphasé en cherchant des données triphasées
    const isTriphase = data.device_info?.type_systeme === 'triphase' || 
                      device.type_systeme === 'triphase' || 
                      donnees_bdd.some(d => d.donnees_triphase) ||
                      donnees_bdd.some(d => d.tension_l1 !== undefined || d.courant_l1 !== undefined || d.puissance_l1 !== undefined)

    const config = getChartConfig(type)

    if (isTriphase && (type === 'tension' || type === 'courant' || type === 'puissance')) {
      // Traitement pour les appareils triphasés
      const phases = ['L1', 'L2', 'L3']
      const phaseColors = {
        L1: { color: 'rgb(255, 99, 132)', backgroundColor: 'rgba(255, 99, 132, 0.2)' },
        L2: { color: 'rgb(54, 162, 235)', backgroundColor: 'rgba(54, 162, 235, 0.2)' },
        L3: { color: 'rgb(75, 192, 192)', backgroundColor: 'rgba(75, 192, 192, 0.2)' }
      }

      // Créer un dataset pour chaque phase
      const datasets = phases.map(phase => {
        // Extraire les données pour cette phase
        const phaseData = donnees_bdd.map(d => {
          let value = null
          const phaseLower = phase.toLowerCase()
          
          if (type === 'tension') {
            value = d[`tension_${phaseLower}`] || 
                   (d.donnees_triphase?.tensions && d.donnees_triphase.tensions[phase])
          } else if (type === 'courant') {
            value = d[`courant_${phaseLower}`] || 
                   (d.donnees_triphase?.courants && d.donnees_triphase.courants[phase])
          } else if (type === 'puissance') {
            value = d[`puissance_${phaseLower}`] || 
                   (d.donnees_triphase?.puissances?.active && d.donnees_triphase.puissances.active[phase])
          }
          
          // Convertir les valeurs null ou undefined en 0 si nécessaire
          // Mais garder null/undefined pour les points qui n'ont pas de données du tout
          return {
            x: new Date(d.timestamp || d.horodatage),
            y: value !== null && value !== undefined ? parseFloat(value) : null
          }
        }).filter(d => d.x) // Filtrer uniquement les points sans horodatage valide

        return {
          label: `${config.label} ${phase}`,
          data: phaseData,
          borderColor: phaseColors[phase].color,
          backgroundColor: phaseColors[phase].backgroundColor,
          tension: 0.4,
          pointRadius: 2,
          pointHoverRadius: 4,
          borderWidth: 2,
          cubicInterpolationMode: 'monotone'
        }
      })

      return { datasets }
    } else {
      // Traitement standard pour les appareils monophasés
      const bddData = donnees_bdd.map(d => ({
        x: new Date(d.timestamp || d.horodatage),
        y: d.value !== null && d.value !== undefined ? parseFloat(d.value) : null
      })).filter(d => d.x) // Filtrer uniquement les points sans horodatage valide

      const tuyaData = donnees_tuya.map(d => ({
        x: new Date(d.timestamp || d.horodatage),
        y: d.value !== null && d.value !== undefined ? parseFloat(d.value) : null
      })).filter(d => d.x) // Filtrer uniquement les points sans horodatage valide

      return {
        datasets: [
          {
            label: `${config.label} (BDD)`,
            data: bddData,
            borderColor: config.color,
            backgroundColor: config.backgroundColor,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 4,
            borderWidth: 2,
            cubicInterpolationMode: 'monotone'
          },
          ...(tuyaData.length > 0 ? [{
            label: `${config.label} (Tuya)`,
            data: tuyaData,
            borderColor: config.secondaryColor,
            backgroundColor: config.secondaryBackgroundColor,
            tension: 0.4,
            pointRadius: 2,
            pointHoverRadius: 4,
            borderWidth: 2,
            borderDash: [5, 5],
            cubicInterpolationMode: 'monotone'
          }] : [])
        ]
      }
    }
  }

  const getChartConfig = (type) => {
    const configs = {
      tension: {
        label: 'Tension',
        unit: 'V',
        color: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        secondaryColor: 'rgb(255, 159, 164)',
        secondaryBackgroundColor: 'rgba(255, 159, 164, 0.2)'
      },
      courant: {
        label: 'Courant',
        unit: 'A',
        color: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        secondaryColor: 'rgb(116, 185, 255)',
        secondaryBackgroundColor: 'rgba(116, 185, 255, 0.2)'
      },
      puissance: {
        label: 'Puissance',
        unit: 'W',
        color: 'rgb(255, 205, 86)',
        backgroundColor: 'rgba(255, 205, 86, 0.2)',
        secondaryColor: 'rgb(255, 219, 128)',
        secondaryBackgroundColor: 'rgba(255, 219, 128, 0.2)'
      }
    }
    return configs[type] || configs.tension
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: `${getChartConfig(chartType).label} - ${device.nom_appareil}`,
        font: {
          size: 16
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function(context) {
            const config = getChartConfig(chartType)
            return `${context.dataset.label}: ${context.parsed.y.toFixed(2)} ${config.unit}`
          },
          title: function(tooltipItems) {
            return new Date(tooltipItems[0].parsed.x).toLocaleString('fr-FR')
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time',
        time: {
          displayFormats: {
            minute: 'HH:mm',
            hour: 'HH:mm',
            day: 'dd/MM'
          }
        },
        title: {
          display: true,
          text: 'Temps'
        }
      },
      y: {
        title: {
          display: true,
          text: `${getChartConfig(chartType).label} (${getChartConfig(chartType).unit})`
        },
        beginAtZero: true,
        suggestedMin: 0
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    }
  }

  const handleCustomRangeApply = () => {
    if (customRange.start && customRange.end) {
      setTimeRange('custom')
      loadChartData()
    }
  }

  return (
    <div className="chart-container">
      <div className="chart-header">
        <h3>
          {getChartConfig(chartType).label} - {device.nom_appareil}
        </h3>
        
      </div>

      <div className="chart-controls">
        <div className="time-range-controls">
          <label>Période :</label>
          <div className="time-range-buttons">
            {['1h', '6h', '24h', '7d', '30d', 'custom'].map(range => (
              <Button
                key={range}
                variant={timeRange === range ? 'primary' : 'outline'}
                size="small"
                onClick={() => {
                  setTimeRange(range)
                  if (range === 'custom') {
                    setShowCustomRange(true)
                  } else {
                    setShowCustomRange(false)
                  }
                }}
              >
                {range === 'custom' ? 'Personnalisé' : range.toUpperCase()}
              </Button>
            ))}
          </div>
        </div>

        {showCustomRange && (
          <div className="custom-range-controls">
            <div className="custom-range-inputs">
              <Input
                type="datetime-local"
                value={customRange.start}
                onChange={(e) => setCustomRange(prev => ({ ...prev, start: e.target.value }))}
                label="Début"
              />
              <Input
                type="datetime-local"
                value={customRange.end}
                onChange={(e) => setCustomRange(prev => ({ ...prev, end: e.target.value }))}
                label="Fin"
              />
              <Button
                variant="primary"
                onClick={handleCustomRangeApply}
                disabled={!customRange.start || !customRange.end}
              >
                Appliquer
              </Button>
            </div>
          </div>
        )}

        <div className="chart-actions">
          <Button
            variant="outline"
            size="small"
            onClick={loadChartData}
            loading={loading}
          >
            🔄 Actualiser
          </Button>
          <Button
            variant="outline"
            size="small"
            onClick={() => {
              // Export des données (CSV)
              exportToCSV()
            }}
          >
            📊 Exporter CSV
          </Button>
        </div>
      </div>

      <div className="chart-content">
        {loading ? (
          <div className="chart-loading">
            <div className="loading-spinner"></div>
            <p>Chargement des données...</p>
          </div>
        ) : error ? (
          <div className="chart-error">
            <div className="error-icon">⚠️</div>
            <h4>Erreur de chargement</h4>
            <p>{error}</p>
            <Button variant="primary" onClick={loadChartData}>
              Réessayer
            </Button>
          </div>
        ) : chartData && chartData.datasets[0].data.length > 0 ? (
          <div className="chart-wrapper">
            <Line data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div className="chart-empty">
            <div className="empty-icon">📈</div>
            <h4>Aucune donnée</h4>
            <p>Aucune donnée disponible pour cette période.</p>
            <Button variant="outline" onClick={loadChartData}>
              Actualiser
            </Button>
          </div>
        )}
      </div>

      {chartData && (
        <div className="chart-stats">
          <div className="data-summary">
            <span>
              📊 {chartData.datasets.reduce((total, dataset) => total + dataset.data.length, 0)} points de données
            </span>
            <span>
              ⏱️ Période: {new Date(getTimeRangeTimestamps().startTime).toLocaleString('fr-FR')} - {new Date(getTimeRangeTimestamps().endTime).toLocaleString('fr-FR')}
            </span>
          </div>
        </div>
      )}
    </div>
  )

function exportToCSV() {
  if (!chartData || chartData.datasets.length === 0 || chartData.datasets.every(d => d.data.length === 0)) {
    alert("Aucune donnée à exporter.");
    return;
  }

  const config = getChartConfig(chartType);
  const isTriphase = chartData.datasets.length > 1 && chartData.datasets.some(d => d.label.includes('L1'));

  let csvContent = '';
  let dataRows = new Map(); // Utiliser une Map pour regrouper les données par timestamp

  if (isTriphase) {
    // --- CAS TRIPHASÉ ---
    const headers = ['Timestamp', `Valeur L1 (${config.unit})`, `Valeur L2 (${config.unit})`, `Valeur L3 (${config.unit})`];
    csvContent += headers.join(',') + '\n';

    // Parcourir chaque dataset (L1, L2, L3)
    chartData.datasets.forEach(dataset => {
      const phaseLabel = dataset.label.includes('L1') ? 'L1' : dataset.label.includes('L2') ? 'L2' : 'L3';
      
      dataset.data.forEach(point => {
        const timestamp = point.x.toISOString();
        if (!dataRows.has(timestamp)) {
          // Initialiser la ligne avec des valeurs vides
          dataRows.set(timestamp, { L1: '', L2: '', L3: '' });
        }
        // Remplir la valeur pour la phase correspondante
        dataRows.get(timestamp)[phaseLabel] = point.y !== null ? point.y.toFixed(3) : '';
      });
    });

    // Convertir la Map en lignes CSV
    const sortedTimestamps = Array.from(dataRows.keys()).sort();
    sortedTimestamps.forEach(timestamp => {
      const rowData = dataRows.get(timestamp);
      csvContent += `${timestamp},${rowData.L1},${rowData.L2},${rowData.L3}\n`;
    });

  } else {
    // --- CAS MONOPHASÉ ---
    const headers = ['Timestamp', `Valeur (${config.unit})`, 'Source'];
    csvContent += headers.join(',') + '\n';

    chartData.datasets.forEach(dataset => {
      const source = dataset.label; // ex: "Tension (BDD)"
      dataset.data.forEach(point => {
        const timestamp = point.x.toISOString();
        const value = point.y !== null ? point.y.toFixed(3) : '';
        csvContent += `${timestamp},${value},"${source}"\n`;
      });
    });
  }

  // Création et téléchargement du fichier
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', `${device.nom_appareil}_${chartType}_${timeRange}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}
}

export default ChartContainer
