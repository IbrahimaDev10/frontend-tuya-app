import React, { useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";

export default function DeviceControl() {
  const {id}=useParams();
  const [status, setStatus] = useState(null);
  const [errors, setErrors] = useState("");

  const handleCommand = async (value) => {
    try {
      const response = await axios.post("http://localhost:5000/toggle-device", {
        device_id: "vdevo174456632030882",  // remplace par ton vrai ID
        code: "switch_1",
        value: value,  // true = allumer, false = éteindre
      });

      if (response.data.success) {
        setStatus(`Appareil ${value ? "allumé" : "éteint"} avec succès.`);
        setErrors("");
      } else {
        setErrors("Échec de la commande.");
      }
    } catch (err) {
      console.errors(err);
      setErrors("Erreur lors de la communication avec le serveur.");
    }
  };

  return (
    <div>
      <h3>Contrôle de l'appareil Tuya</h3>
      <button className="bouton_allumer" onClick={() => handleCommand(true)}>Allumer{id}</button>
      <button className="bouton_eteindre" onClick={() => handleCommand(false)}>Éteindre</button>

      {status && <p style={{ color: "green" }}>{status}</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}
