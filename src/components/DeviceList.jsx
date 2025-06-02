import React, { useState, useEffect, useContext } from "react";
import axios from "axios";
import { Link, useNavigate } from "react-router-dom";
import DashboardContent from "./dashboard/DashboardContent";
import { MyContext } from "../App";
import "../deviceList.css"

export default function DeviceList() {
  const [devices, setDevices] = useState([]);
  const [error, setError] = useState("");

   const context=useContext(MyContext);
   

  useEffect(() => {
    const fetchDevices = async () => {
      const jwt=localStorage.getItem("jwt");
          const payload = JSON.parse(atob(jwt.split('.')[1]));
          const isExpired = Date.now() >= payload.exp * 1000;
      try {
        if (!isExpired) {

          console.log(payload);
          console.log(isExpired, 'testtt');
          const res = await axios.get(`${import.meta.env.VITE_API_URL}/get_devices` , {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      });
        if (res.data.success) {
          setDevices(res.data.devices);
          setError("");
          console.res(jwt);
        } else {
          setError("Échec de récupération des appareils.");
        }
      }
  if (isExpired) {
    localStorage.removeItem("jwt");
    navigate("/connexion");
    return;
  }
      
      } catch (err) {
        setError("Erreur de connexion au serveur.");
      }
    };

    fetchDevices();
  }, []);
  
  const navigate=useNavigate();

  return (
    <>
    <DashboardContent />
    <div className="card shadow border-0 p-3 mt-4 cardDevice">
    
    <div className="DeviceList ">
      <div className="titleTableDevice">
       <h3 className="text-bg">Liste des produits</h3>
       </div>
      <div className="table">
        <table className="table table-responsive table-bordered table-striped">
        <thead>
          <tr className="entete_table">
            <th>Nom</th><th>Icone</th><th>Id</th><th>Produit</th><th>Categorie</th><th>Status</th>
          </tr>
        </thead>
        <tbody >

       
        {devices.map((d) => (
          <tr key={d.id} className="body_table">
            <td><Link className="deviceLink" to={`/device/${d.id}`} onClick={()=>{context.setIsClicked(1)}} >{d.name}</Link></td>
            <td><img src={`https://images.tuyaeu.com/${d.icon}`} style={{ width: "50px", height: "40px", objectFit: "cover" }} /></td>
            <td>{d.id}</td>
            <td>{d.productName}</td>
            <td>{d.category}</td>
            <td>{d.isOnline ? 'en ligne': 'NON'}</td>
            

           </tr>

          
        ) ) }
         </tbody>

        </table>
      </div>
      {/*
      <h2>Mes appareils IOT (Internet Of Things)</h2>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <ul>
        {devices.map((d) => (
          <li key={d.id}>
            <Link className="deviceLink" to={`/device/${d.id}`}>
            <img src={`https://images.tuyaeu.com/${d.icon}`} style={{ width: "50px", height: "40px", objectFit: "cover" }} />
           <span> <strong>{d.name}</strong> – ID : {d.id} </span> 
           </Link>
          </li>
        ))}
      </ul>
      */}
    </div>
    </div>
    </>
  );
}
