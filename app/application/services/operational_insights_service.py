"""
Servicio para obtener insights operativos del día
Usado por el bot de IA como contexto privado
"""
import os
import requests
from typing import Optional, Dict, Any
from flask import current_app


class OperationalInsightsService:
    """Servicio para obtener datos operativos internos"""
    
    @staticmethod
    def _is_production() -> bool:
        """Detecta si estamos en producción usando el mismo criterio del proyecto"""
        try:
            from app.helpers.production_check import is_production
            return is_production()
        except ImportError:
            # Fallback si no existe production_check
            is_cloud_run = bool(
                os.environ.get('K_SERVICE') or 
                os.environ.get('GAE_ENV') or 
                os.environ.get('CLOUD_RUN_SERVICE')
            )
            flask_env = os.environ.get('FLASK_ENV', '').lower()
            return is_cloud_run or (flask_env == 'production')
    
    @staticmethod
    def get_daily_summary() -> Optional[Dict[str, Any]]:
        """
        Obtiene el resumen operativo del día desde el endpoint interno.
        
        Returns:
            Dict con datos operativos o None si falla
        """
        try:
            api_key = os.environ.get('BIMBA_INTERNAL_API_KEY')
            
            if not api_key:
                return None
            
            # Determinar URL base según entorno
            base_url = os.environ.get('BIMBA_INTERNAL_API_BASE_URL')
            
            if not base_url:
                if OperationalInsightsService._is_production():
                    # En producción sin URL configurada, no llamar API operacional
                    try:
                        current_app.logger.warning(
                            "BIMBA_INTERNAL_API_BASE_URL no configurada en producción. "
                            "OperationalInsightsService retornará None."
                        )
                    except:
                        pass  # Si no hay contexto de app, continuar silenciosamente
                    return None
                else:
                    # En desarrollo, usar localhost por defecto
                    base_url = 'http://127.0.0.1:5001'
            
            url = f"{base_url}/api/v1/operational/summary"
            
            headers = {
                'X-API-KEY': api_key
            }
            
            # Timeout más corto (2 segundos) - si es lento, mejor no usar esos datos
            response = requests.get(url, headers=headers, timeout=2)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            if data.get('status') != 'ok':
                return None
            
            return data
            
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
        except Exception:
            return None


