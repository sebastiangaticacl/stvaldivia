#!/usr/bin/env python3
"""
Script para verificar que las rutas de caja están registradas correctamente
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    
    print("🔍 Creando aplicación Flask...")
    app = create_app()
    
    print("\n📋 Rutas registradas relacionadas con 'caja':")
    caja_routes = []
    for rule in app.url_map.iter_rules():
        if 'caja' in rule.rule.lower():
            caja_routes.append({
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': list(rule.methods)
            })
    
    if caja_routes:
        for route in sorted(caja_routes, key=lambda x: x['rule']):
            methods = ', '.join([m for m in route['methods'] if m != 'HEAD' and m != 'OPTIONS'])
            print(f"  ✅ {route['rule']:30} [{methods:15}] → {route['endpoint']}")
    else:
        print("  ❌ No se encontraron rutas de caja")
    
    # Verificar específicamente /caja/login
    login_route = None
    for rule in app.url_map.iter_rules():
        if rule.rule == '/caja/login' or rule.rule.endswith('/caja/login'):
            login_route = rule
            break
    
    print("\n🔐 Verificación de /caja/login:")
    if login_route:
        print(f"  ✅ Ruta encontrada: {login_route.rule}")
        print(f"     Endpoint: {login_route.endpoint}")
        print(f"     Métodos: {list(login_route.methods)}")
    else:
        print("  ❌ Ruta /caja/login NO encontrada")
        print("\n  Rutas disponibles que contienen 'login':")
        for rule in app.url_map.iter_rules():
            if 'login' in rule.rule.lower():
                print(f"    - {rule.rule} → {rule.endpoint}")
    
    # Probar con test client
    print("\n🧪 Probando con test client...")
    with app.test_client() as client:
        response = client.get('/caja/login')
        print(f"  GET /caja/login → Status: {response.status_code}")
        if response.status_code == 200:
            print("  ✅ La ruta funciona correctamente")
        elif response.status_code == 302:
            print(f"  ℹ️  Redirección a: {response.location}")
        else:
            print(f"  ❌ Error: {response.status_code}")
            if response.data:
                print(f"     Respuesta: {response.data[:200]}")
    
except Exception as e:
    print(f"❌ Error al verificar rutas: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)










