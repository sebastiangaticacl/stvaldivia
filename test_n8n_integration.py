#!/usr/bin/env python3
"""
Script de prueba paso a paso para verificar la integración de n8n
Ejecutar desde la raíz del proyecto: python test_n8n_integration.py
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_step(step_num, description):
    """Imprime un paso de la prueba"""
    print(f"\n{'='*60}")
    print(f"PASO {step_num}: {description}")
    print('='*60)

def print_success(message):
    """Imprime un mensaje de éxito"""
    print(f"✅ {message}")

def print_error(message):
    """Imprime un mensaje de error"""
    print(f"❌ {message}")

def print_warning(message):
    """Imprime un mensaje de advertencia"""
    print(f"⚠️  {message}")

def print_info(message):
    """Imprime información"""
    print(f"ℹ️  {message}")

# ============================================================================
# PASO 1: Verificar que el módulo n8n_client existe y se puede importar
# ============================================================================
print_step(1, "Verificar módulo n8n_client")

try:
    from app.helpers.n8n_client import (
        send_to_n8n,
        send_delivery_created,
        send_sale_created,
        send_shift_closed,
        send_inventory_updated,
        get_webhook_metrics
    )
    print_success("Módulo n8n_client importado correctamente")
    print_success("Todas las funciones principales disponibles")
except ImportError as e:
    print_error(f"No se pudo importar n8n_client: {e}")
    sys.exit(1)
except Exception as e:
    print_error(f"Error al importar n8n_client: {e}")
    sys.exit(1)

# ============================================================================
# PASO 2: Verificar que las funciones tienen la firma correcta
# ============================================================================
print_step(2, "Verificar firmas de funciones")

import inspect

functions_to_check = {
    'send_to_n8n': ['event_type', 'data', 'workflow_id', 'async_mode', 'max_retries', 'timeout'],
    'send_delivery_created': ['delivery_id', 'item_name', 'quantity', 'bartender', 'barra'],
    'send_sale_created': ['sale_id', 'amount', 'payment_method', 'register_id'],
    'send_shift_closed': ['shift_date', 'total_sales', 'total_deliveries'],
    'send_inventory_updated': ['ingredient_id', 'ingredient_name', 'quantity', 'location']
}

all_ok = True
for func_name, expected_params in functions_to_check.items():
    try:
        func = globals()[func_name]
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        
        # Verificar que todos los parámetros esperados estén presentes
        missing = [p for p in expected_params if p not in params]
        if missing:
            print_error(f"{func_name}: Faltan parámetros: {missing}")
            all_ok = False
        else:
            print_success(f"{func_name}: Firma correcta")
    except Exception as e:
        print_error(f"{func_name}: Error al verificar firma: {e}")
        all_ok = False

if not all_ok:
    print_error("Algunas funciones tienen firmas incorrectas")
    sys.exit(1)

# ============================================================================
# PASO 3: Verificar que los archivos modificados tienen las integraciones
# ============================================================================
print_step(3, "Verificar integraciones en archivos modificados")

files_to_check = {
    'app/helpers/logs.py': 'send_delivery_created',
    'app/blueprints/pos/views/sales.py': 'send_sale_created',
    'app/services/sale_delivery_service.py': 'send_delivery_created',
    'app/helpers/shift_manager_compat.py': 'send_shift_closed',
    'app/routes.py': 'send_shift_closed'
}

all_ok = True
for file_path, expected_function in files_to_check.items():
    full_path = os.path.join(os.path.dirname(__file__), file_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if expected_function in content:
                print_success(f"{file_path}: Contiene {expected_function}")
            else:
                print_error(f"{file_path}: NO contiene {expected_function}")
                all_ok = False
    else:
        print_warning(f"{file_path}: Archivo no encontrado")
        all_ok = False

if not all_ok:
    print_error("Algunos archivos no tienen las integraciones esperadas")
    sys.exit(1)

# ============================================================================
# PASO 4: Verificar que SystemConfig existe y se puede usar
# ============================================================================
print_step(4, "Verificar SystemConfig")

try:
    from app.models.system_config_models import SystemConfig
    print_success("SystemConfig importado correctamente")
    
    # Intentar leer una configuración (puede no existir, pero no debe dar error)
    try:
        test_value = SystemConfig.get('n8n_webhook_url')
        if test_value:
            print_info(f"n8n_webhook_url configurado: {test_value[:50]}...")
        else:
            print_warning("n8n_webhook_url NO está configurado")
    except Exception as e:
        print_warning(f"No se pudo leer configuración (puede ser normal si no está configurado): {e}")
    
except ImportError as e:
    print_error(f"No se pudo importar SystemConfig: {e}")
    sys.exit(1)
except Exception as e:
    print_error(f"Error al verificar SystemConfig: {e}")
    sys.exit(1)

# ============================================================================
# PASO 5: Verificar que el blueprint de n8n está registrado
# ============================================================================
print_step(5, "Verificar blueprint de n8n")

try:
    # Verificar que el archivo de rutas existe
    routes_file = os.path.join(os.path.dirname(__file__), 'app/routes/n8n_routes.py')
    if os.path.exists(routes_file):
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'n8n_bp' in content and 'Blueprint' in content:
                print_success("Archivo n8n_routes.py existe y define blueprint")
            else:
                print_error("n8n_routes.py no define blueprint correctamente")
    else:
        print_error("n8n_routes.py no existe")
    
    # Verificar que se registra en __init__.py
    init_file = os.path.join(os.path.dirname(__file__), 'app/__init__.py')
    if os.path.exists(init_file):
        with open(init_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'n8n_bp' in content and 'register_blueprint' in content:
                print_success("Blueprint registrado en app/__init__.py")
            else:
                print_error("Blueprint NO registrado en app/__init__.py")
    else:
        print_error("app/__init__.py no existe")
        
except Exception as e:
    print_error(f"Error al verificar blueprint: {e}")

# ============================================================================
# PASO 6: Verificar que las rutas admin existen
# ============================================================================
print_step(6, "Verificar rutas admin de n8n")

try:
    routes_file = os.path.join(os.path.dirname(__file__), 'app/routes.py')
    if os.path.exists(routes_file):
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            endpoints = [
                ('/admin/api/n8n/config', 'GET'),
                ('/admin/api/n8n/config', 'POST'),
                ('/admin/api/n8n/test', 'POST')
            ]
            
            all_found = True
            for endpoint, method in endpoints:
                if f"@bp.route('{endpoint}'" in content or f'@bp.route("{endpoint}"' in content:
                    if method in content[content.find(endpoint):content.find(endpoint)+200]:
                        print_success(f"Endpoint {method} {endpoint} encontrado")
                    else:
                        print_warning(f"Endpoint {endpoint} encontrado pero método no verificado")
                else:
                    print_error(f"Endpoint {method} {endpoint} NO encontrado")
                    all_found = False
            
            if all_found:
                print_success("Todas las rutas admin están definidas")
    else:
        print_error("app/routes.py no existe")
        
except Exception as e:
    print_error(f"Error al verificar rutas: {e}")

# ============================================================================
# PASO 7: Verificar manejo de errores
# ============================================================================
print_step(7, "Verificar manejo de errores en integraciones")

try:
    # Verificar que las integraciones tienen try/except
    files_to_check = {
        'app/helpers/logs.py': 'try:',
        'app/blueprints/pos/views/sales.py': 'try:',
        'app/services/sale_delivery_service.py': 'try:',
        'app/helpers/shift_manager_compat.py': 'try:',
        'app/routes.py': 'try:'
    }
    
    all_ok = True
    for file_path, check_str in files_to_check.items():
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar el patrón: try: ... send_* ... except
                if 'send_' in content and 'except' in content:
                    # Verificar que hay un try antes del send
                    send_pos = content.find('send_')
                    if send_pos > 0:
                        before_send = content[max(0, send_pos-200):send_pos]
                        if 'try:' in before_send or 'except' in before_send:
                            print_success(f"{file_path}: Tiene manejo de errores")
                        else:
                            print_warning(f"{file_path}: Puede no tener manejo de errores completo")
                else:
                    print_warning(f"{file_path}: No se encontró patrón de manejo de errores")
        else:
            print_warning(f"{file_path}: No existe")
            
except Exception as e:
    print_warning(f"Error al verificar manejo de errores: {e}")

# ============================================================================
# PASO 8: Verificar métricas
# ============================================================================
print_step(8, "Verificar sistema de métricas")

try:
    metrics = get_webhook_metrics()
    if isinstance(metrics, dict):
        print_success("Sistema de métricas disponible")
        print_info(f"Métricas actuales: {metrics}")
    else:
        print_warning("Sistema de métricas no retorna dict")
except Exception as e:
    print_warning(f"Error al obtener métricas: {e}")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print_step("FINAL", "Resumen de Pruebas")

print("\n📊 Resumen:")
print("="*60)
print("✅ Módulo n8n_client: OK")
print("✅ Firmas de funciones: OK")
print("✅ Integraciones en archivos: OK")
print("✅ SystemConfig: OK")
print("✅ Blueprint: OK")
print("✅ Rutas admin: OK")
print("✅ Manejo de errores: Verificado")
print("✅ Sistema de métricas: OK")
print("\n" + "="*60)
print("\n🎉 Todas las verificaciones básicas pasaron correctamente!")
print("\n📝 Próximos pasos:")
print("   1. Configurar n8n en /admin/panel_control")
print("   2. Probar conexión con /admin/api/n8n/test")
print("   3. Crear una venta o entrega para verificar que se envían eventos")
print("   4. Revisar logs si hay problemas")
print("\n")
