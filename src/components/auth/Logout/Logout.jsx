import React from 'react';
import { useAuth } from '../AuthContext';
import './logout.css';

export default function Logout() {
  const { logout } = useAuth();

  return (
    <div className='logout'>
      <button className='btnLogout' onClick={logout}>Se deconnecter</button>
    </div>
  );
}