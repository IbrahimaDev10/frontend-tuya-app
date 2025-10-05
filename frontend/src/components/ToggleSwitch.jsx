// Pas besoin d'importer le CSS ici si vous l'avez mis dans DeviceManagement.css
// qui est déjà chargé par la page.

const ToggleSwitch = ({ isOn, onToggle, isLoading = false, isDisabled = false }) => {
  const switchClass = `toggle-switch ${isLoading ? 'loading' : ''} ${isDisabled ? 'disabled' : ''}`;

  return (
    <label className={switchClass} title={isLoading ? "Chargement..." : `Passer à ${isOn ? 'OFF' : 'ON'}` }>
      <input 
        type="checkbox" 
        checked={isOn} 
        onChange={onToggle}
        disabled={isLoading || isDisabled}
      />
      <span className="slider"></span>
    </label>
  );
};

export default ToggleSwitch;
