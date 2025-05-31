import React from 'react'
import { useNavigate } from 'react-router-dom'
import "../logout.css"

import { MyContext } from '../App';
import { useContext } from 'react'

export default function Logout() {
    const navigate = useNavigate();

      const handleLogout = () => {
    localStorage.removeItem("jwt"); // supprime le token
    navigate("/connexion");
    
  };

  return (
    <div className='logout'>
    <button className='btnLogout' onClick={handleLogout}>Se deconnecter</button>
    </div>
  )
}
