"""
Helper para GetNet basado en PlaceToPay API
GetNet usa PlaceToPay como base, por lo que la estructura es similar
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


def generate_placetopay_signature(login: str, trankey: str, seed: str, nonce: str) -> str:
    """
    Genera firma SHA1 para PlaceToPay/GetNet (según ejemplo oficial Java)
    
    Formato PlaceToPay estándar: SHA1(nonce + seed + trankey)
    NOTA: El ejemplo oficial de Java usa SHA1, no SHA256
    """
    # Usar nonce sin codificar para el hash (según ejemplo Java)
    # En Java: Utils.sha1(this.getNonce(false)+this.getSeed()+this.tranKey)
    data_to_hash = f"{nonce}{seed}{trankey}"
    signature = hashlib.sha1(data_to_hash.encode('utf-8')).digest()
    return base64.b64encode(signature).decode('utf-8')


def generate_placetopay_auth(login: str, trankey: str) -> Dict[str, str]:
    """
    Genera objeto de autenticación para PlaceToPay/GetNet
    
    Estructura estándar de PlaceToPay (según ejemplo oficial Java):
    {
        "login": "login_value",
        "tranKey": "signature_sha1_base64",
        "seed": "ISO8601_timestamp",
        "nonce": "base64_random"
    }
    
    NOTA: El nonce se codifica en base64 para enviarlo, pero para el hash se usa sin codificar
    """
    # Seed: timestamp ISO 8601 con formato yyyy-MM-dd'T'HH:mmZ (según ejemplo Java)
    # Java usa: new SimpleDateFormat("yyyy-MM-dd'T'HH:mmZ", Locale.getDefault())
    # Formato ejemplo: 2024-12-26T05:30-0500 (zona horaria sin dos puntos)
    from datetime import timezone
    now = datetime.now(timezone.utc)
    # Formato: yyyy-MM-dd'T'HH:mmZ (ejemplo: 2024-12-26T05:30-0500)
    seed = now.strftime('%Y-%m-%dT%H:%M%z')
    # Asegurar formato correcto: +0000 en lugar de +00:00
    if ':' in seed[-5:]:
        # Si tiene formato +00:00, convertirlo a +0000 (sin los dos puntos)
        seed = seed[:-3] + seed[-2:]
    
    # Nonce: valor aleatorio hexadecimal (según ejemplo Java: BigInteger.toString(16))
    # Luego se codifica en base64 para enviarlo
    import random
    nonce_hex = ''.join(random.choices('0123456789abcdef', k=32))  # 32 caracteres hex = 16 bytes
    
    # Generar firma usando nonce sin codificar (según ejemplo Java)
    signature = generate_placetopay_signature(login, trankey, seed, nonce_hex)
    
    # Codificar nonce en base64 para enviarlo
    nonce_base64 = base64.b64encode(bytes.fromhex(nonce_hex)).decode('utf-8')
    
    return {
        'login': login,
        'tranKey': signature,
        'seed': seed,
        'nonce': nonce_base64
    }


def create_placetopay_payment_request(
    auth: Dict[str, str],
    amount: float,
    currency: str,
    reference: str,
    description: str,
    return_url: str,
    cancel_url: str,
    buyer_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Crea request para PlaceToPay/GetNet según estructura estándar
    
    Estructura PlaceToPay:
    {
        "auth": {...},
        "payment": {
            "reference": "...",
            "description": "...",
            "amount": {
                "currency": "CLP",
                "total": 10000
            }
        },
        "expiration": "ISO8601",
        "returnUrl": "...",
        "cancelUrl": "...",
        "buyer": {...},
        "ipAddress": "...",
        "userAgent": "..."
    }
    """
    return {
        'auth': auth,
        'payment': {
            'reference': reference,
            'description': description,
            'amount': {
                'currency': currency,
                'total': int(amount)  # CLP no usa decimales
            }
        },
        'expiration': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        'returnUrl': return_url,
        'cancelUrl': cancel_url,
        'buyer': buyer_data,
        'ipAddress': buyer_data.get('ipAddress', '127.0.0.1'),
        'userAgent': buyer_data.get('userAgent', 'Mozilla/5.0')
    }


def get_placetopay_endpoint(base_url: str, endpoint_type: str = 'api') -> str:
    """
    Obtiene el endpoint correcto para PlaceToPay/GetNet
    
    Según ejemplo oficial Java (RestCarrier.java):
    - /api/session (para crear pagos - request)
    - /api/session/{requestId} (para consultar - query)
    - /api/collect (para collect)
    - /api/reverse (para reversar)
    """
    if endpoint_type == 'session' or endpoint_type == 'request':
        # Endpoint correcto según ejemplo oficial: api/session
        return f"{base_url}/api/session"
    elif endpoint_type == 'query':
        return f"{base_url}/api/query"
    elif endpoint_type == 'collect':
        return f"{base_url}/api/collect"
    elif endpoint_type == 'reverse':
        return f"{base_url}/api/reverse"
    else:
        # Endpoint por defecto según ejemplo oficial
        return f"{base_url}/api/session"


def create_getnet_payment_placetopay(
    amount: float,
    currency: str,
    order_id: str,
    customer_data: Dict[str, Any],
    return_url: str,
    cancel_url: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Crea un pago usando estructura PlaceToPay (estándar de GetNet)
    """
    from app.helpers.getnet_web_helper import get_getnet_config
    
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
        logger.info(f"🔧 MODO DEMO (PlaceToPay): Simulando pago GetNet para order_id={order_id}")
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
                'message': 'Modo demo activado (PlaceToPay)'
            }
        }
    
    if not config.get('login') or not config.get('trankey'):
        logger.error("GetNet credentials no configuradas")
        return None
    
    try:
        # Generar autenticación
        auth = generate_placetopay_auth(config['login'], config['trankey'])
        
        # Preparar datos del comprador
        # PlaceToPay requiere que algunos campos no estén vacíos
        document_number = customer_data.get('document_number', '').strip()
        if not document_number:
            # Si no hay RUT, usar un valor por defecto para pruebas
            document_number = '12345678-9'
            logger.warning("No se proporcionó RUT, usando valor por defecto para pruebas")
        
        buyer_data = {
            'document': document_number,
            'documentType': 'CC',  # CC=Cédula, NIT=NIT, CE=Cédula Extranjería
            'name': customer_data.get('first_name', 'Cliente') or 'Cliente',
            'surname': customer_data.get('last_name', '') or '',
            'email': customer_data.get('email', 'cliente@ejemplo.com') or 'cliente@ejemplo.com',
            'mobile': customer_data.get('phone_number', '') or '',
            'address': {
                'street': customer_data.get('address', 'Calle Principal') or 'Calle Principal',
                'city': customer_data.get('city', 'Santiago') or 'Santiago',
                'country': 'CL'  # Chile - código ISO 3166-1 alpha-2
            }
        }
        
        # Agregar ipAddress y userAgent al buyer_data si están disponibles
        try:
            from flask import request as flask_request
            if flask_request:
                buyer_data['ipAddress'] = flask_request.remote_addr or '127.0.0.1'
                buyer_data['userAgent'] = flask_request.headers.get('User-Agent', 'Mozilla/5.0')
        except:
            # Si no hay request disponible, usar valores por defecto
            buyer_data['ipAddress'] = buyer_data.get('ipAddress', '127.0.0.1')
            buyer_data['userAgent'] = buyer_data.get('userAgent', 'Mozilla/5.0')
        
        # Crear request
        payment_request = create_placetopay_payment_request(
            auth=auth,
            amount=amount,
            currency=currency,
            reference=order_id,
            description=f'Pago de entradas - {order_id}',
            return_url=return_url,
            cancel_url=cancel_url,
            buyer_data=buyer_data
        )
        
        # Agregar metadata si existe
        if metadata:
            payment_request['metadata'] = metadata
        
        # Intentar múltiples endpoints posibles (priorizando api/session según ejemplo oficial)
        possible_endpoints = [
            f"{config['api_base_url']}/api/session",  # Endpoint oficial según ejemplo Java
            f"{config['api_base_url']}/api/collect",
            f"{config['api_base_url']}/checkout/api/session",
            f"{config['api_base_url']}/checkout/api/collect",
            f"{config['api_base_url']}/api/v1/payment",
            f"{config['api_base_url']}/api/payment",
        ]
        
        # Headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        logger.info(f"Creando pago PlaceToPay/GetNet")
        logger.info(f"Request keys: {list(payment_request.keys())}")
        logger.debug(f"Request completo: {payment_request}")
        
        # Intentar cada endpoint hasta que uno funcione
        last_error = None
        for endpoint in possible_endpoints:
            logger.info(f"Intentando endpoint: {endpoint}")
            try:
                response = requests.post(
                    endpoint,
                    json=payment_request,
                    headers=headers,
                    timeout=30,
                    verify=True  # Verificar certificado SSL
                )
                logger.info(f"Respuesta PlaceToPay/GetNet: status={response.status_code} desde {endpoint}")
                
                if response.status_code in [200, 201]:
                    try:
                        payment_response = response.json()
                        logger.info(f"Response JSON keys: {list(payment_response.keys()) if isinstance(payment_response, dict) else 'No es dict'}")
                        
                        # PlaceToPay retorna processUrl y requestId
                        process_url = payment_response.get('processUrl') or payment_response.get('process_url')
                        request_id = payment_response.get('requestId') or payment_response.get('request_id')
                        
                        if process_url and request_id:
                            logger.info(f"✅ Pago creado en {endpoint}: requestId={request_id}, processUrl={process_url[:50]}...")
                            return {
                                'payment_id': request_id,
                                'checkout_url': process_url,
                                'payment_data': payment_response
                            }
                        else:
                            logger.warning(f"Endpoint {endpoint} retornó 200 pero sin processUrl/requestId")
                            logger.debug(f"Response: {payment_response}")
                            # Continuar con el siguiente endpoint
                            continue
                    except ValueError as e:
                        logger.warning(f"Endpoint {endpoint} retornó respuesta no-JSON: {response.text[:500]}")
                        # Continuar con el siguiente endpoint
                        continue
                elif response.status_code == 404:
                    logger.warning(f"Endpoint {endpoint} no encontrado (404), probando siguiente...")
                    continue
                elif response.status_code == 403:
                    logger.warning(f"Endpoint {endpoint} rechazado (403), probando siguiente...")
                    logger.debug(f"Response: {response.text[:500]}")
                    last_error = f"403 Forbidden desde {endpoint}"
                    continue
                else:
                    logger.warning(f"Endpoint {endpoint} retornó {response.status_code}, probando siguiente...")
                    last_error = f"Status {response.status_code} desde {endpoint}"
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en {endpoint}, probando siguiente...")
                last_error = f"Timeout en {endpoint}"
                continue
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Error de conexión en {endpoint}: {e}, probando siguiente...")
                last_error = f"Connection error en {endpoint}: {e}"
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error de request en {endpoint}: {e}, probando siguiente...")
                last_error = f"Request error en {endpoint}: {e}"
                continue
        
        # Si llegamos aquí, ningún endpoint funcionó
        logger.error(f"❌ Todos los endpoints fallaron. Último error: {last_error}")
        logger.error(f"Endpoints probados: {', '.join(possible_endpoints)}")
        return None
            
    except Exception as e:
        logger.error(f"Excepción al crear pago PlaceToPay/GetNet: {e}", exc_info=True)
        return None

