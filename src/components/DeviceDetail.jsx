import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import axios from 'axios';
import DashboardContent from './dashboard/DashboardContent';
import { FaHome } from "react-icons/fa";
import { FaChartLine } from "react-icons/fa";
import { IoSettings } from "react-icons/io5";
import DeviceDetailMenu from './layout/DeviceDetailMenu';
import DeviceCommand from './DeviceCommand';
import DeviceLatestStatus from './DeviceLatestStatus';

export default function DeviceDetail() {
  const { id } = useParams();  // récupère l'id dans l'URL
  const [device, setDevice] = useState([]);



  useEffect(() => {
    // Exemple : récupérer les infos du device depuis ton serveur
    const jwt=localStorage.getItem('jwt');
    axios.get(`${import.meta.env.VITE_API_URL}/get-device-name/${id}` , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      })
      .then((res) => {
        const resultdata=res.data.device_name;
        setDevice(resultdata);
        console.log(resultdata);
        
      })
      .catch((error) => {
        console.error(error);
      });
  }, [id]); 
{/*
  if (!device) {
    return <div>Chargement...</div>;
  } */}

  return (
    <>
    <DashboardContent />
    <div className="card shadow debut border-0 p-3 mt-4">
        <center>
    <h2>Détails de l'appareil {device.map((item)=>( <span key={item.id}> {item.name }</span>  ))}</h2>
    </center>
    </div>
      <DeviceDetailMenu />
      {/*
        <div className="card shadow menu border-0 p-3 mt-4">
            <div className="row">
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Etat de changement</span>
                        <span>ON</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Total Ele</span>
                        <span>132.500KWh</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Bill</span>
                        <span>12383.200</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Voltage</span>
                        <span>220.13V</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Current</span>
                        <span>0.334A</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Power</span>
                        <span>41.47W</span>
                    </div>
                </div>
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Frequency</span>
                        <span>50.03Hz</span>
                    </div>
                </div>  
                <div className="col-lg-3">
                    <div className='result_produit'>
                        <span>Factor</span>
                        <span>0.57PF</span>
                    </div>
                </div>
            </div>
        

      

    </div> */}
    <DeviceLatestStatus />
    <DeviceCommand />
    </>
  );
}
