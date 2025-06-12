import React, { useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MdEmail } from 'react-icons/md';
import { TbLockPassword } from 'react-icons/tb';
import { FaEye } from 'react-icons/fa';
import { IoEyeOff } from 'react-icons/io5';
import { Button } from '@mui/material';
import { useAuth } from '../AuthContext';
import { MyContext } from '../../../App';
import bg from '../../../assets/images/backgroundlogin.jpg';
import '../../../loginpage.css';

export default function Login() {
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const { login } = useAuth();
  const { setIsHideSidebarAndHeader } = useContext(MyContext);

  useEffect(() => {
    setIsHideSidebarAndHeader(false);
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const result = await login(formData.username, formData.password);
    if (!result.success) {
      setError(result.error);
    }
  };

  return (
    <>
      <img src={bg} alt="" className='bglogin' style={{
        backgroundImage: `url(${bg})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundRepeat: "no-repeat",
        height: "100vh"
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
                  name="password"
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

              {error && <p style={{ color: "red" }}>{error}</p>}

              <p className="register-link">
                Pas de compte? <button onClick={() => navigate('/register')}>S'inscrire</button>
              </p>
            </form>
          </div>
        </div>
      </section>
    </>
  );
}