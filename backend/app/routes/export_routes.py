# app/routes/export_routes.py - Routes d'export Excel détaillé
# ✅ Export des données DeviceData avec support monophasé/triphasé

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.client import Client
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
import io
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Créer le blueprint
export_bp = Blueprint('export', __name__, url_prefix='/api/export')

# =================== FONCTIONS UTILITAIRES ===================

def authenticated_user_required(f):
    """Décorateur pour les routes accessibles à tout utilisateur authentifié"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            # Vérifie si l'utilisateur existe et est actif
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
            
            if not current_user or not current_user.actif or not current_user.is_admin():
                return jsonify({'error': 'Permission admin requise'}), 403
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

def validate_export_parameters():
    """Valider les paramètres d'export"""
    client_id = request.args.get('client_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not client_id:
        return None, 'client_id est requis'
    
    if not start_date:
        return None, 'start_date est requis (format: YYYY-MM-DD)'
    
    if not end_date:
        return None, 'end_date est requis (format: YYYY-MM-DD)'
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_dt > end_dt:
            return None, 'start_date doit être antérieure à end_date'
        
        # Ajouter 23:59:59 à end_date pour inclure toute la journée
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
    except ValueError:
        return None, 'Format de date invalide. Utilisez YYYY-MM-DD'
    
    return {
        'client_id': client_id,
        'start_date': start_dt,
        'end_date': end_dt
    }, None

def can_user_access_client(user, client_id):
    """Vérifier si l'utilisateur peut accéder aux données du client"""
    if user.is_admin() or user.is_superadmin():
        return True
    
    # Pour les clients, vérifier qu'ils accèdent à leurs propres données
    if hasattr(user, 'client_id') and user.client_id == client_id:
        return True
    
    return False

def build_export_dataframe(device_data_list):
    """Construire le DataFrame pour l'export Excel"""
    export_data = []
    
    for data in device_data_list:
        # Récupérer le nom de l'appareil
        device = Device.query.get(data.appareil_id)
        nom_appareil = device.nom_appareil if device else "Appareil inconnu"
        
        # Structure de base pour chaque enregistrement
        row = {
            'Horodatage': data.horodatage,
            'ID Appareil': data.appareil_id,
            'Nom Appareil': nom_appareil,
            'Type Système': data.type_systeme,
        }
        
        if data.type_systeme == 'monophase':
            # Données monophasées
            row.update({
                'Tension (V)': data.tension,
                'Courant (A)': data.courant,
                'Puissance (W)': data.puissance,
                'Énergie (kWh)': data.energie,
                # Colonnes triphasées vides pour monophasé
                'Tension L1 (V)': None,
                'Tension L2 (V)': None,
                'Tension L3 (V)': None,
                'Courant L1 (A)': None,
                'Courant L2 (A)': None,
                'Courant L3 (A)': None,
                'Puissance Totale (W)': None,
                'Énergie Totale (kWh)': None,
                'Facteur Puissance Total': None,
            })
        else:
            # Données triphasées
            row.update({
                # Colonnes monophasées vides pour triphasé
                'Tension (V)': None,
                'Courant (A)': None,
                'Puissance (W)': None,
                'Énergie (kWh)': None,
                # Données triphasées
                'Tension L1 (V)': data.tension_l1,
                'Tension L2 (V)': data.tension_l2,
                'Tension L3 (V)': data.tension_l3,
                'Courant L1 (A)': data.courant_l1,
                'Courant L2 (A)': data.courant_l2,
                'Courant L3 (A)': data.courant_l3,
                'Puissance Totale (W)': data.puissance_totale,
                'Énergie Totale (kWh)': data.energie_totale,
                'Facteur Puissance Total': data.facteur_puissance_total,
            })
        
        # Données environnementales communes
        row.update({
            'Température (°C)': data.temperature,
            'Humidité (%)': data.humidite,
            'État Switch': data.etat_switch,
        })
        
        export_data.append(row)
    
    return pd.DataFrame(export_data)

# =================== ROUTES D'EXPORT ===================

@export_bp.route('/detailed-excel', methods=['GET'])
@authenticated_user_required
def export_detailed_excel(current_user):
    """
    Export Excel détaillé des données DeviceData pour un client et une période donnés
    """
    try:
        # Valider les paramètres
        params, error = validate_export_parameters()
        if error:
            return jsonify({'error': error}), 400
        
        client_id = params['client_id']
        start_date = params['start_date']
        end_date = params['end_date']
        
        # Vérifier les permissions
        if not can_user_access_client(current_user, client_id):
            return jsonify({'error': 'Accès non autorisé aux données de ce client'}), 403
        
        # Vérifier que le client existe
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client non trouvé'}), 404
        
        logger.info(f"Export Excel demandé pour client {client_id} du {start_date} au {end_date}")
        
        # Récupérer les données avec jointure sur Device
        query = db.session.query(DeviceData).join(Device).filter(
            DeviceData.client_id == client_id,
            DeviceData.horodatage >= start_date,
            DeviceData.horodatage <= end_date
        ).order_by(DeviceData.horodatage)
        
        device_data_list = query.all()
        
        if not device_data_list:
            return jsonify({'error': 'Aucune donnée trouvée pour la période spécifiée'}), 404
        
        logger.info(f"Récupération de {len(device_data_list)} enregistrements pour l'export")
        
        # Construire le DataFrame
        df = build_export_dataframe(device_data_list)
        
        # Générer le fichier Excel en mémoire
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Rapport Détaillé', index=False)
            
            # Ajuster automatiquement la largeur des colonnes
            worksheet = writer.sheets['Rapport Détaillé']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Limiter à 50 caractères
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Générer le nom du fichier
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Rapport_Detaillé_{client_id}_{date_str}.xlsx"
        
        logger.info(f"Export Excel généré avec succès: {filename}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export Excel: {str(e)}")
        return jsonify({'error': f'Erreur lors de la génération du rapport: {str(e)}'}), 500

@export_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de santé du module d'export"""
    return jsonify({
        'status': 'healthy',
        'module': 'export_routes',
        'timestamp': datetime.utcnow().isoformat()
    })

# =================== GESTIONNAIRES D'ERREUR ===================

@export_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Requête invalide'}), 400

@export_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Authentification requise'}), 401

@export_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Accès interdit'}), 403

@export_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ressource non trouvée'}), 404

@export_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Erreur interne: {str(error)}")
    return jsonify({'error': 'Erreur interne du serveur'}), 500 