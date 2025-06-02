import React from 'react'
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export default function DeviceLatestStatus() {
    const { id } = useParams();

    const fetchDeviceLatestStatus = async () => {
      const jwt=localStorage.getItem('jwt');
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/device-status/${id}` , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      });
        return response.data;
      };

      const { data, isLoading, error } = useQuery({
        queryKey: ['device-the-latest-status', id],
        queryFn: fetchDeviceLatestStatus,
        //refetchInterval: 5000,
       
      });

      if (isLoading) return <div>Chargement...</div>;
      if (error) return <div>Erreur : {error.message}</div>;
      if (!data || !data.success || !data.devices.length) return <div>Aucune donnée disponible.</div>;
    
      const statusList = data.devices[0].status;
  return (
    <div className="card shadow menu border-0 p-3 mt-4">
            <div className="row">
        
        {statusList.map((item, index) => {
          let label = item.code;
          let value = item.value;

          // Formatage dynamique
          switch (item.code) {
            case 'cur_voltage':
              value = `${value / 100} V`;
              label = 'Tension';
              break;
            case 'cur_current':
              value = `${value / 1000} A`;
              label = 'Courant';
              break;
            case 'cur_power':
              value = `${value} W`;
              label = 'Puissance';
              break;
            case 'add_ele':
              value = `${value} kWh`;
              label = 'Consommation';
              break;
            case 'switch_1':
              value = value ? 'ON' : 'OFF';
              label = 'Interrupteur';
              break;
              /*
            case 'countdown_1':
              value = `${value} sec`;
              label = 'Compte à rebours';
              break;
            default:
              label = item.code;
              value= item.value;
              */
          }

          return (
            <div  key={index} className="col-lg-3">
                    <div className='result_produit'>
        
              <span>{label} :</span>
              <span>{value} :</span>
            </div>
            </div>
          );
        })}
      

            </div>
                </div>
  )
}
