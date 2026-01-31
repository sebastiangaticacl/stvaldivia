#!/usr/bin/env python3
"""
Script para verificar que las rutas de gestión de variables de entorno están registradas
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    
    print("🔍 Creando aplicación Flask...")
    app = create_app()
    
    print("\n📋 Verificando rutas de gestión de variables de entorno:")
    print("=" * 60)
    
    # Buscar rutas relacionadas con bot/env-vars
    env_vars_routes = []
    for rule in app.url_map.iter_rules():
        if 'env-var' in rule.rule.lower() or 'bot/env' in rule.rule.lower():
            env_vars_routes.append({
                'rule': rule.rule,
                'endpoint': rule.endpoint,
                'methods': list(rule.methods)
            })
    
    if env_vars_routes:
        print("✅ Rutas encontradas:")
        for route in sorted(env_vars_routes, key=lambda x: x['rule']):
            methods = ', '.join([m for m in route['methods'] if m != 'HEAD' and m != 'OPTIONS'])
            print(f"   {route['rule']:40} [{methods:20}] → {route['endpoint']}")
    else:
        print("❌ No se encontraron rutas de gestión de variables de entorno")
        print("\n   Buscando rutas relacionadas con 'bot':")
        bot_routes = []
        for rule in app.url_map.iter_rules():
            if 'bot' in rule.rule.lower():
                bot_routes.append(rule.rule)
        if bot_routes:
            for route in sorted(set(bot_routes))[:10]:
                print(f"      - {route}")
    
    # Verificar específicamente las rutas que creamos
    print("\n🔐 Verificación de rutas específicas:")
    print("-" * 60)
    
    routes_to_check = [
        '/admin/bot/env-vars',
        '/admin/bot/env-vars/update'
    ]
    
    for route_path in routes_to_check:
        found = False
        for rule in app.url_map.iter_rules():
            if rule.rule == route_path or rule.rule.endswith(route_path):
                found = True
                methods = ', '.join([m for m in rule.methods if m != 'HEAD' and m != 'OPTIONS'])
                print(f"   ✅ {route_path:35} [{methods:20}] → {rule.endpoint}")
                break
        
        if not found:
            print(f"   ❌ {route_path:35} NO encontrada")
    
    # Verificar que el blueprint esté registrado
    print("\n📦 Verificación de blueprints:")
    print("-" * 60)
    admin_blueprints = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('admin.'):
            admin_blueprints.append(rule.endpoint.split('.')[0])
    
    if 'admin' in set(admin_blueprints):
        print("   ✅ Blueprint 'admin' está registrado")
    else:
        print("   ❌ Blueprint 'admin' NO está registrado")
    
    # Probar acceso a la ruta (sin autenticación, debería redirigir)
    print("\n🧪 Probando acceso a /admin/bot/env-vars (sin autenticación):")
    print("-" * 60)
    with app.test_client() as client:
        response = client.get('/admin/bot/env-vars', follow_redirects=False)
        status = response.status_code
        if status == 302:
            location = response.headers.get('Location', '')
            print(f"   ✅ Redirige correctamente (302) → {location}")
        elif status == 200:
            print(f"   ⚠️  Responde 200 (debería requerir autenticación)")
        else:
            print(f"   ⚠️  Status inesperado: {status}")
    
    print("\n" + "=" * 60)
    print("✅ Verificación completada")
    print("=" * 60)
    print("\n💡 Para probar la interfaz:")
    print("   1. Inicia el servidor: python run_local.py")
    print("   2. Inicia sesión como superadmin (sebagatica)")
    print("   3. Ve a: http://127.0.0.1:5001/admin/bot/config")
    print("   4. Haz clic en '⚙️ Gestionar Variables de Entorno'")
    print("   5. O accede directamente: http://127.0.0.1:5001/admin/bot/env-vars")
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

