// src/components/DropdownMenu.jsx
import React, { useState, useRef, useEffect } from 'react';
import './DropdownMenu.css';

const DropdownMenu = ({ children, icon = '...', title = 'Plus d\'actions' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [menuPosition, setMenuPosition] = useState({ right: 0, left: 'auto' });
  const dropdownRef = useRef(null);
  const menuRef = useRef(null);

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

  // Ajuster la position du menu pour éviter qu'il sorte de l'écran
  useEffect(() => {
    if (isOpen && menuRef.current) {
      const menuRect = menuRef.current.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      
      // Si le menu dépasse du côté droit de l'écran
      if (menuRect.right > viewportWidth) {
        setMenuPosition({ right: 'auto', left: 0 });
      } else {
        setMenuPosition({ right: 0, left: 'auto' });
      }
    }
  }, [isOpen]);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="dropdown-container" ref={dropdownRef}>
      <button className="dropdown-toggle" onClick={toggleMenu} title={title}>
        {icon}
      </button>
      {isOpen && (
        <div 
          className="dropdown-menu" 
          ref={menuRef}
          style={menuPosition}
        >
          {children}
        </div>
      )}
    </div>
  );
};

export default DropdownMenu;
