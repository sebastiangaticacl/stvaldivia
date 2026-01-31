"""
Helper para integración con GetNet Web Checkout API
"""
import logging
import requests
import hashlib
import base64
import secrets
from typing import Optional, Dict, Any
from flask import current_app
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache de tokens (expira en 50 minutos, los tokens suelen durar 1 hora)
_token_cache = {
    'access_token': None,
    'expires_at': None
}


def get_getnet_config() -> Dict[str, Any]:
    """Obtiene la configuración de GetNet desde variables de entorno"""
    return {
        'api_base_url': current_app.config.get('GETNET_API_BASE_URL', 'https://checkout.test.getnet.cl'),
        'login': current_app.config.get('GETNET_LOGIN', '7ffbb7bf1f7361b1200b2e8d74e1d76f'),
        'trankey': current_app.config.get('GETNET_TRANKEY', 'SnZP3D63n3I9dH9O'),
        'client_id': current_app.config.get('GETNET_CLIENT_ID'),  # Legacy/OAuth2
        'client_secret': current_app.config.get('GETNET_CLIENT_SECRET'),  # Legacy/OAuth2
        'merchant_id': current_app.config.get('GETNET_MERCHANT_ID'),
        'sandbox': current_app.config.get('GETNET_SANDBOX', True),
        'demo_mode': current_app.config.get('GETNET_DEMO_MODE', False),  # Modo demo para desarrollo
    }


def generate_getnet_signature(login: str, trankey: str, seed: str, nonce: str) -> str:
    """
    Genera firma SHA256 para GetNet
    
    NOTA: Este método es una aproximación basada en patrones comunes.
    DEBE ajustarse según la documentación oficial de GetNet.
    
    Formato típico: SHA256(nonce + seed + trankey)
    """
    # Ajustar según documentación oficial de GetNet
    # Posibles variaciones:
    # - SHA256(nonce + seed + trankey)
    # - SHA256(seed + nonce + trankey)
    # - SHA256(trankey + seed + nonce)
    data_to_hash = f"{nonce}{seed}{trankey}"
    signature = hashlib.sha256(data_to_hash.encode('utf-8')).digest()
    return base64.b64encode(signature).decode('utf-8')


def generate_getnet_auth(login: str, trankey: str) -> Dict[str, str]:
    """
    Genera objeto de autenticación para GetNet
    
    NOTA: Ajustar según documentación oficial de GetNet
    """
    # Generar seed (timestamp ISO 8601)
    seed = datetime.utcnow().isoformat()
    
    # Generar nonce (aleatorio base64)
    nonce_bytes = secrets.token_bytes(16)
    nonce = base64.b64encode(nonce_bytes).decode('utf-8')
    
    # Generar firma
    signature = generate_getnet_signature(login, trankey, seed, nonce)
    
    return {
        'login': login,
        'tranKey': signature,
        'seed': seed,
        'nonce': nonce
    }


def get_getnet_auth_headers() -> Dict[str, str]:
    """
    Obtiene headers de autenticación para GetNet
    Usa Login/Trankey (método principal) o OAuth2 (legacy)
    
    Returns:
        Dict con headers de autenticación
    """
    config = get_getnet_config()
    
    # Priorizar Login/Trankey (método de GetNet)
    if config.get('login') and config.get('trankey'):
        # Headers básicos - GetNet puede requerir autenticación en el body
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    # Fallback a OAuth2 si está configurado
    if config.get('client_id') and config.get('client_secret'):
        access_token = get_getnet_access_token()
        if access_token:
            return {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
    
    logger.error("GetNet credentials no configuradas (ni Login/Trankey ni OAuth2)")
    return {}


def get_getnet_access_token(force_refresh: bool = False) -> Optional[str]:
    """
    Obtiene token de acceso de GetNet usando OAuth2 (método legacy/alternativo)
    Usa cache para evitar solicitudes innecesarias
    
    Args:
        force_refresh: Si es True, fuerza la renovación del token
        
    Returns:
        access_token o None si hay error
    """
    config = get_getnet_config()

    # MODO SOLO LOCAL: No intentar OAuth2 ni conexiones externas
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            return None
    except Exception:
        pass
    
    if not config.get('client_id') or not config.get('client_secret'):
        return None  # No hay credenciales OAuth2, usar Login/Trankey
    
    # Verificar cache
    if not force_refresh and _token_cache['access_token']:
        if _token_cache['expires_at'] and datetime.utcnow() < _token_cache['expires_at']:
            logger.debug("Usando token de GetNet desde cache")
            return _token_cache['access_token']
    
    try:
        # URL de autenticación OAuth2
        auth_url = f"{config['api_base_url']}/auth/oauth/v2/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }
        
        data = {
            'grant_type': 'client_credentials',
            'scope': 'oob',
        }
        
        auth = (config['client_id'], config['client_secret'])
        
        logger.info(f"Obteniendo token OAuth2 de GetNet desde {auth_url}")
        response = requests.post(
            auth_url,
            headers=headers,
            data=data,
            auth=auth,
            timeout=10
        )
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            
            if access_token:
                _token_cache['access_token'] = access_token
                _token_cache['expires_at'] = datetime.utcnow() + timedelta(seconds=expires_in - 600)
                logger.info("✅ Token OAuth2 de GetNet obtenido exitosamente")
                return access_token
        
        logger.error(f"Error al obtener token OAuth2 GetNet: {response.status_code} - {response.text}")
        return None
            
    except Exception as e:
        logger.error(f"Excepción al obtener token OAuth2 GetNet: {e}", exc_info=True)
        return None


def create_getnet_payment(
    amount: float,
    currency: str,
    order_id: str,
    customer_data: Dict[str, Any],
    return_url: str,
    cancel_url: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Crea un payment intent en GetNet Web Checkout
    
    Args:
        amount: Monto en CLP (pesos chilenos)
        currency: Moneda (CLP)
        order_id: ID único de la orden
        customer_data: Datos del cliente
        return_url: URL de retorno después del pago
        cancel_url: URL si se cancela el pago
        metadata: Metadatos adicionales
        
    Returns:
        Dict con payment_id y checkout_url, o None si hay error
    """
    config = get_getnet_config()

    # MODO SOLO LOCAL: forzar modo demo (sin red)
    try:
        if current_app and current_app.config.get('LOCAL_ONLY', True):
            config['demo_mode'] = True
    except Exception:
        pass
    
    # Determinar si usar modo demo
    # Modo demo se activa si:
    # 1. GETNET_DEMO_MODE está explícitamente en 'true'
    # 2. O si no hay PUBLIC_BASE_URL configurado (desarrollo local sin tunneling)
    use_demo_mode = config.get('demo_mode', False)
    
    # Verificar si hay URL pública configurada (necesaria para callbacks reales)
    from urllib.parse import urlparse
    parsed_return = urlparse(return_url)
    is_localhost = parsed_return.netloc in ('127.0.0.1', 'localhost', '0.0.0.0') or parsed_return.netloc.startswith('127.0.0.1:') or parsed_return.netloc.startswith('localhost:')
    
    # Si no hay PUBLIC_BASE_URL y es localhost, forzar modo demo
    public_base_url = current_app.config.get('PUBLIC_BASE_URL') if current_app else None
    if not public_base_url and is_localhost:
        use_demo_mode = True
        logger.info(f"🔧 MODO DEMO activado automáticamente: URL localhost detectada sin PUBLIC_BASE_URL")
    
    # Modo demo: simular respuesta exitosa para desarrollo
    if use_demo_mode:
        logger.info(f"🔧 MODO DEMO: Simulando pago GetNet para order_id={order_id}")
        # En modo demo, redirigir directamente al callback con payment_id
        # return_url ya incluye el session_id en la ruta: /ecommerce/payment/callback/{session_id}
        # Solo agregamos los parámetros de query
        from urllib.parse import urlunparse, parse_qs, urlencode
        query_params = parse_qs(parsed_return.query)
        query_params['payment_id'] = [f'DEMO-{order_id}']
        query_params['status'] = ['approved']
        new_query = urlencode(query_params, doseq=True)
        demo_checkout_url = urlunparse((
            parsed_return.scheme, parsed_return.netloc, parsed_return.path,
            parsed_return.params, new_query, parsed_return.fragment
        ))
        return {
            'payment_id': f'DEMO-{order_id}',
            'checkout_url': demo_checkout_url,
            'payment_data': {
                'status': 'demo',
                'message': 'Modo demo activado'
            }
        }
    
    headers = get_getnet_auth_headers()
    
    if not headers:
        logger.error("No se pudo obtener headers de autenticación de GetNet")
        return None
    
    try:
        # Generar autenticación con Login/Trankey
        auth = generate_getnet_auth(config['login'], config['trankey'])
        
        # Preparar datos para GetNet Web Checkout
        # NOTA: Ajustar estructura según documentación oficial de GetNet
        # Esta es una aproximación basada en patrones comunes
        payment_data = {
            'auth': auth,
            'payment': {
                'reference': order_id,
                'amount': {
                    'currency': currency,  # 'CLP' para Chile
                    'total': int(amount)  # Monto en pesos (CLP no usa decimales)
                },
                'description': f'Pago de entradas - {order_id}'
            },
            'expiration': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            'returnUrl': return_url,
            'cancelUrl': cancel_url,
            'buyer': {
                'document': customer_data.get('document_number', ''),
                'documentType': 'CC',  # CC=Cédula, NIT=NIT, CE=Cédula Extranjería
                'name': customer_data.get('first_name', ''),
                'surname': customer_data.get('last_name', ''),
                'email': customer_data.get('email', ''),
                'mobile': customer_data.get('phone_number', ''),
                'address': {
                    'street': customer_data.get('address', ''),
                    'city': customer_data.get('city', 'Santiago'),
                    'country': 'CL',
                    'phone': customer_data.get('phone_number', '')
                }
            }
        }
        
        # Agregar metadata si existe
        if metadata:
            payment_data['metadata'] = metadata
        
        # Endpoint para crear pago
        # GetNet usa PlaceToPay como base, que típicamente usa /api/collect
        # Probar primero con el endpoint estándar de PlaceToPay
        payment_url = f"{config['api_base_url']}/api/collect"
        
        # Si falla, se puede intentar con:
        # - /api/v1/payment
        # - /api/payment
        # - /checkout/api/collect
        
        logger.info(f"Creando pago en GetNet: order_id={order_id}, amount={amount}, endpoint={payment_url}")
        logger.info(f"Headers: {list(headers.keys())}")
        logger.info(f"Payment data keys: {list(payment_data.keys())}")
        logger.debug(f"Payment data completo: {payment_data}")
        
        # Validar que los datos requeridos estén presentes
        if not payment_data.get('auth'):
            logger.error("Falta objeto 'auth' en payment_data")
            return None
        if not payment_data.get('payment'):
            logger.error("Falta objeto 'payment' en payment_data")
            return None
        if not payment_data.get('returnUrl'):
            logger.error("Falta 'returnUrl' en payment_data")
            return None
        
        try:
            response = requests.post(
                payment_url,
                json=payment_data,
                headers=headers,
                timeout=30
            )
        except requests.exceptions.Timeout:
            logger.error(f"Timeout al conectar con GetNet: {payment_url}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Error de conexión con GetNet: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de request a GetNet: {e}")
            return None
        
        logger.info(f"Respuesta GetNet: status={response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        logger.info(f"Response text (primeros 1000 chars): {response.text[:1000]}")
        
        # Log detallado del contenido de la respuesta
        if response.text:
            try:
                response_json = response.json()
                logger.info(f"Response JSON keys: {list(response_json.keys()) if isinstance(response_json, dict) else 'No es dict'}")
            except:
                pass
        
        if response.status_code in [200, 201]:
            try:
                payment_response = response.json()
            except ValueError as e:
                logger.error(f"GetNet retornó respuesta no-JSON: {response.text[:500]}")
                return None
            
            # GetNet típicamente retorna requestId y processUrl
            payment_id = (
                payment_response.get('requestId') or
                payment_response.get('request_id') or
                payment_response.get('payment_id') or 
                payment_response.get('id')
            )
            checkout_url = (
                payment_response.get('processUrl') or
                payment_response.get('process_url') or
                payment_response.get('checkout_url') or 
                payment_response.get('redirect_url') or 
                payment_response.get('url')
            )
            
            if payment_id and checkout_url:
                logger.info(f"✅ Pago creado en GetNet: payment_id={payment_id}")
                return {
                    'payment_id': payment_id,
                    'checkout_url': checkout_url,
                    'payment_data': payment_response
                }
            else:
                logger.error(f"GetNet no retornó payment_id o checkout_url")
                logger.error(f"Response completa: {payment_response}")
                logger.error(f"payment_id encontrado: {payment_id}")
                logger.error(f"checkout_url encontrado: {checkout_url}")
                return None
        else:
            logger.error(f"Error al crear pago en GetNet: status={response.status_code}")
            logger.error(f"Response headers: {dict(response.headers)}")
            logger.error(f"Response text (primeros 2000 chars): {response.text[:2000]}")
            
            # Si es 403, puede ser que el endpoint o la autenticación sean incorrectos
            if response.status_code == 403:
                logger.error("⚠️ 403 Forbidden: Posibles causas:")
                logger.error("  1. Endpoint incorrecto (probablemente)")
                logger.error("  2. Autenticación incorrecta (firma SHA256)")
                logger.error("  3. Estructura del request incorrecta")
                logger.error("  4. Credenciales sin permisos para este endpoint")
                logger.error(f"  Endpoint usado: {payment_url}")
                logger.error(f"  Base URL: {config['api_base_url']}")
            
            # Intentar parsear error si es JSON
            try:
                error_data = response.json()
                logger.error(f"Error JSON: {error_data}")
            except:
                logger.error("Respuesta no es JSON (probablemente HTML de error)")
            
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Excepción de red al crear pago GetNet: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Excepción al crear pago GetNet: {e}", exc_info=True)
        return None


def get_getnet_payment_status(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el estado de un pago en GetNet
    
    Args:
        payment_id: ID del pago en GetNet
        
    Returns:
        Dict con información del pago o None si hay error
    """
    config = get_getnet_config()
    
    # En modo demo, si el payment_id empieza con DEMO-, retornar estado simulado
    if config.get('demo_mode') and payment_id and payment_id.startswith('DEMO-'):
        logger.info(f"Modo demo: simulando estado de pago para {payment_id}")
        return {
            'status': 'APPROVED',
            'payment_id': payment_id,
            'requestId': payment_id,
            'transaction_id': f'DEMO-TXN-{payment_id}',
            'auth_code': 'DEMO-AUTH',
            'message': 'Pago simulado en modo demo'
        }
    
    headers = get_getnet_auth_headers()
    
    if not headers:
        logger.error("No se pudo obtener headers de autenticación de GetNet")
        return None
    
    try:
        # Endpoint para consultar estado del pago
        # NOTA: Ajustar según documentación oficial de GetNet
        payment_status_url = f"{config['api_base_url']}/v1/payments/{payment_id}"
        
        logger.debug(f"Consultando estado de pago GetNet: payment_id={payment_id}, endpoint={payment_status_url}")
        response = requests.get(
            payment_status_url,
            headers=headers,
            timeout=10
        )
        
        logger.debug(f"Respuesta consulta estado: status={response.status_code}")
        
        if response.status_code == 200:
            payment_data = response.json()
            logger.debug(f"Estado de pago GetNet: {payment_data.get('status')}")
            return payment_data
        else:
            logger.error(f"Error al consultar estado de pago GetNet: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Excepción de red al consultar pago GetNet: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Excepción al consultar pago GetNet: {e}", exc_info=True)
        return None


def is_payment_approved(payment_status: Dict[str, Any]) -> bool:
    """
    Verifica si un pago está aprobado según el estado de GetNet
    
    Args:
        payment_status: Dict con información del pago de GetNet
        
    Returns:
        True si el pago está aprobado
    """
    status = payment_status.get('status', '').upper()
    return status in ['APPROVED', 'APROBADO', 'SUCCESS', 'SUCCESSFUL']


def extract_payment_info(payment_status: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae información relevante del pago de GetNet
    
    Args:
        payment_status: Dict con información del pago de GetNet
        
    Returns:
        Dict con información extraída
    """
    return {
        'payment_id': payment_status.get('payment_id') or payment_status.get('id'),
        'status': payment_status.get('status', '').upper(),
        'transaction_id': payment_status.get('transaction_id') or payment_status.get('transactionId'),
        'auth_code': payment_status.get('auth_code') or payment_status.get('authCode') or payment_status.get('authorization_code'),
        'amount': payment_status.get('amount', {}).get('value', 0) / 100 if isinstance(payment_status.get('amount'), dict) else payment_status.get('amount', 0),
        'currency': payment_status.get('amount', {}).get('currency', 'CLP') if isinstance(payment_status.get('amount'), dict) else 'CLP',
        'payment_method': payment_status.get('payment_method') or payment_status.get('paymentMethod'),
        'created_at': payment_status.get('created_at') or payment_status.get('createdAt'),
    }

