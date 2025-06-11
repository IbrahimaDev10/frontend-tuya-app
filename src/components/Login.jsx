import React, { useState } from "react";
import axios from "axios";
import DeviceControl from "./DeviceControl";
import DeviceList from "./DeviceList";
import bg_login from "../assets/images/bg_login.jpg"
import sertec_logo from "../assets/images/sertec_logo.jpeg"
import { MdEmail } from "react-icons/md";
import { TbLockPassword } from "react-icons/tb";
import { FaEye } from "react-icons/fa";
import { IoEyeOff } from "react-icons/io5";
import { Button } from '@mui/material';
import {useNavigate } from "react-router-dom";

export default function Login() {
  const [formData, setFormData] = useState({
    username: "",
    password: "",
    countryCode: "221", // par défaut
    appType: "Smartlife"
  });

  const [tokenData, setTokenData] = useState(null);
  const [error, setError] = useState("");

  const [showPassword ,setShowPassword]=useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post("http://localhost:5000/api/auth/login", {
        email: formData.username,
        password: formData.password
      });

      if (response.data.success) {
        // Mise à jour pour correspondre à la structure de la réponse
        localStorage.setItem("token", response.data.data.access_token);
        localStorage.setItem("refresh_token", response.data.data.refresh_token);
        localStorage.setItem("user", JSON.stringify(response.data.data.user));
        navigate("/dash");
      } else {
        setError("Erreur d'authentification");
      }
    } catch (err) {
      setError(err.response?.data?.message || "Erreur de connexion");
    }
  };


  return (
    <>
    <img src={sertec_logo} className='loginPatern' />
    <section className='loginSection'>
    <div className="loginBox">
            <div className='logo text-center'>
            
            <h5>Login</h5>
            </div>
    <div className="wrapper mt-3 card border  ">
      <form onSubmit={handleLogin}>
      <div className="form-group mb-3 position-relative  ">
      <span className='icon'><MdEmail /></span>
        <input
          type="email"
          className="form-control"
          name="username"
          placeholder="Email"
          value={formData.username}
          onChange={handleChange}
        />
        </div>
        <div className="form-group mb-3 position-relative  ">
        <span className='icon'><TbLockPassword /></span>
        <input
          type={`${showPassword===false ? 'password' : 'text'}`}
          className="form-control"
          name="password"
          placeholder="Mot de passe"
          value={formData.password}
          onChange={handleChange}
        />
                            <span className='toggleShowPassword' onClick={()=>setShowPassword(!showPassword)}>
                        {
                            showPassword===false ? <FaEye />
                            : <IoEyeOff />
                        }
                    </span>
                    </div>
        <div className="form-group" >
        <button type="submit">Se connecter</button>
        </div>
       
      </form>
      </div>
      



      {tokenData && (
        <div style={{ marginTop: "20px" }}>
          <h4 style={{ colorp: "white" }}>Token :</h4>
          <pre>{JSON.stringify(tokenData, null, 2)}</pre>
        </div>
      )}

      {error && <p style={{ color: "red" }}>{error}</p>}
    
   {/* <DeviceControl />
    <DeviceList /> */}
    </div>
    </section>
    </>
  );
}
