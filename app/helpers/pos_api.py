import requests
from flask import current_app
from .cache import cached, invalidate_sale_cache

SALE_ID_PREFIX = "BMB "
SALE_ID_PREFIX_NO_SPACE = "BMB"

@cached('sale_items', ttl=600)  # 10 minutos para reducir carga en API
def _get_sale_items_internal(numeric_sale_id):
    """Función interna para obtener items de venta (con cache) - Modo local: devuelve vacío"""
    # MODO SOLO LOCAL: No conectar a API externa
    local_only = current_app.config.get('LOCAL_ONLY', True)
    if local_only:
        return [], "Modo solo local: No se conecta a API externa", None
    
    api_key = current_app.config.get('API_KEY')
    base_url = current_app.config.get('BASE_API_URL')

    if not api_key or not base_url:
        return [], "Error de configuración: API_KEY o BASE_API_URL no está configurada.", None

    url = f"{base_url}/sales/{numeric_sale_id}"
    headers = {
        "x-api-key": api_key,
        "accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        canonical = data.get("sale_id", f"{SALE_ID_PREFIX}{numeric_sale_id}")
        cart_items = data.get("cart_items", [])

        return cart_items, None, canonical

    except requests.exceptions.HTTPError as e:
        return [], f"Error HTTP al consultar venta: {e}", None
    except requests.exceptions.RequestException as e:
        return [], f"Error de red/API: {e}", None
    except ValueError as e:
        return [], f"Error al parsear JSON de la API: {e}", None
    except Exception as e:
        return [], f"Error inesperado al obtener datos de la API: {e}", None

def get_sale_items(numeric_sale_id):
    """Obtiene items de venta (con cache)"""
    return _get_sale_items_internal(numeric_sale_id)

@cached('entity_details', ttl=1800)  # 30 minutos para reducir carga en API
def _get_entity_details_internal(entity_type, entity_id):
    """Función interna para obtener detalles de entidad (con cache)"""
    api_key = current_app.config['API_KEY']
    base_url = current_app.config['BASE_API_URL']

    if not api_key or not entity_id or entity_id == "0":
        return None

    url = f"{base_url}/{entity_type}/{entity_id}"
    headers = {
        "x-api-key": api_key,
        "accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error al obtener detalles de {entity_type} {entity_id}: {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener detalles de {entity_type} {entity_id}: {e}")
        return None

def get_entity_details(entity_type, entity_id):
    """Obtiene detalles de entidad (con cache)"""
    return _get_entity_details_internal(entity_type, entity_id)

@cached('employees', ttl=1800)  # 30 minutos para reducir carga en API
def _get_employees_internal(only_bartenders=False, only_cashiers=False):
    """Obtiene la lista de empleados desde la API de PHP Point of Sale
    
    Args:
        only_bartenders: Si es True, filtra solo empleados con custom_fields.Cargo == "Bartender"
    """
    api_key = current_app.config['API_KEY']
    base_url = current_app.config['BASE_API_URL']

    if not api_key:
        return []

    url = f"{base_url}/employees"
    headers = {
        "x-api-key": api_key,
        "accept": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # La API puede devolver un objeto con una lista o directamente una lista
        if isinstance(data, dict):
            employees = data.get('employees', data.get('data', []))
        else:
            employees = data
        
        # Filtrar solo empleados activos y con información válida
        valid_employees = []
        for emp in employees:
            if isinstance(emp, dict):
                # Si se requiere solo bartenders o solo cajeros, verificar custom_fields
                if only_bartenders or only_cashiers:
                    custom_fields = emp.get('custom_fields', {})
                    if isinstance(custom_fields, dict):
                        cargo = custom_fields.get('Cargo', '')
                        if only_bartenders and cargo != 'Bartender':
                            continue
                        if only_cashiers and cargo != 'Cajero':
                            continue
                    else:
                        # Si custom_fields no es un dict, intentar acceder directamente
                        cargo = getattr(custom_fields, 'Cargo', None) if hasattr(custom_fields, 'Cargo') else None
                        if only_bartenders and cargo != 'Bartender':
                            continue
                        if only_cashiers and cargo != 'Cajero':
                            continue
                
                # Verificar que tenga nombre o esté activo
                if emp.get('first_name') or emp.get('last_name') or emp.get('name'):
                    valid_employees.append(emp)
        
        return valid_employees
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error al obtener empleados: {e}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener empleados: {e}")
        return []

def get_employees(only_bartenders=False, only_cashiers=False):
    "Obtiene lista de empleados desde base de datos local"
    from app.helpers.employee_db import get_employees_local
    return get_employees_local(only_bartenders=only_bartenders, only_cashiers=only_cashiers, sync_if_needed=False)
def get_employee_pin(employee):
    """Extrae el PIN de un empleado desde custom_fields.Pin"""
    if not employee or not isinstance(employee, dict):
        return None
    
    # Primero intentar desde custom_fields.Pin
    custom_fields = employee.get('custom_fields', {})
    if isinstance(custom_fields, dict):
        pin = custom_fields.get('Pin')
        if pin:
            return str(pin)
    
    # Fallback a campos antiguos por compatibilidad
    return employee.get('pin') or employee.get('pin_number') or employee.get('password')

def verify_employee_pin(employee_id, pin):
    """Verifica el PIN de un empleado"""
    api_key = current_app.config['API_KEY']
    base_url = current_app.config['BASE_API_URL']

    if not api_key or not employee_id or not pin:
        return False

    # Obtener detalles del empleado
    employee = get_entity_details("employees", employee_id)
    
    if not employee:
        return False

    # Verificar PIN desde custom_fields.Pin
    stored_pin = get_employee_pin(employee)
    
    if stored_pin:
        # Comparar PINs (pueden estar encriptados o como string)
        return str(stored_pin) == str(pin)
    
    return False

def authenticate_employee(username_or_pin, pin=None, employee_id=None):
    """
    Autentica un empleado por PIN usando base de datos local.
    Si se proporciona employee_id, verifica solo ese empleado con el PIN proporcionado.
    Si solo se proporciona username_or_pin, se busca el empleado y se usa su PIN almacenado.
    Si se proporciona pin también, se verifica ese PIN específico.
    """
    # Importar funciones de BD local
    from app.helpers.employee_db import get_employee_by_id, verify_employee_pin_local, get_employees_local
    
    # Si se proporciona employee_id, buscar directamente ese empleado en BD local
    if employee_id:
        employee = get_employee_by_id(str(employee_id), sync_if_needed=False)
        if employee:
            # Verificar PIN usando función local
            if pin and verify_employee_pin_local(str(employee_id), str(pin)):
                return {
                    'id': employee.get('id'),
                    'name': employee.get('name', 'Empleado'),
                    'first_name': employee.get('first_name', ''),
                    'last_name': employee.get('last_name', ''),
                    'pin': employee.get('pin')
                }
        return None

    # Si no hay employee_id, buscar en todos los empleados locales
    employees = get_employees_local(only_bartenders=False, only_cashiers=False, sync_if_needed=False)
    
    for employee in employees:
        emp_id = employee.get('id')
        emp_pin = employee.get('pin')
        emp_name = employee.get('name', '')
        
        # Buscar por PIN (username_or_pin es el PIN)
        if emp_pin and str(emp_pin) == str(username_or_pin):
            return {
                'id': emp_id,
                'name': emp_name,
                'first_name': employee.get('first_name', ''),
                'last_name': employee.get('last_name', ''),
                'pin': emp_pin
            }
        
        # También buscar por nombre completo o parcial
        if emp_name and username_or_pin.lower() in emp_name.lower():
            if pin and emp_pin and str(emp_pin) == str(pin):
                return {
                    'id': emp_id,
                    'name': emp_name,
                    'first_name': employee.get('first_name', ''),
                    'last_name': employee.get('last_name', ''),
                    'pin': emp_pin
                }
    
    return None

def _get_entradas_sales_internal(limit=1000):
    """Obtiene todas las ventas que contienen items con categoría 'Entradas'"""
    api_key = current_app.config['API_KEY']
    base_url = current_app.config['BASE_API_URL']

    if not api_key:
        return []

    url = f"{base_url}/sales"
    headers = {
        "x-api-key": api_key,
        "accept": "application/json"
    }

    try:
        # PHP POS API requiere start_date y end_date (obligatorios)
        from datetime import datetime, timedelta
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=30)  # Últimos 30 días por defecto
        start_date = start_date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = end_date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Limitar a máximo 100 según documentación
        limit = min(limit, 100)
        
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'limit': limit
        }
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # La API puede devolver un objeto con una lista o directamente una lista
        if isinstance(data, dict):
            sales = data.get('sales', data.get('data', []))
        else:
            sales = data

        # Filtrar solo ventas que tienen items con categoría "Entradas"
        entradas_sales = []
        for sale in sales:
            if not isinstance(sale, dict):
                continue
            
            cart_items = sale.get('cart_items', [])
            sale_id = sale.get('sale_id', '')
            
            # Buscar items con categoría "Entradas"
            for item in cart_items:
                if not isinstance(item, dict):
                    continue
                
                # Verificar categoría del item
                category = item.get('category', '')
                item_name = item.get('name', '')
                
                # También verificar si el nombre contiene "Entrada" o si la categoría coincide
                if category == 'Entradas' or 'Entrada' in item_name or category == 'Entradas':
                    # Extraer precio del item
                    price = float(item.get('unit_price', 0) or item.get('price', 0) or 0)
                    qty = int(item.get('quantity', 0) or item.get('qty', 0) or 0)
                    
                    # Obtener fecha de la venta
                    sale_date = sale.get('sale_time', sale.get('sale_date', sale.get('created_at', '')))
                    
                    # Obtener información del empleado (cajero) y caja
                    employee_id = sale.get('employee_id', sale.get('sold_by_employee_id', ''))
                    register_id = sale.get('register_id', sale.get('register', ''))
                    
                    # Obtener total de la venta
                    sale_total = float(sale.get('total', 0) or sale.get('total_amount', 0) or 0)
                    
                    entradas_sales.append({
                        'sale_id': sale_id,
                        'item_name': item_name,
                        'price': price,
                        'quantity': qty,
                        'sale_date': sale_date,
                        'total': price * qty,
                        'employee_id': employee_id,
                        'register_id': register_id,
                        'sale_total': sale_total
                    })
                    break  # Solo agregar una vez por venta
        
        return entradas_sales
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error al obtener ventas de entradas: {e}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener ventas de entradas: {e}")
        return []

def get_entradas_sales(limit=1000):
    """Obtiene todas las ventas con categoría 'Entradas' (con cache)"""
    return _get_entradas_sales_internal(limit)

@cached('all_sales', ttl=300)
def _get_all_sales_internal(limit=100, max_results=100, use_pagination=False, start_date=None, end_date=None):
    """Obtiene ventas para análisis de cajeros y cajas
    
    Args:
        limit: Número de resultados por página (máximo 100 según API)
        max_results: Número máximo de resultados a obtener (por defecto 100 para consultas rápidas)
        use_pagination: Si es True, hace múltiples llamadas con paginación (requiere más tiempo)
        start_date: Fecha de inicio (formato ISO: YYYY-MM-DDTHH:MM:SSZ) - REQUERIDO por API
        end_date: Fecha de fin (formato ISO: YYYY-MM-DDTHH:MM:SSZ) - REQUERIDO por API
    """
    from datetime import datetime, timedelta
    
    api_key = current_app.config['API_KEY']
    base_url = current_app.config['BASE_API_URL']

    if not api_key:
        return []

    # Limitar a máximo 100 por llamada según documentación de la API
    limit = min(limit, 100)
    
    # Si no se proporcionan fechas, usar rango de últimos 30 días (por defecto)
    if not start_date or not end_date:
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=30)
        start_date = start_date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = end_date_obj.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    url = f"{base_url}/sales"
    headers = {
        "x-api-key": api_key,
        "accept": "application/json"
    }

    all_sales = []
    
    try:
        # Primera llamada: offset=0, limit=100 (o menos)
        offset = 0
        max_offset = max_results if use_pagination else limit
        
        while offset < max_offset:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'offset': offset,
                'limit': min(limit, max_offset - offset)
            }
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                
                # Verificar que la respuesta es JSON antes de parsear
                content_type = resp.headers.get('content-type', '').lower()
                
                # Si el endpoint /sales devuelve 500, intentar método alternativo
                if resp.status_code == 500:
                    current_app.logger.warning("Endpoint /sales devuelve 500, intentando método alternativo")
                    try:
                        resp = requests.get(url, headers=headers, timeout=30)
                        if resp.status_code != 200:
                            current_app.logger.warning(f"Endpoint /sales no disponible (status {resp.status_code})")
                            break
                        content_type = resp.headers.get('content-type', '').lower()
                    except:
                        break
                
                # Verificar que la respuesta es JSON
                if 'application/json' not in content_type:
                    # La API devolvió HTML en lugar de JSON (probablemente error o página de login)
                    current_app.logger.error(f"API devolvió HTML en lugar de JSON. Status: {resp.status_code}, Content-Type: {content_type}")
                    current_app.logger.error(f"Respuesta (primeros 500 chars): {resp.text[:500]}")
                    break
                
                resp.raise_for_status()
                
                # Parsear JSON con manejo de errores
                try:
                    data = resp.json()
                except ValueError as json_error:
                    # Error al parsear JSON (probablemente recibió HTML)
                    current_app.logger.error(f"Error al parsear JSON de respuesta: {json_error}")
                    current_app.logger.error(f"Respuesta recibida (primeros 500 chars): {resp.text[:500]}")
                    break

                # La API puede devolver un objeto con una lista o directamente una lista
                if isinstance(data, dict):
                    sales = data.get('sales', data.get('data', []))
                else:
                    sales = data
                
                if not sales or len(sales) == 0:
                    # No hay más resultados
                    break
                
                # Procesar ventas
                for sale in sales:
                    if not isinstance(sale, dict):
                        continue
                    
                    sale_id = sale.get('sale_id', '')
                    employee_id = sale.get('employee_id', sale.get('sold_by_employee_id', ''))
                    register_id = sale.get('register_id', sale.get('register', ''))
                    sale_date = sale.get('sale_time', sale.get('sale_date', sale.get('created_at', '')))
                    sale_total = float(sale.get('total', 0) or sale.get('total_amount', 0) or 0)
                    
                    all_sales.append({
                        'sale_id': sale_id,
                        'employee_id': employee_id,
                        'register_id': register_id,
                        'sale_time': sale_date,
                        'sale_date': sale_date,
                        'total': sale_total,
                        'sale_total': sale_total
                    })
                
                # Si obtuvimos menos resultados que el límite, no hay más páginas
                if len(sales) < limit:
                    break
                
                offset += limit
                
                # Si use_pagination es True y necesitamos más resultados, esperar 60 segundos
                # (según documentación PHP POS: delay de ~60 segundos entre llamadas pesadas)
                if use_pagination and offset < max_offset:
                    import time
                    current_app.logger.info(f"Obtenidas {len(all_sales)} ventas. Esperando 60 segundos antes de la siguiente página (requerido por PHP POS API)...")
                    time.sleep(60)  # 60 segundos según documentación PHP POS
                elif not use_pagination:
                    # Para consultas normales, solo obtener la primera página (máximo 100 items)
                    break
                    
            except ValueError as e:
                # Error al parsear JSON (probablemente recibió HTML)
                current_app.logger.error(f"Error al parsear JSON de respuesta (offset {offset}): {e}")
                current_app.logger.error(f"Respuesta recibida (primeros 500 chars): {resp.text[:500] if 'resp' in locals() else 'N/A'}")
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 500:
                    current_app.logger.warning("El endpoint /sales no está disponible en esta API (error 500).")
                else:
                    current_app.logger.error(f"Error HTTP al obtener ventas (offset {offset}): {e}")
                    # Intentar ver qué devolvió la API
                    try:
                        if hasattr(e.response, 'text'):
                            current_app.logger.error(f"Respuesta de error (primeros 500 chars): {e.response.text[:500]}")
                    except:
                        pass
                break
            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"Error de red al obtener ventas (offset {offset}): {e}")
                break
            except Exception as e:
                current_app.logger.error(f"Error inesperado al obtener ventas (offset {offset}): {e}")
                break
        
        current_app.logger.info(f"Obtenidas {len(all_sales)} ventas desde la API")
        return all_sales
        
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener todas las ventas: {e}")
        return []

def get_all_sales(limit=100, max_results=100, use_pagination=False, start_date=None, end_date=None):
    """Obtiene ventas para análisis (con cache)
    
    Args:
        limit: Número de resultados por página (máximo 100)
        max_results: Número máximo de resultados a obtener (por defecto 100)
        use_pagination: Si es True, hace múltiples llamadas con paginación
        start_date: Fecha de inicio (formato ISO: YYYY-MM-DDTHH:MM:SSZ) - Si None, usa últimos 30 días
        end_date: Fecha de fin (formato ISO: YYYY-MM-DDTHH:MM:SSZ) - Si None, usa fecha actual
    """
    return _get_all_sales_internal(limit, max_results, use_pagination, start_date, end_date)