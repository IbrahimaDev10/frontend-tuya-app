# app/routes/export_routes.py - VERSION COMPLÈTE MODULABLE

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.client import Client
from datetime import datetime
from functools import wraps
import pandas as pd
import io
import logging

# Imports pour PDF avec graphiques
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.dates as mdates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

export_bp = Blueprint('export', __name__, url_prefix='/api/export')

# =================== FONCTIONS UTILITAIRES ===================

def authenticated_user_required(f):
    """Décorateur pour authentification"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)
            
            if not current_user or not current_user.actif:
                return jsonify({'error': 'Authentification requise'}), 401
            
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': f'Erreur authentification: {str(e)}'}), 401
    return decorated_function

def validate_export_parameters():
    """Valider les paramètres d'export"""
    client_id = request.args.get('client_id')
    device_id = request.args.get('device_id')  # Nouveau paramètre optionnel
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
        
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        
    except ValueError:
        return None, 'Format de date invalide. Utilisez YYYY-MM-DD'
    
    return {
        'client_id': client_id,
        'device_id': device_id,  # Peut être None
        'start_date': start_dt,
        'end_date': end_dt
    }, None

def can_user_access_client(user, client_id):
    """Vérifier les permissions client"""
    if user.is_admin() or user.is_superadmin():
        return True
    
    if hasattr(user, 'client_id') and user.client_id == client_id:
        return True
    
    return False

def get_devices_for_export(client_id, device_id=None):
    """Récupérer les appareils à exporter"""
    if device_id:
        # Export pour un seul appareil
        device = Device.query.filter_by(
            id=device_id,
            client_id=client_id,
            actif=True
        ).first()
        return [device] if device else []
    else:
        # Export pour tous les appareils du client
        return Device.query.filter_by(
            client_id=client_id,
            actif=True
        ).all()

def build_export_dataframe(device_data_list):
    """Construire le DataFrame pour l'export"""
    export_data = []
    
    for data in device_data_list:
        device = Device.query.get(data.appareil_id)
        nom_appareil = device.nom_appareil if device else "Appareil inconnu"
        
        row = {
            'Horodatage': data.horodatage,
            'ID Appareil': data.appareil_id,
            'Nom Appareil': nom_appareil,
            'Type Système': data.type_systeme,
        }
        
        if data.type_systeme == 'monophase':
            row.update({
                'Tension (V)': data.tension,
                'Courant (A)': data.courant,
                'Puissance (W)': data.puissance,
                'Énergie (kWh)': data.energie,
                'Tension L1 (V)': None,
                'Tension L2 (V)': None,
                'Tension L3 (V)': None,
                'Courant L1 (A)': None,
                'Courant L2 (A)': None,
                'Courant L3 (A)': None,
                'Puissance Totale (W)': None,
                'Énergie Totale (kWh)': None,
            })
        else:
            row.update({
                'Tension (V)': None,
                'Courant (A)': None,
                'Puissance (W)': None,
                'Énergie (kWh)': None,
                'Tension L1 (V)': data.tension_l1,
                'Tension L2 (V)': data.tension_l2,
                'Tension L3 (V)': data.tension_l3,
                'Courant L1 (A)': data.courant_l1,
                'Courant L2 (A)': data.courant_l2,
                'Courant L3 (A)': data.courant_l3,
                'Puissance Totale (W)': data.puissance_totale,
                'Énergie Totale (kWh)': data.energie_totale,
            })
        
        row.update({
            'Température (°C)': data.temperature,
            'Humidité (%)': data.humidite,
            'État Switch': data.etat_switch,
        })
        
        export_data.append(row)
    
    return pd.DataFrame(export_data)

# =================== FONCTIONS GRAPHIQUES PDF ===================

def create_custom_chart(df, device_name, system_type, chart_type, options, figsize):
    """Créer un graphique personnalisé"""
    fig, ax = plt.subplots(figsize=figsize)
    
    # Déterminer les données
    if chart_type == 'power':
        if system_type == 'monophase':
            data = [df['Puissance (W)']]
            ylabel = 'Puissance (W)'
            colors = ['#2E86AB']
            labels = ['Puissance']
        else:
            data = [df['Puissance Totale (W)']]
            ylabel = 'Puissance (W)'
            colors = ['#2E86AB']
            labels = ['Puissance Totale']
        title = f'Évolution de la Puissance - {device_name}'
    
    elif chart_type == 'voltage':
        ylabel = 'Tension (V)'
        title = f'Évolution de la Tension - {device_name}'
        if system_type == 'monophase':
            data = [df['Tension (V)']]
            colors = ['#A23B72']
            labels = ['Tension']
        else:
            data = [df['Tension L1 (V)'], df['Tension L2 (V)'], df['Tension L3 (V)']]
            colors = ['#F18F01', '#C73E1D', '#6A994E']
            labels = ['L1', 'L2', 'L3']
    
    elif chart_type == 'current':
        ylabel = 'Courant (A)'
        title = f'Évolution du Courant - {device_name}'
        if system_type == 'monophase':
            data = [df['Courant (A)']]
            colors = ['#06A77D']
            labels = ['Courant']
        else:
            data = [df['Courant L1 (A)'], df['Courant L2 (A)'], df['Courant L3 (A)']]
            colors = ['#F18F01', '#C73E1D', '#6A994E']
            labels = ['L1', 'L2', 'L3']
    
    # Tracer selon le style
    for d, color, label in zip(data, colors, labels):
        if d.notna().any():
            if options['chart_style'] == 'line':
                ax.plot(df['Horodatage'], d, label=label, color=color, linewidth=2)
            elif options['chart_style'] == 'area':
                ax.fill_between(df['Horodatage'], d, alpha=0.3, color=color, label=label)
                ax.plot(df['Horodatage'], d, color=color, linewidth=1.5)
            elif options['chart_style'] == 'bar':
                ax.bar(df['Horodatage'], d, label=label, color=color, alpha=0.7, width=0.0001)
    
    ax.set_xlabel('Temps', fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    if options['show_legend']:
        ax.legend()
    
    if options['show_grid']:
        ax.grid(True, alpha=0.3)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_custom_summary_page(pdf, client, start_date, end_date, device_count, device_names, options):
    """Page de résumé personnalisée"""
    fig = plt.figure(figsize=(8.5, 11) if options['page_orientation'] == 'portrait' else (11, 8.5))
    
    fig.text(0.5, 0.9, 'RAPPORT D\'ANALYSE PERSONNALISÉ', 
             ha='center', fontsize=20, fontweight='bold')
    
    fig.text(0.5, 0.8, f'Client: {client.nom_entreprise}', 
             ha='center', fontsize=14)
    
    fig.text(0.1, 0.65, 'Période:', fontsize=12, fontweight='bold')
    fig.text(0.1, 0.60, f'{start_date.strftime("%d/%m/%Y")} - {end_date.strftime("%d/%m/%Y")}', 
             fontsize=11)
    
    fig.text(0.1, 0.50, 'Configuration:', fontsize=12, fontweight='bold')
    fig.text(0.1, 0.45, f'• Appareils ({device_count}):', fontsize=11)
    
    # Lister les appareils
    y_pos = 0.40
    for name in device_names[:10]:  # Max 10 pour éviter débordement
        fig.text(0.15, y_pos, f'  - {name}', fontsize=10)
        y_pos -= 0.03
    
    if len(device_names) > 10:
        fig.text(0.15, y_pos, f'  ... et {len(device_names) - 10} autres', fontsize=10, style='italic')
        y_pos -= 0.05
    
    fig.text(0.1, y_pos - 0.05, f'• Graphiques:', fontsize=11)
    fig.text(0.15, y_pos - 0.08, f'  - Puissance: {"Oui" if options["include_power"] else "Non"}', fontsize=10)
    fig.text(0.15, y_pos - 0.11, f'  - Tension: {"Oui" if options["include_voltage"] else "Non"}', fontsize=10)
    fig.text(0.15, y_pos - 0.14, f'  - Courant: {"Oui" if options["include_current"] else "Non"}', fontsize=10)
    fig.text(0.1, y_pos - 0.19, f'• Style: {options["chart_style"].capitalize()}', fontsize=11)
    fig.text(0.1, y_pos - 0.22, f'• Orientation: {options["page_orientation"].capitalize()}', fontsize=11)
    
    fig.text(0.1, 0.05, f'Généré le: {datetime.now().strftime("%d/%m/%Y à %H:%M")}', 
             fontsize=10, style='italic')
    
    plt.axis('off')
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

# =================== ROUTES D'EXPORT ===================

@export_bp.route('/csv', methods=['GET'])
@authenticated_user_required
def export_csv(current_user):
    """
    Export CSV modulable
    Paramètres:
    - client_id: requis
    - device_id: optionnel (si absent, exporte tous les appareils)
    - start_date: requis
    - end_date: requis
    """
    try:
        params, error = validate_export_parameters()
        if error:
            return jsonify({'error': error}), 400
        
        client_id = params['client_id']
        device_id = params['device_id']
        start_date = params['start_date']
        end_date = params['end_date']
        
        if not can_user_access_client(current_user, client_id):
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client non trouvé'}), 404
        
        # Construire la requête
        query = db.session.query(DeviceData).join(Device).filter(
            DeviceData.client_id == client_id,
            DeviceData.horodatage >= start_date,
            DeviceData.horodatage <= end_date
        )
        
        # Filtrer par appareil si spécifié
        if device_id:
            query = query.filter(DeviceData.appareil_id == device_id)
        
        device_data_list = query.order_by(DeviceData.horodatage).all()
        
        if not device_data_list:
            return jsonify({'error': 'Aucune donnée trouvée'}), 404
        
        df = build_export_dataframe(device_data_list)
        
        # Générer le CSV
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig', sep=';')
        output.seek(0)
        
        bytes_output = io.BytesIO()
        bytes_output.write(output.getvalue().encode('utf-8-sig'))
        bytes_output.seek(0)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        scope = f"Device_{device_id[:8]}" if device_id else "All"
        filename = f"Export_CSV_{scope}_{date_str}.csv"
        
        logger.info(f"Export CSV généré: {filename}")
        
        return send_file(
            bytes_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erreur export CSV: {str(e)}")
        return jsonify({'error': f'Erreur génération CSV: {str(e)}'}), 500

@export_bp.route('/excel', methods=['GET'])
@authenticated_user_required
def export_excel(current_user):
    """
    Export Excel modulable
    Paramètres:
    - client_id: requis
    - device_id: optionnel
    - start_date: requis
    - end_date: requis
    """
    try:
        params, error = validate_export_parameters()
        if error:
            return jsonify({'error': error}), 400
        
        client_id = params['client_id']
        device_id = params['device_id']
        start_date = params['start_date']
        end_date = params['end_date']
        
        if not can_user_access_client(current_user, client_id):
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client non trouvé'}), 404
        
        query = db.session.query(DeviceData).join(Device).filter(
            DeviceData.client_id == client_id,
            DeviceData.horodatage >= start_date,
            DeviceData.horodatage <= end_date
        )
        
        if device_id:
            query = query.filter(DeviceData.appareil_id == device_id)
        
        device_data_list = query.order_by(DeviceData.horodatage).all()
        
        if not device_data_list:
            return jsonify({'error': 'Aucune donnée trouvée'}), 404
        
        df = build_export_dataframe(device_data_list)
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Données Détaillées', index=False)
            
            worksheet = writer.sheets['Données Détaillées']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        scope = f"Device_{device_id[:8]}" if device_id else "All"
        filename = f"Export_Excel_{scope}_{date_str}.xlsx"
        
        logger.info(f"Export Excel généré: {filename}")
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erreur export Excel: {str(e)}")
        return jsonify({'error': f'Erreur génération Excel: {str(e)}'}), 500

@export_bp.route('/pdf-graphique', methods=['GET'])
@authenticated_user_required
def export_pdf_graphique(current_user):
    """
    Export PDF modulable avec graphiques
    
    Paramètres obligatoires:
    - client_id
    - start_date
    - end_date
    
    Paramètres optionnels:
    - device_id: ID d'un appareil spécifique (sinon tous)
    - include_power: true/false (défaut: true)
    - include_voltage: true/false (défaut: true)
    - include_current: true/false (défaut: true)
    - include_summary: true/false (défaut: true)
    - chart_style: line/area/bar (défaut: line)
    - page_orientation: portrait/landscape (défaut: landscape)
    - show_grid: true/false (défaut: true)
    - show_legend: true/false (défaut: true)
    """
    try:
        params, error = validate_export_parameters()
        if error:
            return jsonify({'error': error}), 400
        
        client_id = params['client_id']
        device_id = params['device_id']
        start_date = params['start_date']
        end_date = params['end_date']
        
        if not can_user_access_client(current_user, client_id):
            return jsonify({'error': 'Accès non autorisé'}), 403
        
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'error': 'Client non trouvé'}), 404
        
        # Options de personnalisation
        options = {
            'include_power': request.args.get('include_power', 'true').lower() == 'true',
            'include_voltage': request.args.get('include_voltage', 'true').lower() == 'true',
            'include_current': request.args.get('include_current', 'true').lower() == 'true',
            'include_summary': request.args.get('include_summary', 'true').lower() == 'true',
            'chart_style': request.args.get('chart_style', 'line'),
            'page_orientation': request.args.get('page_orientation', 'landscape'),
            'show_grid': request.args.get('show_grid', 'true').lower() == 'true',
            'show_legend': request.args.get('show_legend', 'true').lower() == 'true',
        }
        
        # Récupérer les appareils
        devices = get_devices_for_export(client_id, device_id)
        
        if not devices:
            return jsonify({'error': 'Aucun appareil trouvé'}), 404
        
        # Créer le PDF
        output = io.BytesIO()
        
        if options['page_orientation'] == 'portrait':
            figsize = (8.5, 11)
        else:
            figsize = (11, 8.5)
        
        with PdfPages(output) as pdf:
            # Page de résumé
            if options['include_summary']:
                device_names = [d.nom_appareil for d in devices]
                create_custom_summary_page(pdf, client, start_date, end_date, 
                                          len(devices), device_names, options)
            
            # Graphiques par appareil
            for device in devices:
                device_data_list = DeviceData.query.filter(
                    DeviceData.appareil_id == device.id,
                    DeviceData.horodatage >= start_date,
                    DeviceData.horodatage <= end_date
                ).order_by(DeviceData.horodatage).all()
                
                if not device_data_list:
                    continue
                
                df = build_export_dataframe(device_data_list)
                
                if options['include_power']:
                    fig = create_custom_chart(df, device.nom_appareil, device.type_systeme, 
                                            'power', options, figsize)
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                
                if options['include_voltage']:
                    fig = create_custom_chart(df, device.nom_appareil, device.type_systeme, 
                                            'voltage', options, figsize)
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
                
                if options['include_current']:
                    fig = create_custom_chart(df, device.nom_appareil, device.type_systeme, 
                                            'current', options, figsize)
                    pdf.savefig(fig, bbox_inches='tight')
                    plt.close(fig)
            
            # Métadonnées
            d = pdf.infodict()
            d['Title'] = f'Rapport Personnalisé - {client.nom_entreprise}'
            d['Author'] = 'SERTEC Platform'
            d['Subject'] = 'Analyse consommation électrique'
            d['CreationDate'] = datetime.now()
        
        output.seek(0)
        
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        scope = f"Device_{device_id[:8]}" if device_id else "All"
        filename = f"Rapport_PDF_{scope}_{date_str}.pdf"
        
        logger.info(f"Export PDF généré: {filename}")
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erreur export PDF: {str(e)}")
        return jsonify({'error': f'Erreur génération PDF: {str(e)}'}), 500

@export_bp.route('/health', methods=['GET'])
def health_check():
    """Vérification de santé"""
    return jsonify({
        'status': 'healthy',
        'module': 'export_routes_modulable',
        'formats': ['csv', 'excel', 'pdf-graphique'],
        'features': ['single_device', 'all_devices', 'customizable_charts'],
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