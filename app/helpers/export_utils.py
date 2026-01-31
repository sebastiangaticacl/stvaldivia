"""
Utilidades para exportar datos del sistema
Formato CSV, JSON y otros
"""
import csv
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import StringIO
from flask import Response
from .logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """Exportador de datos en diferentes formatos"""
    
    @staticmethod
    def export_to_csv(data: List[Dict[str, Any]], filename: str = "export") -> Response:
        """
        Exporta datos a CSV
        
        Args:
            data: Lista de diccionarios con los datos
            filename: Nombre del archivo (sin extensión)
            
        Returns:
            Flask Response con el CSV
        """
        if not data:
            return Response(
                "No hay datos para exportar",
                mimetype='text/plain',
                status=404
            )
        
        # Obtener headers de las claves del primer elemento
        fieldnames = list(data[0].keys())
        
        # Crear CSV en memoria
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        
        # Preparar respuesta
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
        
        output.close()
        return response
    
    @staticmethod
    def export_to_json(data: List[Dict[str, Any]], filename: str = "export") -> Response:
        """
        Exporta datos a JSON
        
        Args:
            data: Lista de diccionarios con los datos
            filename: Nombre del archivo (sin extensión)
            
        Returns:
            Flask Response con el JSON
        """
        json_data = {
            'export_date': datetime.now().isoformat(),
            'count': len(data),
            'data': data
        }
        
        response = Response(
            json.dumps(json_data, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"'
            }
        )
        
        return response
    
    @staticmethod
    def export_logs_csv(logs: List[List[str]], filename: str = "logs") -> Response:
        """
        Exporta logs (formato específico para logs del sistema)
        
        Args:
            logs: Lista de listas con los logs
            filename: Nombre del archivo
            
        Returns:
            Flask Response con el CSV
        """
        if not logs:
            return Response(
                "No hay logs para exportar",
                mimetype='text/plain',
                status=404
            )
        
        # Header esperado para logs
        header = ['sale_id', 'item_name', 'qty', 'bartender', 'barra', 'timestamp']
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        writer.writerows(logs)
        
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            }
        )
        
        output.close()
        return response


class MetricsExporter:
    """Exportador de métricas y estadísticas"""
    
    @staticmethod
    def export_delivery_metrics(deliveries: List[Dict[str, Any]], format: str = 'csv') -> Response:
        """
        Exporta métricas de entregas
        
        Args:
            deliveries: Lista de entregas
            format: Formato de exportación ('csv' o 'json')
            
        Returns:
            Flask Response con los datos exportados
        """
        if format.lower() == 'json':
            return DataExporter.export_to_json(deliveries, "delivery_metrics")
        else:
            return DataExporter.export_to_csv(deliveries, "delivery_metrics")
    
    @staticmethod
    def generate_summary_report(deliveries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera un reporte resumen de entregas
        
        Args:
            deliveries: Lista de entregas
            
        Returns:
            dict con estadísticas resumidas
        """
        if not deliveries:
            return {
                'total': 0,
                'date_range': None,
                'summary': {}
            }
        
        # Agrupar por fecha
        by_date = {}
        by_bartender = {}
        by_barra = {}
        total_items = 0
        
        for delivery in deliveries:
            # Por fecha
            date = delivery.get('timestamp', '').split(' ')[0] if delivery.get('timestamp') else 'Unknown'
            by_date[date] = by_date.get(date, 0) + 1
            
            # Por bartender
            bartender = delivery.get('bartender', 'Unknown')
            by_bartender[bartender] = by_bartender.get(bartender, 0) + 1
            
            # Por barra
            barra = delivery.get('barra', 'Unknown')
            by_barra[barra] = by_barra.get(barra, 0) + 1
            
            # Total items
            qty = delivery.get('qty', 0)
            try:
                total_items += int(qty) if isinstance(qty, (int, str)) else 0
            except (ValueError, TypeError):
                pass
        
        # Obtener rango de fechas
        dates = sorted([d for d in by_date.keys() if d != 'Unknown'])
        date_range = {
            'start': dates[0] if dates else None,
            'end': dates[-1] if dates else None
        }
        
        return {
            'total': len(deliveries),
            'total_items': total_items,
            'date_range': date_range,
            'by_date': by_date,
            'by_bartender': by_bartender,
            'by_barra': by_barra,
            'generated_at': datetime.now().isoformat()
        }














