"""
Cliente para interactuar con la API de SumUp
"""
import requests
import logging
from flask import current_app
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SumUpClient:
    """Cliente para interactuar con la API de SumUp"""
    
    BASE_URL = "https://api.sumup.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el cliente SumUp
        
        Args:
            api_key: API key de SumUp (si no se provee, intenta obtener desde config)
        """
        if api_key:
            self.api_key = api_key
        else:
            # Intentar obtener desde configuración de Flask o variables de entorno
            try:
                self.api_key = current_app.config.get('SUMUP_API_KEY') or os.environ.get('SUMUP_API_KEY')
            except RuntimeError:
                # Fuera de contexto Flask, usar variables de entorno
                self.api_key = os.environ.get('SUMUP_API_KEY')
        
        if not self.api_key:
            logger.warning("⚠️  SUMUP_API_KEY no configurada. Las llamadas a la API fallarán.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene los headers para las peticiones a la API"""
        if not self.api_key:
            raise ValueError("API key de SumUp no configurada")
        
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def create_checkout(
        self,
        amount: float,
        currency: str = 'CLP',
        checkout_reference: Optional[str] = None,
        description: Optional[str] = None,
        return_url: Optional[str] = None,
        customer_id: Optional[str] = None,
        merchant_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea un checkout en SumUp
        
        Args:
            amount: Monto del pago
            currency: Moneda (por defecto CLP)
            checkout_reference: Referencia única del checkout (si no se provee, se genera)
            description: Descripción del checkout
            return_url: URL a la que redirigir después del pago
            customer_id: ID del cliente (opcional)
            merchant_code: Código del comerciante (opcional)
        
        Returns:
            dict: Respuesta de la API con información del checkout
        """
        # MODO SOLO LOCAL: no conectar con SumUp (simular checkout)
        try:
            if current_app and current_app.config.get('LOCAL_ONLY', True):
                import uuid
                demo_id = checkout_reference or f"DEMO-{uuid.uuid4().hex[:12]}"
                return {
                    'success': True,
                    'data': {
                        'id': demo_id,
                        'status': 'demo',
                        'amount': float(amount),
                        'currency': currency,
                        'description': description,
                        'return_url': return_url,
                        'checkout_url': return_url or ''
                    }
                }
        except Exception:
            # Si no hay contexto Flask, continuar con comportamiento normal
            pass

        if not self.api_key:
            return {
                'success': False,
                'error': 'API key no configurada'
            }
        
        try:
            url = f"{self.BASE_URL}/v0.1/checkouts"
            
            payload = {
                'amount': float(amount),
                'currency': currency
            }
            
            if checkout_reference:
                payload['checkout_reference'] = checkout_reference
            
            if description:
                payload['description'] = description
            
            if return_url:
                payload['return_url'] = return_url
            
            if customer_id:
                payload['customer_id'] = customer_id
            
            if merchant_code:
                payload['merchant_code'] = merchant_code
            
            logger.info(f"Creando checkout SumUp: {url}")
            logger.debug(f"Payload: {payload}")
            
            # Resolver DNS manualmente antes de conectar para evitar problemas con eventlet/greendns
            # Esto es similar a la solución usada en email_ticket_helper.py
            # Resolver DNS con socket estándar (no eventlet) para poblar el cache de DNS del sistema
            import socket
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            
            try:
                logger.debug(f"Resolviendo DNS para {hostname}...")
                # Usar socket estándar (no eventlet) para resolver DNS
                # Esto evita el timeout de greendns y puebla el cache de DNS del sistema
                resolved_ip = socket.gethostbyname(hostname)
                logger.debug(f"✅ DNS resuelto: {hostname} -> {resolved_ip}")
            except Exception as dns_error:
                logger.warning(f"⚠️ No se pudo resolver DNS manualmente: {dns_error}")
                # Continuar de todas formas, requests podría resolverlo
            
            # Intentar conexión con retry para manejar problemas de DNS intermitentes
            max_retries = 3
            last_error = None
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Usar timeout más largo para conexión y lectura (conexión: 30s, lectura: 30s)
                    # Usar URL original con hostname (no IP) para que el certificado SSL funcione
                    response = requests.post(
                        url,
                        json=payload,
                        headers=self._get_headers(),
                        timeout=(30, 30)  # (connect timeout, read timeout)
                    )
                    # Si llegamos aquí, la conexión fue exitosa
                    break
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    last_error = e
                    if attempt < max_retries:
                        wait_time = attempt * 2  # Backoff exponencial: 2s, 4s
                        logger.warning(f"⚠️  Intento {attempt}/{max_retries} falló: {e}. Reintentando en {wait_time}s...")
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ Todos los intentos fallaron después de {max_retries} intentos")
                        raise
            
            # Verificar Content-Type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' not in content_type:
                error_msg = f"La API devolvió contenido no JSON. Status: {response.status_code}"
                response_text = response.text[:500] if response.text else 'Sin contenido'
                logger.error(f"❌ {error_msg}")
                logger.error(f"Respuesta: {response_text}")
                return {
                    'success': False,
                    'error': f'Error del servidor: La API devolvió una respuesta no válida (Status {response.status_code})',
                    'status_code': response.status_code
                }
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                error_text = response.text[:500] if hasattr(response, 'text') else str(e)
                logger.error(f"❌ Error HTTP al crear checkout: {e}")
                logger.error(f"Respuesta: {error_text}")
                
                # Intentar parsear error JSON si es posible
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_data.get('error', str(e)))
                except:
                    error_message = f'Error del servidor: {response.status_code}'
                
                return {
                    'success': False,
                    'error': error_message,
                    'status_code': response.status_code
                }
            
            try:
                data = response.json()
                logger.info(f"✅ Checkout creado exitosamente: {data.get('id')}")
                return {
                    'success': True,
                    'data': data
                }
            except ValueError as e:
                error_msg = f"Error al parsear JSON de la respuesta: {e}"
                response_text = response.text[:500] if response.text else 'Sin contenido'
                logger.error(f"❌ {error_msg}")
                logger.error(f"Respuesta: {response_text}")
                return {
                    'success': False,
                    'error': 'Error al procesar la respuesta del servidor',
                    'status_code': response.status_code
                }
            
        except (requests.exceptions.RequestException, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            error_msg = str(e)
            if 'NameResolutionError' in error_msg or 'Failed to resolve' in error_msg:
                error_msg = 'Error de conexión: No se pudo resolver el servidor de SumUp. Por favor intenta de nuevo.'
            logger.error(f"Error de red al crear checkout en SumUp: {e}")
            return {
                'success': False,
                'error': f'Error de conexión: {error_msg}'
            }
        except Exception as e:
            logger.error(f"Error inesperado al crear checkout: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_checkout(self, checkout_id: str) -> Dict[str, Any]:
        """
        Obtiene información de un checkout
        
        Args:
            checkout_id: ID del checkout
        
        Returns:
            dict: Información del checkout
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'API key no configurada'
            }
        
        try:
            url = f"{self.BASE_URL}/v0.1/checkouts/{checkout_id}"
            
            # Usar timeout más largo para conexión y lectura
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=(30, 30)  # (connect timeout, read timeout)
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data
            }
            
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and hasattr(e.response, 'status_code') and e.response.status_code == 404:
                logger.debug(f"Checkout {checkout_id} no encontrado")
                return {
                    'success': False,
                    'error': 'Checkout no encontrado',
                    'status_code': 404
                }
            else:
                logger.error(f"Error HTTP al obtener checkout {checkout_id}: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'status_code': e.response.status_code if hasattr(e, 'response') else None
                }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al obtener checkout {checkout_id}: {e}")
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error inesperado al obtener checkout {checkout_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_checkout(self, checkout_id: str, payment_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un checkout (inicia el flujo de pago)
        
        Args:
            checkout_id: ID del checkout
            payment_data: Datos adicionales del pago (opcional)
        
        Returns:
            dict: Resultado del procesamiento
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'API key no configurada'
            }
        
        try:
            url = f"{self.BASE_URL}/v0.1/checkouts/{checkout_id}/process"
            
            payload = payment_data or {}
            
            # Usar timeout más largo para conexión y lectura
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=(30, 30)  # (connect timeout, read timeout)
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'success': True,
                'data': data
            }
            
        except requests.exceptions.HTTPError as e:
            error_text = response.text[:500] if hasattr(e, 'response') and hasattr(e.response, 'text') else str(e)
            logger.error(f"Error HTTP al procesar checkout {checkout_id}: {e}")
            logger.error(f"Respuesta: {error_text}")
            
            try:
                error_data = e.response.json() if hasattr(e, 'response') else {}
                error_message = error_data.get('message', error_data.get('error', str(e)))
            except:
                error_message = f'Error del servidor: {e.response.status_code if hasattr(e, "response") else "unknown"}'
            
            return {
                'success': False,
                'error': error_message,
                'status_code': e.response.status_code if hasattr(e, 'response') else None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al procesar checkout {checkout_id}: {e}")
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error inesperado al procesar checkout {checkout_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

