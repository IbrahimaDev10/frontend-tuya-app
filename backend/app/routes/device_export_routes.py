# app/routes/device_export_routes.py
"""
Routes API pour l'export des données d'appareils
Formats: Excel, CSV, PDF
Périodes: Jour, Mois, Année
"""

from flask import Blueprint, request, jsonify, send_file, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.device import Device
from app.services.device_export_service import DeviceDataExportService
from datetime import datetime, date
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Créer le blueprint
export_bp = Blueprint('device_export', __name__, url_prefix='/api/devices/export')

# Instance du service d'export
export_service = DeviceDataExportService()

# =================== DÉCORATEURS ===================

def authenticated_user_required(f):
    """Décorateur pour les routes nécessitant une authentification"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user or not current_user.actif:
                return jsonify({'error': 'Authentification requise ou utilisateur inactif'}), 401
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

def admin_required(f):
    """Décorateur pour les routes admin"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user or not current_user.is_admin():
                return jsonify({'error': 'Permission admin requise'}), 403
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

# =================== ROUTES D'EXPORT INDIVIDUEL ===================

@export_bp.route('/<device_id>/download', methods=['POST'])
@authenticated_user_required
def export_device_data(current_user, device_id):
    """
    Export des données d'un appareil
    
    Body JSON:
    {
        "format": "excel" | "csv" | "pdf",
        "period_type": "day" | "month" | "year",
        "period_value": "2024-01-15" | "2024-01" | 2024,
        "include_graphs": true (pour PDF uniquement)
    }
    """
    try:
        # Vérifier que l'appareil existe et est accessible
        device = Device.query.get(device_id)
        if not device:
            return jsonify({'error': 'Appareil non trouvé'}), 404
        
        # Vérifier les permissions
        if not device.peut_etre_vu_par_utilisateur(current_user):
            return jsonify({'error': 'Accès interdit à cet appareil'}), 403
        
        # Récupérer les paramètres
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        format_type = data.get('format', 'excel').lower()
        period_type = data.get('period_type', 'day')
        period_value = data.get('period_value')
        include_graphs = data.get('include_graphs', True)
        
        # Validation du format
        if format_type not in ['excel', 'csv', 'pdf']:
            return jsonify({'error': f'Format non supporté: {format_type}'}), 400
        
        # Validation de la période
        if period_type not in ['day', 'month', 'year']:
            return jsonify({'error': f'Type de période non supporté: {period_type}'}), 400
        
        if not period_value:
            return jsonify({'error': 'Valeur de période requise'}), 400
        
        # Appeler le service d'export
        result = export_service.export_device_data(
            device_id=device_id,
            period_type=period_type,
            period_value=period_value,
            format=format_type,
            include_graphs=include_graphs
        )
        
        if not result.get('success'):
            return jsonify({
                'error': result.get('error', 'Erreur lors de l\'export')
            }), 400
        
        # Retourner le fichier
        file = result['file']
        filename = result['filename']
        mime_type = result['mime_type']
        
        response = make_response(file.getvalue())
        response.headers['Content-Type'] = mime_type
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = result.get('size', len(file.getvalue()))
        
        # Log l'export
        logger.info(f"Export {format_type} réussi pour appareil {device_id} par utilisateur {current_user.id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur export appareil {device_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500

@export_bp.route('/batch/download', methods=['POST'])
@authenticated_user_required
def export_multiple_devices_data(current_user):
    """
    Export des données de plusieurs appareils

    Body JSON:
    {
        "device_ids": ["device_id1", "device_id2", ...],
        "format": "excel" | "csv" | "pdf",
        "period_type": "day" | "month" | "year",
        "period_value": "2024-01-15" | "2024-01" | 2024
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400

        device_ids = data.get('device_ids', [])
        format_type = (data.get('format') or 'excel').lower()
        period_type = data.get('period_type', 'day')
        period_value = data.get('period_value')

        # Validations basiques
        if not device_ids:
            return jsonify({'error': 'Liste des appareils requise'}), 400
        if len(device_ids) > 50:
            return jsonify({'error': 'Maximum 50 appareils par export'}), 400
        if format_type not in ['excel', 'csv', 'pdf']:
            return jsonify({'error': f'Format non supporté: {format_type}'}), 400
        if period_type not in ['day', 'month', 'year']:
            return jsonify({'error': f'Type de période non supporté: {period_type}'}), 400
        if period_value in (None, ""):
            return jsonify({'error': 'Valeur de période requise'}), 400

        # Filtrer par permissions
        accessible_device_ids = []
        for dev_id in device_ids:
            device = Device.query.get(dev_id)
            if device and device.peut_etre_vu_par_utilisateur(current_user):
                accessible_device_ids.append(dev_id)

        if not accessible_device_ids:
            return jsonify({'error': 'Aucun appareil accessible trouvé'}), 403

        # 🔧 APPEL SERVICE (===> parenthèses fermées correctement)
        result = export_service.export_multiple_devices(
            device_ids=accessible_device_ids,
            period_type=period_type,
            period_value=period_value,
            format=format_type
        )

        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Erreur lors de l\'export')}), 400

        file = result['file']           # io.BytesIO
        filename = result['filename']   # str
        mime_type = result['mime_type'] # str

        resp = make_response(file.getvalue())
        resp.headers['Content-Type'] = mime_type
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        resp.headers['Content-Length'] = result.get('size', len(file.getvalue()))

        logger.info(
            f"Export batch {format_type} OK | devices={len(accessible_device_ids)} | user={current_user.id}"
        )
        return resp

    except Exception as e:
        logger.error(f"Erreur export batch: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
