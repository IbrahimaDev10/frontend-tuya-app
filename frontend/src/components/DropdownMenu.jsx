// src/components/DropdownMenu.jsx
import React, { useState, useRef, useEffect } from 'react';
import './DropdownMenu.css'; // Créez ce fichier CSS

const DropdownMenu = ({ children, icon = '...', title = 'Plus d\'actions' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Fermer le menu si on clique en dehors
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="dropdown-container" ref={dropdownRef}>
      <button className="dropdown-toggle" onClick={toggleMenu} title={title}>
        {icon}
      </button>
      {isOpen && (
        <div className="dropdown-menu">
          {children}
        </div>
      )}
    </div>
  );
};

export default DropdownMenu;
