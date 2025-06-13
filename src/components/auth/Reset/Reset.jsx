import React, { useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MdEmail } from 'react-icons/md';
import { TbLockPassword } from 'react-icons/tb';
import { FaEye } from 'react-icons/fa';
import { IoEyeOff } from 'react-icons/io5';
import { Button } from '@mui/material';
import { useAuth } from '../AuthContext';
import { MyContext } from '../../../App';
import '../Login/loginpage.css';
import bg from '../../../assets/images/backgroundlogin.jpg';

export default function Reset() {
  const [step, setStep] = useState('request'); // 'request' ou 'reset'
  const [formData, setFormData] = useState({
    email: '',
    token: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const { setIsHideSidebarAndHeader } = useContext(MyContext);
  const navigate = useNavigate();

  useEffect(() => {
    setIsHideSidebarAndHeader(false);
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleRequestReset = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: formData.email })
      });
      const data = await response.json();
      
      if (response.ok) {
        setSuccess('Un email de réinitialisation a été envoyé à votre adresse email.');
        setStep('reset');
      } else {
        setError(data.error || 'Une erreur est survenue');
      }
    } catch (err) {
      setError('Erreur de connexion au serveur');
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (formData.newPassword !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: formData.token,
          new_password: formData.newPassword
        })
      });
      const data = await response.json();

      if (response.ok) {
        setSuccess('Votre mot de passe a été réinitialisé avec succès');
        setTimeout(() => navigate('/login'), 2000);
      } else {
        setError(data.error || 'Une erreur est survenue');
      }
    } catch (err) {
      setError('Erreur de connexion au serveur');
    }
  };

  return (
    <section
      className="login-page-section"
      style={{
        backgroundImage: `url(${bg})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <div className="login">
        <div className="login-header">
          <h3>{step === 'request' ? 'Réinitialisation du mot de passe' : 'Nouveau mot de passe'}</h3>
        </div>
        <div className="login-body">
          {step === 'request' ? (
            <form onSubmit={handleRequestReset} className="login-form">
              <div className="input-group">
                <MdEmail className="input-icon" />
                <input
                  type="email"
                  name="email"
                  placeholder="Adresse Email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                />
              </div>

              <Button
                type="submit"
                variant="contained"
                fullWidth
                sx={{ mt: 3, mb: 2 }}
              >
                Envoyer le lien de réinitialisation
              </Button>

              {error && <p style={{ color: "red" }}>{error}</p>}
              {success && <p style={{ color: "green" }}>{success}</p>}

              <p className="register-link">
                <button onClick={() => navigate('/connexion')}>
                  Retour à la connexion
                </button>
              </p>
            </form>
          ) : (
            <form onSubmit={handleResetPassword} className="login-form">
              <div className="input-group">
                <input
                  type="text"
                  name="token"
                  placeholder="Code de réinitialisation"
                  value={formData.token}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="input-group">
                <TbLockPassword className="input-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="newPassword"
                  placeholder="Nouveau mot de passe"
                  value={formData.newPassword}
                  onChange={handleChange}
                  required
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <IoEyeOff /> : <FaEye />}
                </button>
              </div>

              <div className="input-group">
                <TbLockPassword className="input-icon" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="confirmPassword"
                  placeholder="Confirmer le mot de passe"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required
                />
              </div>

              <Button
                type="submit"
                variant="contained"
                fullWidth
                sx={{ mt: 3, mb: 2 }}
              >
                Réinitialiser le mot de passe
              </Button>

              {error && <p style={{ color: "red" }}>{error}</p>}
              {success && <p style={{ color: "green" }}>{success}</p>}
            </form>
          )}
        </div>
      </div>
    </section>
  );
}