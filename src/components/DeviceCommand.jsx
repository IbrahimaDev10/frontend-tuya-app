import React, {useEffect, useState} from 'react'
import { FaPowerOff } from "react-icons/fa";
import { LuTimerReset } from "react-icons/lu";
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

export default function DeviceCommand() {
    const { id } = useParams();
      const [status, setStatus] = useState(null);
      const [erreur, setErreur] = useState("");


      const fetchDeviceStatus = async () => {

       const jwt=localStorage.getItem('jwt');
        const response = await axios.get(`${import.meta.env.VITE_API_URL}/device-status/${id}` , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      } );
        return response.data;
      };

      const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['device-status', id],
        queryFn: fetchDeviceStatus,
        //refetchInterval: 3000,
       
      });

      if (isLoading) return <p>Chargement...</p>;
  if (error || !data?.success) return <p>Erreur lors de la récupération du statut</p>;

  const statusList = data.devices?.[0]?.status || [];
  const switchStatus = statusList.find(item => item.code === 'switch_1');

    const handleCommand = async (value) => {
      const jwt=localStorage.getItem('jwt');
    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/toggle-device`  , {
        mydevice_id: id,  
        code: "switch_1",
        value: value,  // true = allumer, false = éteindre
      } , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      } );

      if (response.data.success) {
        setStatus(`Appareil ${value ? "allumé" : "éteint"} avec succès.`);
        setErreur("");
        refetch();
        console.log(!switchStatus?.value)
      } else {
        setErreur("Échec de la commande.");
      }
    } catch (err) {
      console.erreur(err);
      setErreur("Erreur lors de la communication avec le serveur.");
    }
  };

  return (
    <div className="card shadow  border-0 p-3 mt-4">
        <div className='row d-flex align-items-center'>
            <div className='col-lg-4'>
                <div className='power'>
                <LuTimerReset />
                </div>
            </div>
            <div className='col-lg-4'> 
            <div className='power'>
            <FaPowerOff className={switchStatus?.value ? 'power_action' : 'power_noaction'} onClick={() => handleCommand(!switchStatus?.value)
              
            } />
                {switchStatus?.value ? 'Allumée' : 'Éteinte'}
                <p>Lampe :{id} {String(switchStatus?.value)}</p>
              
                </div>
            </div>
            <div className='col-lg-4'> 
            <div className='power'>
                <LuTimerReset />

                </div>
            </div>
        </div>

    </div>
  )
}
