import React from 'react'
import Button from './Button'
import './Modal.css'

const ConfirmModal = ({ 
  title, 
  message, 
  confirmText = 'Confirmer', 
  cancelText = 'Annuler',
  onConfirm, 
  onCancel,
  variant = 'primary' // primary, danger
}) => {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content small" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
        </div>

        <div className="modal-body">
          <p>{message}</p>
        </div>

        <div className="modal-footer">
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            variant={variant === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmModal