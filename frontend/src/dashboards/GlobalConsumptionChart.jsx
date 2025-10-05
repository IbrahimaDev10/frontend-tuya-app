import React, { useState } from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler } from 'chart.js';
import 'chartjs-adapter-date-fns';
import Button from '../components/Button'; // Assurez-vous que le chemin est correct

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler);

const GlobalConsumptionChart = ({ data, onTimeRangeChange, isLoading }) => {
  const [activeRange, setActiveRange] = useState('24h');

  const handleTimeRangeClick = (range) => {
    setActiveRange(range);
    if (onTimeRangeChange) {
      onTimeRangeChange(range);
    }
  };

  const chartData = {
    labels: data.map(d => new Date(d.time)),
    datasets: [
      {
        label: 'Consommation Totale (W)',
        data: data.map(d => d.value),
        fill: true,
        backgroundColor: 'rgba(0, 123, 255, 0.2)',
        borderColor: '#007bff',
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { 
        type: 'time', 
        time: { 
          unit: activeRange === '24h' ? 'hour' : 'day',
          displayFormats: {
            hour: 'HH:mm',
            day: 'EEEE' // Affiche le jour de la semaine en toutes lettres (Lundi, Mardi, etc.)
          },
          tooltipFormat: activeRange === '24h' ? 'dd/MM/yyyy HH:mm' : 'EEEE dd/MM/yyyy'
        }, 
        grid: { display: false } 
      },
      y: { beginAtZero: true, title: { display: true, text: 'Puissance (W)' } },
    },
    plugins: { 
      legend: { display: false }, 
      tooltip: { 
        mode: 'index', 
        intersect: false,
        callbacks: {
          title: (context) => {
            const date = new Date(context[0].parsed.x);
            if (activeRange === '7d') {
              // Format pour afficher "Lundi 01/01/2023" en français
              const options = { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' };
              return date.toLocaleDateString('fr-FR', options);
            }
            return date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
          }
        }
      }
    },
    interaction: { intersect: false, mode: 'index' },
  };

  return (
    <div className="dashboard-section">
      <div className="section-header">
        <h2>Consommation Globale</h2>
        <div className="time-range-buttons">
          <Button variant={activeRange === '24h' ? 'primary' : 'outline'} size="small" onClick={() => handleTimeRangeClick('24h')}>24h</Button>
          <Button variant={activeRange === '7d' ? 'primary' : 'outline'} size="small" onClick={() => handleTimeRangeClick('7d')}>7j</Button>
        </div>
      </div>
      <div className="chart-wrapper">
        {isLoading ? (
          <div className="loading-overlay"><span>Chargement des données...</span></div>
        ) : (
          <Line data={chartData} options={chartOptions} />
        )}
      </div>
    </div>
  );
};

export default GlobalConsumptionChart;
