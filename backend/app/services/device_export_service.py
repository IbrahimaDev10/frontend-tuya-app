# app/services/device_export_service.py
"""
Service d'export des données d'appareils IoT
Formats supportés: Excel, CSV, PDF
Périodes: Jour, Mois, Année
Compatible: Monophasé et Triphasé
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import io
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import HexColor
import matplotlib
matplotlib.use('Agg')  # Backend non-GUI pour serveur
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sqlalchemy import func, and_, or_
from app.models.device import Device
from app.models.device_data import DeviceData
from app.models.client import Client
from app.models.site import Site
from app import db
import logging

logger = logging.getLogger(__name__)

class DeviceDataExportService:
    """Service d'export des données d'appareils avec support multi-format et multi-période"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Configuration des styles personnalisés pour PDF"""
        # Style titre principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=HexColor('#1e3a8a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Style sous-titre
        self.styles.add(ParagraphStyle(
            name='CustomSubTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=HexColor('#3b82f6'),
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        ))
        
        # Style info
        self.styles.add(ParagraphStyle(
            name='InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=HexColor('#6b7280'),
            alignment=TA_LEFT
        ))
        
    # =================== MÉTHODES PRINCIPALES D'EXPORT ===================
    
    def export_device_data(self, device_id: str, period_type: str, period_value: Any, 
                           format: str, include_graphs: bool = True) -> Dict[str, Any]:
        """
        Export principal des données d'un appareil
        
        Args:
            device_id: ID de l'appareil
            period_type: 'day', 'month', 'year'
            period_value: Date, mois ou année selon le type
            format: 'excel', 'csv', 'pdf'
            include_graphs: Inclure les graphiques (pour PDF)
            
        Returns:
            Dict avec le fichier généré et les métadonnées
        """
        try:
            # Récupérer l'appareil
            device = Device.query.get(device_id)
            if not device:
                return {'success': False, 'error': 'Appareil non trouvé'}
            
            # Déterminer la période
            start_date, end_date = self._get_period_dates(period_type, period_value)
            
            # Récupérer les données
            data = self._fetch_device_data(device, start_date, end_date)
            
            if not data:
                return {
                    'success': False, 
                    'error': f'Aucune donnée disponible pour la période sélectionnée'
                }
            
            # Préparer les données selon le type d'appareil
            if device.type_systeme == 'triphase':
                df = self._prepare_triphase_dataframe(data)
            else:
                df = self._prepare_monophase_dataframe(data)
            
            # Générer l'export selon le format
            if format == 'excel':
                result = self._export_to_excel(df, device, start_date, end_date, period_type)
            elif format == 'csv':
                result = self._export_to_csv(df, device, start_date, end_date)
            elif format == 'pdf':
                result = self._export_to_pdf(df, device, start_date, end_date, period_type, include_graphs)
            else:
                return {'success': False, 'error': f'Format non supporté: {format}'}
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur export données appareil {device_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def export_multiple_devices(self, device_ids: List[str], period_type: str, 
                               period_value: Any, format: str) -> Dict[str, Any]:
        """
        Export des données de plusieurs appareils
        
        Args:
            device_ids: Liste des IDs d'appareils
            period_type: 'day', 'month', 'year'
            period_value: Date, mois ou année
            format: 'excel', 'csv', 'pdf'
            
        Returns:
            Dict avec le fichier généré
        """
        try:
            devices = Device.query.filter(Device.id.in_(device_ids)).all()
            
            if not devices:
                return {'success': False, 'error': 'Aucun appareil trouvé'}
            
            start_date, end_date = self._get_period_dates(period_type, period_value)
            
            # Créer un dictionnaire de DataFrames par appareil
            all_data = {}
            
            for device in devices:
                data = self._fetch_device_data(device, start_date, end_date)
                if data:
                    if device.type_systeme == 'triphase':
                        df = self._prepare_triphase_dataframe(data)
                    else:
                        df = self._prepare_monophase_dataframe(data)
                    all_data[device.nom_appareil] = df
            
            if not all_data:
                return {'success': False, 'error': 'Aucune donnée disponible'}
            
            # Export selon format
            if format == 'excel':
                result = self._export_multiple_to_excel(all_data, devices, start_date, end_date, period_type)
            elif format == 'csv':
                # Pour CSV, on combine tous dans un seul fichier
                result = self._export_multiple_to_csv(all_data, devices, start_date, end_date)
            elif format == 'pdf':
                result = self._export_multiple_to_pdf(all_data, devices, start_date, end_date, period_type)
            else:
                return {'success': False, 'error': f'Format non supporté: {format}'}
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur export multiple: {e}")
            return {'success': False, 'error': str(e)}
    
    # =================== MÉTHODES DE RÉCUPÉRATION DES DONNÉES ===================
    
    def _get_period_dates(self, period_type: str, period_value: Any) -> tuple:
        """Calculer les dates de début et fin selon la période"""
        if period_type == 'day':
            if isinstance(period_value, str):
                date = datetime.strptime(period_value, '%Y-%m-%d').date()
            else:
                date = period_value
            start = datetime.combine(date, datetime.min.time())
            end = datetime.combine(date, datetime.max.time())
            
        elif period_type == 'month':
            if isinstance(period_value, str):
                year, month = map(int, period_value.split('-'))
            else:
                year = period_value['year']
                month = period_value['month']
            
            start = datetime(year, month, 1)
            # Dernier jour du mois
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
                
        elif period_type == 'year':
            if isinstance(period_value, int):
                year = period_value
            else:
                year = int(period_value)
            
            start = datetime(year, 1, 1)
            end = datetime(year, 12, 31, 23, 59, 59)
            
        else:
            raise ValueError(f"Type de période non supporté: {period_type}")
        
        return start, end
    
    def _fetch_device_data(self, device: Device, start_date: datetime, end_date: datetime) -> List[DeviceData]:
        """Récupérer les données d'un appareil pour une période"""
        return DeviceData.query.filter(
            DeviceData.appareil_id == device.id,
            DeviceData.horodatage >= start_date,
            DeviceData.horodatage <= end_date
        ).order_by(DeviceData.horodatage.asc()).all()
    
    # =================== PRÉPARATION DES DATAFRAMES ===================
    
    def _prepare_monophase_dataframe(self, data: List[DeviceData]) -> pd.DataFrame:
        """Préparer DataFrame pour appareil monophasé"""
        records = []
        
        for record in data:
            row = {
                'Date/Heure': record.horodatage,
                'Tension (V)': record.tension,
                'Courant (A)': record.courant,
                'Puissance (W)': record.puissance,
                'Énergie (kWh)': record.energie,
                'Température (°C)': record.temperature,
                'État': 'ON' if record.etat_switch else 'OFF'
            }
            records.append(row)
        
        df = pd.DataFrame(records)
        
        # Calculer des statistiques supplémentaires
        if not df.empty:
            df['Facteur de puissance'] = np.where(
                (df['Tension (V)'].notna()) & (df['Courant (A)'].notna()) & (df['Courant (A)'] > 0),
                df['Puissance (W)'] / (df['Tension (V)'] * df['Courant (A)']),
                np.nan
            )
            df['Facteur de puissance'] = df['Facteur de puissance'].round(3)
        
        return df
    
    def _prepare_triphase_dataframe(self, data: List[DeviceData]) -> pd.DataFrame:
        """Préparer DataFrame pour appareil triphasé"""
        records = []
        
        for record in data:
            row = {
                'Date/Heure': record.horodatage,
                # Tensions par phase
                'Tension L1 (V)': record.tension_l1,
                'Tension L2 (V)': record.tension_l2,
                'Tension L3 (V)': record.tension_l3,
                # Courants par phase
                'Courant L1 (A)': record.courant_l1,
                'Courant L2 (A)': record.courant_l2,
                'Courant L3 (A)': record.courant_l3,
                'Courant Neutre (A)': record.courant_neutre,
                # Puissances par phase
                'Puissance L1 (W)': record.puissance_l1,
                'Puissance L2 (W)': record.puissance_l2,
                'Puissance L3 (W)': record.puissance_l3,
                'Puissance Totale (W)': record.puissance_totale,
                # Facteurs de puissance
                'FP L1': record.facteur_puissance_l1,
                'FP L2': record.facteur_puissance_l2,
                'FP L3': record.facteur_puissance_l3,
                'FP Total': record.facteur_puissance_total,
                # Autres
                'Fréquence (Hz)': record.frequence,
                'Énergie Totale (kWh)': record.energie_totale,
                'Température (°C)': record.temperature,
                'État': 'ON' if record.etat_switch else 'OFF'
            }
            records.append(row)
        
        df = pd.DataFrame(records)
        
        # Calculer déséquilibres si données disponibles
        if not df.empty:
            # Déséquilibre tension
            tension_cols = ['Tension L1 (V)', 'Tension L2 (V)', 'Tension L3 (V)']
            df['Tension Moyenne (V)'] = df[tension_cols].mean(axis=1)
            
            # Déséquilibre courant
            courant_cols = ['Courant L1 (A)', 'Courant L2 (A)', 'Courant L3 (A)']
            df['Courant Moyen (A)'] = df[courant_cols].mean(axis=1)
            
            # Calculer % déséquilibre
            df['Déséquilibre Tension (%)'] = self._calculate_imbalance(df, tension_cols)
            df['Déséquilibre Courant (%)'] = self._calculate_imbalance(df, courant_cols)
        
        return df
    
    def _calculate_imbalance(self, df: pd.DataFrame, columns: List[str]) -> pd.Series:
        """Calculer le déséquilibre en pourcentage"""
        mean_val = df[columns].mean(axis=1)
        max_dev = df[columns].sub(mean_val, axis=0).abs().max(axis=1)
        imbalance = (max_dev / mean_val * 100).round(2)
        return imbalance.replace([np.inf, -np.inf], np.nan)
    
    # =================== EXPORT EXCEL ===================
    
    def _export_to_excel(self, df: pd.DataFrame, device: Device, start_date: datetime, 
                        end_date: datetime, period_type: str) -> Dict[str, Any]:
        """Export vers Excel avec mise en forme"""
        try:
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Feuille principale avec données
                df.to_excel(writer, sheet_name='Données', index=False)
                
                # Récupérer le workbook et worksheet
                workbook = writer.book
                worksheet = writer.sheets['Données']
                
                # Formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'fg_color': '#1e3a8a',
                    'font_color': 'white',
                    'border': 1
                })
                
                date_format = workbook.add_format({
                    'num_format': 'dd/mm/yyyy hh:mm:ss',
                    'border': 1
                })
                
                number_format = workbook.add_format({
                    'num_format': '#,##0.00',
                    'border': 1
                })
                
                # Appliquer les formats aux colonnes
                for col_num, col_name in enumerate(df.columns):
                    worksheet.write(0, col_num, col_name, header_format)
                    
                    if 'Date' in col_name:
                        worksheet.set_column(col_num, col_num, 20, date_format)
                    else:
                        worksheet.set_column(col_num, col_num, 15, number_format)
                
                # Ajouter feuille de statistiques
                stats_df = self._calculate_statistics(df, device.type_systeme)
                stats_df.to_excel(writer, sheet_name='Statistiques', index=False)
                
                # Ajouter feuille d'informations
                info_df = pd.DataFrame({
                    'Information': ['Appareil', 'Type', 'Système', 'Période', 'Date début', 'Date fin', 'Nombre de mesures'],
                    'Valeur': [
                        device.nom_appareil,
                        device.type_appareil,
                        device.type_systeme,
                        period_type,
                        start_date.strftime('%Y-%m-%d %H:%M'),
                        end_date.strftime('%Y-%m-%d %H:%M'),
                        len(df)
                    ]
                })
                info_df.to_excel(writer, sheet_name='Informations', index=False)
                
                # Ajouter graphiques si données suffisantes
                if len(df) > 1:
                    self._add_excel_charts(writer, df, device.type_systeme)
            
            output.seek(0)
            
            filename = f"{device.nom_appareil}_{period_type}_{start_date.strftime('%Y%m%d')}.xlsx"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': len(output.getvalue()),
                'stats': {
                    'total_records': len(df),
                    'period': f"{start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}",
                    'device_type': device.type_systeme
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export Excel: {e}")
            return {'success': False, 'error': str(e)}
    
    def _add_excel_charts(self, writer, df: pd.DataFrame, type_systeme: str):
        """Ajouter des graphiques dans Excel"""
        workbook = writer.book
        
        # Créer une nouvelle feuille pour les graphiques
        chart_sheet = workbook.add_worksheet('Graphiques')
        
        # Graphique de tension
        if type_systeme == 'monophase':
            # Graphique simple pour monophasé
            chart = workbook.add_chart({'type': 'line'})
            chart.add_series({
                'categories': ['Données', 1, 0, len(df), 0],
                'values': ['Données', 1, 1, len(df), 1],
                'name': 'Tension (V)'
            })
            chart.set_title({'name': 'Évolution de la Tension'})
            chart.set_x_axis({'name': 'Temps'})
            chart.set_y_axis({'name': 'Tension (V)'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})
            
        else:
            # Graphique multi-séries pour triphasé
            chart = workbook.add_chart({'type': 'line'})
            for i, phase in enumerate(['L1', 'L2', 'L3']):
                chart.add_series({
                    'categories': ['Données', 1, 0, len(df), 0],
                    'values': ['Données', 1, i+1, len(df), i+1],
                    'name': f'Tension {phase}'
                })
            chart.set_title({'name': 'Évolution des Tensions par Phase'})
            chart.set_x_axis({'name': 'Temps'})
            chart.set_y_axis({'name': 'Tension (V)'})
            chart_sheet.insert_chart('B2', chart, {'x_scale': 2, 'y_scale': 1.5})
    
    # =================== EXPORT CSV ===================
    
    def _export_to_csv(self, df: pd.DataFrame, device: Device, start_date: datetime, 
                      end_date: datetime) -> Dict[str, Any]:
        """Export vers CSV"""
        try:
            output = BytesIO()
            
            # Convertir DataFrame en CSV
            df.to_csv(output, index=False, encoding='utf-8-sig')  # UTF-8 avec BOM pour Excel
            
            output.seek(0)
            
            filename = f"{device.nom_appareil}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'text/csv',
                'size': len(output.getvalue()),
                'stats': {
                    'total_records': len(df),
                    'columns': list(df.columns)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export CSV: {e}")
            return {'success': False, 'error': str(e)}
    
    # =================== EXPORT PDF ===================
    
    def _export_to_pdf(self, df: pd.DataFrame, device: Device, start_date: datetime, 
                      end_date: datetime, period_type: str, include_graphs: bool = True) -> Dict[str, Any]:
        """Export vers PDF avec mise en forme professionnelle"""
        try:
            output = BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                output,
                pagesize=landscape(A4) if device.type_systeme == 'triphase' else A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            # Conteneur pour les éléments
            elements = []
            
            # Titre principal
            title = Paragraph(
                f"Rapport de Données - {device.nom_appareil}",
                self.styles['CustomTitle']
            )
            elements.append(title)
            elements.append(Spacer(1, 20))
            
            # Informations de l'appareil
            elements.extend(self._create_device_info_section(device, start_date, end_date, period_type))
            elements.append(Spacer(1, 20))
            
            # Statistiques
            stats_df = self._calculate_statistics(df, device.type_systeme)
            elements.append(Paragraph("Statistiques", self.styles['CustomSubTitle']))
            elements.append(Spacer(1, 10))
            elements.append(self._create_stats_table(stats_df))
            elements.append(PageBreak())
            
            # Graphiques si demandés
            if include_graphs and len(df) > 1:
                elements.append(Paragraph("Graphiques", self.styles['CustomSubTitle']))
                elements.append(Spacer(1, 10))
                
                # Créer les graphiques
                graphs = self._create_pdf_graphs(df, device.type_systeme)
                for graph in graphs:
                    elements.append(graph)
                    elements.append(Spacer(1, 20))
                
                elements.append(PageBreak())
            
            # Tableau de données (limité pour PDF)
            elements.append(Paragraph("Données Détaillées", self.styles['CustomSubTitle']))
            elements.append(Spacer(1, 10))
            
            # Limiter le nombre de lignes pour le PDF
            data_sample = df.head(100) if len(df) > 100 else df
            elements.append(self._create_data_table(data_sample, device.type_systeme))
            
            if len(df) > 100:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(
                    f"Note: Seules les 100 premières mesures sur {len(df)} sont affichées. "
                    f"Pour l'ensemble des données, utilisez l'export Excel ou CSV.",
                    self.styles['InfoStyle']
                ))
            
            # Générer le PDF
            doc.build(elements, onFirstPage=self._add_page_header, onLaterPages=self._add_page_header)
            
            output.seek(0)
            
            filename = f"{device.nom_appareil}_rapport_{period_type}_{start_date.strftime('%Y%m%d')}.pdf"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'application/pdf',
                'size': len(output.getvalue()),
                'stats': {
                    'total_records': len(df),
                    'pages_estimated': (len(df) // 30) + 2  # Estimation approximative
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export PDF: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_device_info_section(self, device: Device, start_date: datetime, 
                                   end_date: datetime, period_type: str) -> List:
        """Créer la section d'informations de l'appareil pour PDF"""
        elements = []
        
        # Récupérer les infos client et site
        client = Client.query.get(device.client_id) if device.client_id else None
        site = Site.query.get(device.site_id) if device.site_id else None
        
        info_data = [
            ['Information', 'Valeur'],
            ['Appareil', device.nom_appareil],
            ['Type', device.type_appareil],
            ['Système électrique', device.type_systeme.capitalize()],
            ['Client', client.nom_entreprise if client else 'N/A'],
            ['Site', site.nom_site if site else 'N/A'],
            ['Période analysée', period_type.capitalize()],
            ['Date début', start_date.strftime('%d/%m/%Y %H:%M')],
            ['Date fin', end_date.strftime('%d/%m/%Y %H:%M')],
            ['État assignation', device.statut_assignation],
            ['En ligne', 'Oui' if device.en_ligne else 'Non']
        ]
        
        # Créer le tableau
        info_table = Table(info_data, colWidths=[150, 350])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        elements.append(info_table)
        
        return elements
    
    def _create_stats_table(self, stats_df: pd.DataFrame) -> Table:
        """Créer le tableau de statistiques pour PDF"""
        # Convertir DataFrame en liste pour Table
        data = [stats_df.columns.tolist()] + stats_df.values.tolist()
        
        # Créer le tableau
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        return table
    
    def _create_data_table(self, df: pd.DataFrame, type_systeme: str) -> Table:
        """Créer le tableau de données pour PDF"""
        # Sélectionner les colonnes selon le type
        if type_systeme == 'monophase':
            columns = ['Date/Heure', 'Tension (V)', 'Courant (A)', 'Puissance (W)', 'État']
        else:
            columns = ['Date/Heure', 'Tension L1 (V)', 'Tension L2 (V)', 'Tension L3 (V)', 
                      'Puissance Totale (W)', 'État']
        
        # Filtrer les colonnes existantes
        columns = [col for col in columns if col in df.columns]
        
        # Préparer les données
        data = [columns]
        for _, row in df[columns].iterrows():
            row_data = []
            for col in columns:
                if 'Date' in col:
                    row_data.append(row[col].strftime('%d/%m %H:%M') if pd.notna(row[col]) else '')
                elif isinstance(row[col], (int, float)):
                    row_data.append(f"{row[col]:.2f}" if pd.notna(row[col]) else '')
                else:
                    row_data.append(str(row[col]) if pd.notna(row[col]) else '')
            data.append(row_data)
        
        # Créer le tableau
        col_widths = [80] + [60] * (len(columns) - 1)
        table = Table(data, colWidths=col_widths)
        
        # Style du tableau
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#f3f4f6')]),
        ]))
        
        return table
    
    def _create_pdf_graphs(self, df: pd.DataFrame, type_systeme: str) -> List:
        """Créer les graphiques pour PDF"""
        graphs = []
        
        try:
            # Graphique de tension
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if type_systeme == 'monophase':
                if 'Tension (V)' in df.columns:
                    ax.plot(df['Date/Heure'], df['Tension (V)'], label='Tension', color='blue')
                    ax.set_ylabel('Tension (V)')
                    ax.set_title('Évolution de la Tension')
            else:
                # Triphasé
                colors_phases = ['red', 'green', 'blue']
                for i, phase in enumerate(['L1', 'L2', 'L3']):
                    col_name = f'Tension {phase} (V)'
                    if col_name in df.columns:
                        ax.plot(df['Date/Heure'], df[col_name], 
                               label=f'Phase {phase}', color=colors_phases[i])
                ax.set_ylabel('Tension (V)')
                ax.set_title('Évolution des Tensions par Phase')
            
            ax.set_xlabel('Temps')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Convertir en image pour PDF
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100)
            img_buffer.seek(0)
            plt.close()
            
            # Créer l'image pour ReportLab
            img = Image(img_buffer, width=500, height=200)
            graphs.append(img)
            
            # Graphique de puissance
            fig, ax = plt.subplots(figsize=(10, 4))
            
            if type_systeme == 'monophase':
                if 'Puissance (W)' in df.columns:
                    ax.plot(df['Date/Heure'], df['Puissance (W)'], label='Puissance', color='orange')
                    ax.set_ylabel('Puissance (W)')
                    ax.set_title('Évolution de la Puissance')
            else:
                if 'Puissance Totale (W)' in df.columns:
                    ax.plot(df['Date/Heure'], df['Puissance Totale (W)'], 
                           label='Puissance Totale', color='orange')
                    ax.set_ylabel('Puissance (W)')
                    ax.set_title('Évolution de la Puissance Totale')
            
            ax.set_xlabel('Temps')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100)
            img_buffer.seek(0)
            plt.close()
            
            img = Image(img_buffer, width=500, height=200)
            graphs.append(img)
            
            # Graphique spécifique triphasé : déséquilibre
            if type_systeme == 'triphase' and 'Déséquilibre Tension (%)' in df.columns:
                fig, ax = plt.subplots(figsize=(10, 4))
                
                ax.plot(df['Date/Heure'], df['Déséquilibre Tension (%)'], 
                       label='Déséquilibre Tension', color='red', linewidth=1)
                if 'Déséquilibre Courant (%)' in df.columns:
                    ax.plot(df['Date/Heure'], df['Déséquilibre Courant (%)'], 
                           label='Déséquilibre Courant', color='purple', linewidth=1)
                
                ax.set_ylabel('Déséquilibre (%)')
                ax.set_xlabel('Temps')
                ax.set_title('Évolution des Déséquilibres')
                ax.axhline(y=2, color='r', linestyle='--', alpha=0.5, label='Seuil 2%')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                img_buffer = BytesIO()
                plt.savefig(img_buffer, format='png', dpi=100)
                img_buffer.seek(0)
                plt.close()
                
                img = Image(img_buffer, width=500, height=200)
                graphs.append(img)
            
        except Exception as e:
            logger.error(f"Erreur création graphiques PDF: {e}")
        
        return graphs
    
    def _add_page_header(self, canvas, doc):
        """Ajouter en-tête de page PDF"""
        canvas.saveState()
        
        # Logo ou titre de l'entreprise
        canvas.setFont('Helvetica-Bold', 16)
        canvas.setFillColor(HexColor('#1e3a8a'))
        canvas.drawString(30, doc.height + 50, "IoT Energy Monitor")
        
        # Date de génération
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(HexColor('#6b7280'))
        canvas.drawRightString(doc.width + 30, doc.height + 50, 
                               f"Généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Ligne de séparation
        canvas.setStrokeColor(HexColor('#1e3a8a'))
        canvas.setLineWidth(2)
        canvas.line(30, doc.height + 40, doc.width + 30, doc.height + 40)
        
        canvas.restoreState()
    
    # =================== STATISTIQUES ===================
    
    def _calculate_statistics(self, df: pd.DataFrame, type_systeme: str) -> pd.DataFrame:
        """Calculer les statistiques pour un DataFrame"""
        stats = {}
        
        if type_systeme == 'monophase':
            # Statistiques monophasé
            numeric_cols = ['Tension (V)', 'Courant (A)', 'Puissance (W)', 'Énergie (kWh)', 'Température (°C)']
            
            for col in numeric_cols:
                if col in df.columns and df[col].notna().any():
                    stats[col] = {
                        'Minimum': df[col].min(),
                        'Maximum': df[col].max(),
                        'Moyenne': df[col].mean(),
                        'Médiane': df[col].median(),
                        'Écart-type': df[col].std()
                    }
            
            # Consommation totale
            if 'Énergie (kWh)' in df.columns:
                stats['Consommation'] = {
                    'Totale (kWh)': df['Énergie (kWh)'].max() - df['Énergie (kWh)'].min() if df['Énergie (kWh)'].notna().any() else 0
                }
            
        else:
            # Statistiques triphasé
            # Tensions
            for phase in ['L1', 'L2', 'L3']:
                col = f'Tension {phase} (V)'
                if col in df.columns and df[col].notna().any():
                    stats[f'Tension {phase}'] = {
                        'Min': df[col].min(),
                        'Max': df[col].max(),
                        'Moy': df[col].mean(),
                        'Std': df[col].std()
                    }
            
            # Courants
            for phase in ['L1', 'L2', 'L3']:
                col = f'Courant {phase} (A)'
                if col in df.columns and df[col].notna().any():
                    stats[f'Courant {phase}'] = {
                        'Min': df[col].min(),
                        'Max': df[col].max(),
                        'Moy': df[col].mean()
                    }
            
            # Puissance totale
            if 'Puissance Totale (W)' in df.columns and df['Puissance Totale (W)'].notna().any():
                stats['Puissance Totale'] = {
                    'Minimum': df['Puissance Totale (W)'].min(),
                    'Maximum': df['Puissance Totale (W)'].max(),
                    'Moyenne': df['Puissance Totale (W)'].mean()
                }
            
            # Déséquilibres
            if 'Déséquilibre Tension (%)' in df.columns and df['Déséquilibre Tension (%)'].notna().any():
                stats['Déséquilibre'] = {
                    'Tension Max (%)': df['Déséquilibre Tension (%)'].max(),
                    'Tension Moy (%)': df['Déséquilibre Tension (%)'].mean()
                }
                
                if 'Déséquilibre Courant (%)' in df.columns and df['Déséquilibre Courant (%)'].notna().any():
                    stats['Déséquilibre']['Courant Max (%)'] = df['Déséquilibre Courant (%)'].max()
                    stats['Déséquilibre']['Courant Moy (%)'] = df['Déséquilibre Courant (%)'].mean()
        
        # Convertir en DataFrame
        stats_data = []
        for metric, values in stats.items():
            for stat, value in values.items():
                stats_data.append({
                    'Métrique': metric,
                    'Statistique': stat,
                    'Valeur': round(value, 2) if isinstance(value, (int, float)) else value
                })
        
        return pd.DataFrame(stats_data)
    
    # =================== EXPORT MULTIPLE ===================
    
    def _export_multiple_to_excel(self, all_data: Dict[str, pd.DataFrame], devices: List[Device], 
                                  start_date: datetime, end_date: datetime, period_type: str) -> Dict[str, Any]:
        """Export multiple vers Excel avec une feuille par appareil"""
        try:
            output = BytesIO()
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Créer une feuille de résumé
                summary_data = []
                
                for device_name, df in all_data.items():
                    device = next((d for d in devices if d.nom_appareil == device_name), None)
                    if device:
                        summary_data.append({
                            'Appareil': device_name,
                            'Type': device.type_appareil,
                            'Système': device.type_systeme,
                            'Nombre de mesures': len(df),
                            'Période': f"{start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}"
                        })
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Résumé', index=False)
                
                # Ajouter une feuille par appareil
                for device_name, df in all_data.items():
                    # Tronquer le nom si trop long (Excel limite à 31 caractères)
                    sheet_name = device_name[:31] if len(device_name) > 31 else device_name
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
                    # Formater la feuille
                    worksheet = writer.sheets[sheet_name]
                    workbook = writer.book
                    
                    header_format = workbook.add_format({
                        'bold': True,
                        'fg_color': '#1e3a8a',
                        'font_color': 'white'
                    })
                    
                    for col_num, col_name in enumerate(df.columns):
                        worksheet.write(0, col_num, col_name, header_format)
            
            output.seek(0)
            
            filename = f"export_multiple_{period_type}_{start_date.strftime('%Y%m%d')}.xlsx"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'size': len(output.getvalue()),
                'stats': {
                    'total_devices': len(devices),
                    'total_records': sum(len(df) for df in all_data.values()),
                    'period': f"{start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}"
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export multiple Excel: {e}")
            return {'success': False, 'error': str(e)}
    
    def _export_multiple_to_csv(self, all_data: Dict[str, pd.DataFrame], devices: List[Device], 
                                start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Export multiple vers CSV (un seul fichier avec colonne appareil)"""
        try:
            output = BytesIO()
            
            # Combiner tous les DataFrames
            combined_df = pd.DataFrame()
            
            for device_name, df in all_data.items():
                df_copy = df.copy()
                df_copy.insert(0, 'Appareil', device_name)
                combined_df = pd.concat([combined_df, df_copy], ignore_index=True)
            
            # Export CSV
            combined_df.to_csv(output, index=False, encoding='utf-8-sig')
            
            output.seek(0)
            
            filename = f"export_multiple_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'text/csv',
                'size': len(output.getvalue()),
                'stats': {
                    'total_devices': len(devices),
                    'total_records': len(combined_df)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export multiple CSV: {e}")
            return {'success': False, 'error': str(e)}
    
    def _export_multiple_to_pdf(self, all_data: Dict[str, pd.DataFrame], devices: List[Device], 
                                start_date: datetime, end_date: datetime, period_type: str) -> Dict[str, Any]:
        """Export multiple vers PDF avec section par appareil"""
        try:
            output = BytesIO()
            
            # Créer le document PDF
            doc = SimpleDocTemplate(
                output,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            elements = []
            
            # Page de titre
            title = Paragraph(
                f"Rapport Multi-Appareils<br/>Période: {period_type.capitalize()}",
                self.styles['CustomTitle']
            )
            elements.append(title)
            elements.append(Spacer(1, 30))
            
            # Informations générales
            info = Paragraph(
                f"Période analysée: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}<br/>"
                f"Nombre d'appareils: {len(devices)}<br/>"
                f"Date de génération: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                self.styles['InfoStyle']
            )
            elements.append(info)
            elements.append(PageBreak())
            
            # Une section par appareil
            for device_name, df in all_data.items():
                device = next((d for d in devices if d.nom_appareil == device_name), None)
                
                if device:
                    # Titre de section
                    section_title = Paragraph(
                        f"Appareil: {device_name}",
                        self.styles['CustomSubTitle']
                    )
                    elements.append(section_title)
                    elements.append(Spacer(1, 10))
                    
                    # Statistiques de l'appareil
                    stats_df = self._calculate_statistics(df, device.type_systeme)
                    elements.append(self._create_stats_table(stats_df.head(10)))
                    elements.append(Spacer(1, 20))
                    
                    # Échantillon de données
                    elements.append(Paragraph("Échantillon de données", self.styles['Normal']))
                    elements.append(Spacer(1, 10))
                    
                    data_sample = df.head(20)
                    elements.append(self._create_data_table(data_sample, device.type_systeme))
                    
                    elements.append(PageBreak())
            
            # Générer le PDF
            doc.build(elements, onFirstPage=self._add_page_header, onLaterPages=self._add_page_header)
            
            output.seek(0)
            
            filename = f"rapport_multiple_{period_type}_{start_date.strftime('%Y%m%d')}.pdf"
            
            return {
                'success': True,
                'file': output,
                'filename': filename,
                'mime_type': 'application/pdf',
                'size': len(output.getvalue()),
                'stats': {
                    'total_devices': len(devices),
                    'total_records': sum(len(df) for df in all_data.values())
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur export multiple PDF: {e}")
            return {'success': False, 'error': str(e)}
    
    # =================== MÉTHODES UTILITAIRES ===================
    
    def get_available_periods(self, device_id: str) -> Dict[str, Any]:
        """Récupérer les périodes disponibles pour un appareil"""
        try:
            device = Device.query.get(device_id)
            if not device:
                return {'success': False, 'error': 'Appareil non trouvé'}
            
            # Récupérer première et dernière date
            first_record = DeviceData.query.filter_by(appareil_id=device_id)\
                                          .order_by(DeviceData.horodatage.asc()).first()
            last_record = DeviceData.query.filter_by(appareil_id=device_id)\
                                         .order_by(DeviceData.horodatage.desc()).first()
            
            if not first_record or not last_record:
                return {
                    'success': False,
                    'error': 'Aucune donnée disponible pour cet appareil'
                }
            
            # Calculer les périodes disponibles
            available_days = []
            available_months = set()
            available_years = set()
            
            current = first_record.horodatage.date()
            end = last_record.horodatage.date()
            
            while current <= end:
                available_days.append(current.strftime('%Y-%m-%d'))
                available_months.add(current.strftime('%Y-%m'))
                available_years.add(current.year)
                current += timedelta(days=1)
            
            return {
                'success': True,
                'device_name': device.nom_appareil,
                'first_date': first_record.horodatage.isoformat(),
                'last_date': last_record.horodatage.isoformat(),
                'available_periods': {
                    'days': available_days[-30:],  # Derniers 30 jours
                    'months': sorted(list(available_months)),
                    'years': sorted(list(available_years))
                },
                'total_records': DeviceData.query.filter_by(appareil_id=device_id).count()
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération périodes: {e}")
            return {'success': False, 'error': str(e)}