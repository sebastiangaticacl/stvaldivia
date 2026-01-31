"""
Cliente extendido para PHP POS API con métodos para el kiosko
Incluye create_sale que no está en el cliente base
"""
import requests
import logging
from flask import current_app
import os

logger = logging.getLogger(__name__)


class PHPPosKioskClient:
    """Cliente para interactuar con PHP POS API desde el kiosko"""
    
    def __init__(self, base_url=None, api_key=None):
        if base_url and api_key:
            self.base_url = base_url
            self.api_key = api_key
        else:
            # Intentar obtener desde configuración de Flask
            try:
                self.base_url = current_app.config.get('BASE_API_URL') or os.environ.get('BASE_API_URL', 'https://clubbb.phppointofsale.com/index.php/api/v1')
                self.api_key = current_app.config.get('API_KEY') or os.environ.get('API_KEY')
            except:
                self.base_url = os.environ.get('BASE_API_URL', 'https://clubbb.phppointofsale.com/index.php/api/v1')
                self.api_key = os.environ.get('API_KEY')
        
        # API key opcional en modo LOCAL_ONLY
        # if not self.api_key:
        #     logger.warning("⚠️  PHP_POS_API_KEY no configurada. Las llamadas a la API fallarán.")
    
    def _get_headers(self):
        """Obtiene los headers para las peticiones a la API"""
        return {
            'x-api-key': self.api_key,
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def create_sale(self, items, total, payment_type="Manual", customer_id=None, employee_id=None, register_id=None):
        """
        Crea una venta en PHP POS
        
        Args:
            items: Lista de diccionarios con formato:
                [
                    {
                        'item_id': '123',
                        'quantity': 2,
                        'price': 5000.0
                    },
                    ...
                ]
            total: Total de la venta
            payment_type: Tipo de pago
            customer_id: ID del cliente (opcional)
            employee_id: ID del empleado/cajero (opcional)
            register_id: ID de la caja/registro (opcional)
        
        Returns:
            dict: {'sale_id': '12345', 'success': True} o {'success': False, 'error': '...'}
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'API key no configurada'
            }
        
        try:
            url = f"{self.base_url}/sales"
            
            cart_items = []
            for item in items:
                cart_item = {
                    'item_id': str(item.get('item_id', '')),
                    'quantity': int(item.get('quantity', 1)),
                    'unit_price': float(item.get('price', 0))
                }
                if item.get('variation_id'):
                    cart_item['variation_id'] = item.get('variation_id')
                cart_items.append(cart_item)
            
            payload = {
                'cart_items': cart_items,
                'mode': 'sale',
            }
            
            payments = [{
                'payment_type': payment_type,
                'payment_amount': float(total)
            }]
            payload['payments'] = payments
            
            if customer_id:
                payload['customer_id'] = customer_id
            if employee_id:
                payload['employee_id'] = employee_id
            if register_id:
                try:
                    if isinstance(register_id, str) and register_id.isdigit():
                        payload['register_id'] = int(register_id)
                    elif isinstance(register_id, (int, float)):
                        payload['register_id'] = int(register_id)
                    else:
                        payload['register_id'] = register_id
                except:
                    payload['register_id'] = register_id
            
            logger.info(f"Creando venta en PHP POS: {url}")
            
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=15
            )
            
            # Verificar Content-Type antes de parsear JSON
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' not in content_type:
                error_msg = f"La API devolvió HTML en lugar de JSON. Status: {response.status_code}, Content-Type: {content_type}"
                response_text = response.text[:500] if response.text else 'Sin contenido'
                logger.error(f"❌ {error_msg}")
                logger.error(f"Respuesta (primeros 500 caracteres): {response_text}")
                return {
                    'success': False,
                    'error': f'Error del servidor: La API devolvió una respuesta no válida (Status {response.status_code}). Por favor, intenta nuevamente.',
                    'sale_id': None
                }
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                logger.error(f"❌ Error HTTP al crear venta: {e}")
                logger.error(f"Respuesta: {response.text[:500]}")
                return {
                    'success': False,
                    'error': f'Error del servidor: {response.status_code}. Por favor, intenta nuevamente.',
                    'sale_id': None
                }
            
            try:
                data = response.json()
            except ValueError as e:
                error_msg = f"Error al parsear JSON de la respuesta: {e}"
                response_text = response.text[:500] if response.text else 'Sin contenido'
                logger.error(f"❌ {error_msg}")
                logger.error(f"Respuesta (primeros 500 caracteres): {response_text}")
                return {
                    'success': False,
                    'error': 'Error al procesar la respuesta del servidor. Por favor, intenta nuevamente.',
                    'sale_id': None
                }
            
            logger.debug(f"Respuesta completa de PHP POS: {data}")
            
            sale_id = data.get('sale_id')
            
            if sale_id == 0 or sale_id is None:
                logger.error(f"❌ Venta no se creó correctamente en PHP POS (sale_id={sale_id})")
                return {
                    'success': False,
                    'error': f'Venta no se creó correctamente (sale_id={sale_id}). Revisar formato del payload.',
                    'sale_id': None,
                    'data': data
                }
            
            sale_id = str(sale_id).strip()
            
            if sale_id and sale_id != '0' and sale_id != 'None' and sale_id.isdigit():
                receipt_url = data.get('receipt_url', '')
                receipt_code = None
                if receipt_url:
                    import re
                    match = re.search(r'/r/([^/?]+)', receipt_url)
                    if match:
                        receipt_code = match.group(1)
                        logger.info(f"✅ Código de recibo extraído: {receipt_code}")
                
                logger.info(f"✅ Venta creada exitosamente en PHP POS: sale_id={sale_id}, receipt_code={receipt_code}")
                return {
                    'success': True,
                    'sale_id': sale_id,
                    'receipt_code': receipt_code,
                    'receipt_url': receipt_url,
                    'data': data
                }
            else:
                logger.warning(f"⚠️  sale_id inválido: {sale_id}")
                return {
                    'success': False,
                    'error': f'sale_id inválido: {sale_id}',
                    'sale_id': None,
                    'data': data
                }
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Error HTTP al crear venta: {e}"
            status_code = e.response.status_code if hasattr(e, 'response') and hasattr(e.response, 'status_code') else None
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_msg += f" - Respuesta: {e.response.text}"
                logger.error(f"Respuesta completa del error: {e.response.text}")
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'status_code': status_code
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al crear venta en PHP POS: {e}")
            return {
                'success': False,
                'error': f'Error de conexión: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error inesperado al crear venta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_item(self, item_id):
        """Obtiene información de un item desde PHP POS"""
        if not self.api_key:
            logger.warning("API key no configurada para get_item")
            return None
        
        try:
            url = f"{self.base_url}/items/{item_id}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 404:
                logger.debug(f"Item {item_id} no encontrado")
            else:
                logger.error(f"Error HTTP al obtener item {item_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al obtener item {item_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener item {item_id}: {e}")
            return None
    
    def get_items(self, limit=1000, category=None):
        """Obtiene lista de items/productos desde PHP POS"""
        if not self.api_key:
            logger.warning("API key no configurada para get_items")
            return []
        
        try:
            url = f"{self.base_url}/items"
            params = {'limit': limit}
            if category:
                params['category'] = category
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=15
            )
            
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, dict):
                items = data.get('items', data.get('data', []))
            else:
                items = data
            
            logger.info(f"✅ Obtenidos {len(items)} items desde PHP POS")
            return items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener items desde PHP POS: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado al obtener items: {e}")
            return []
    
    def get_item_kits(self, limit=1000):
        """Obtiene lista de Item Kits desde PHP POS"""
        if not self.api_key:
            logger.warning("API key no configurada para get_item_kits")
            return []
        
        try:
            # Intentar diferentes endpoints posibles
            endpoints = ['item_kits', 'item-kits', 'itemkits', 'kits']
            
            for endpoint in endpoints:
                try:
                    url = f"{self.base_url}/{endpoint}"
                    response = requests.get(
                        url,
                        headers=self._get_headers(),
                        params={'limit': limit},
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if isinstance(data, dict):
                            kits = data.get('item_kits', data.get('kits', data.get('data', [])))
                        else:
                            kits = data
                        
                        logger.info(f"✅ Obtenidos {len(kits)} item kits desde PHP POS (endpoint: /{endpoint})")
                        return kits
                except requests.exceptions.HTTPError:
                    continue
                except Exception:
                    continue
            
            logger.warning("⚠️  No se encontró endpoint de Item Kits en PHP POS")
            return []
            
        except Exception as e:
            logger.error(f"Error inesperado al obtener item kits: {e}")
            return []
    
    def get_sale(self, sale_id):
        """Obtiene información de una venta desde PHP POS"""
        if not self.api_key:
            logger.warning("API key no configurada para get_sale")
            return None
        
        try:
            url = f"{self.base_url}/sales/{sale_id}"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if hasattr(e.response, 'status_code') and e.response.status_code == 404:
                logger.debug(f"Venta {sale_id} no encontrada")
            else:
                logger.error(f"Error HTTP al obtener venta {sale_id}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red al obtener venta {sale_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado al obtener venta {sale_id}: {e}")
            return None



