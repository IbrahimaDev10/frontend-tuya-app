import React, { useState, useContext, useEffect } from "react";
import bg from "../assets/images/backgroundlogin.jpg"
import "../loginpage.css"
import axios from "axios";
import { MdEmail } from "react-icons/md";
import { TbLockPassword } from "react-icons/tb";
import { FaEye } from "react-icons/fa";
import { IoEyeOff } from "react-icons/io5";
import { Button } from '@mui/material';
import { useNavigate } from "react-router-dom";
import { MyContext } from "../App";

export default function LoginPage() {

    const [formData, setFormData] = useState({
      username: "",
      password: "",
      countryCode: "221", // par défaut
      appType: "Smartlife"
    });

    const [tokenData, setTokenData] = useState(null);
    const [error, setError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // Ajouter la logique de soumission ici
  };

    const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleLogin = async (e) => {
    e.preventDefault();

    try {
      const response = await axios.post(`${import.meta.env.VITE_API_URL}/api/auth/login`, {
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
      console.error(err);
    }
  };

  
    const { setIsHideSidebarAndHeader } = useContext(MyContext);
  
        useEffect(() => {
          setIsHideSidebarAndHeader(false); // Remet à false dès que la page est chargée
          
        }, []);

  return (
    <>
      <img src={bg} alt="" className='bglogin' style={{
    backgroundImage: `url(${bg})`,
    backgroundSize: "cover",
    backgroundPosition: "center",
    backgroundRepeat: "no-repeat",
    height: "100vh", // ou minHeight si tu veux l'adapter
    
  }} />
      <section className="section">
        <div className="login">
          <div className="login-header">
            <h3>Connexion</h3>
          </div>   
          <div className="login-body">
            <form onSubmit={handleLogin} className="login-form">
              <div className="input-group">
                <MdEmail className="input-icon" />
                <input 
                  type="email"
                  name="username"
                  placeholder="Adresse Email"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>
              
              <div className="input-group">
                <TbLockPassword className="input-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  name='password'
                  placeholder="Mot de passe"
                  required
                  value={formData.password}
                  onChange={handleChange}
                />
                <button 
                  type="button" 
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <IoEyeOff /> : <FaEye />}
                </button>
              </div>

              <div className="login-options">
                <label>
                  <input type="checkbox" /> Se souvenir de moi
                </label>
                <a href="#forgot">Mot de passe oublié?</a>
              </div>

              <Button 
                type="submit" 
                variant="contained" 
                fullWidth
                sx={{ mt: 3, mb: 2 }}
              >
                Se connecter
              </Button>

              <p className="register-link">
                Pas de compte? <button onClick={() => navigate('/register')}>S'inscrire</button>
              </p>
            </form>
          </div>
        </div>
      </section>
    </>
  )
}