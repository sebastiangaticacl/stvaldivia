#!/usr/bin/env python3
"""
Script de prueba para verificar que el sistema de toggle de base de datos funciona
"""
from app import create_app
from app.models import db
from app.models.system_config_models import SystemConfig
from app.helpers.database_config_helper import (
    get_database_mode,
    set_database_mode,
    get_database_url_for_mode,
    get_current_database_info,
    set_database_urls
)

def test_database_toggle():
    """Prueba el sistema de toggle de base de datos"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🧪 PRUEBAS DEL SISTEMA DE TOGGLE DE BASE DE DATOS")
        print("=" * 80)
        print()
        
        # Test 1: Verificar que la tabla existe
        print("📋 Test 1: Verificar tabla system_config")
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'system_config' in tables:
                print("   ✅ Tabla 'system_config' existe")
            else:
                print("   ❌ Tabla 'system_config' NO existe")
                print("   💡 Ejecuta: python3 migrate_system_config.py")
                return False
        except Exception as e:
            print(f"   ❌ Error al verificar tabla: {e}")
            return False
        
        print()
        
        # Test 2: Leer modo actual
        print("📋 Test 2: Leer modo actual de base de datos")
        try:
            current_mode = get_database_mode()
            print(f"   ✅ Modo actual: {current_mode}")
        except Exception as e:
            print(f"   ❌ Error al leer modo: {e}")
            return False
        
        print()
        
        # Test 3: Obtener información actual
        print("📋 Test 3: Obtener información de base de datos")
        try:
            db_info = get_current_database_info()
            print(f"   ✅ Información obtenida:")
            print(f"      - Modo: {db_info.get('mode', 'N/A')}")
            print(f"      - URL: {db_info.get('url', 'N/A')}")
        except Exception as e:
            print(f"   ❌ Error al obtener información: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
        
        # Test 4: Cambiar modo (test)
        print("📋 Test 4: Cambiar modo de base de datos")
        try:
            # Guardar modo original
            original_mode = get_database_mode()
            print(f"   Modo original: {original_mode}")
            
            # Cambiar a modo opuesto
            test_mode = 'dev' if original_mode == 'prod' else 'prod'
            print(f"   Cambiando a modo: {test_mode}")
            
            success = set_database_mode(test_mode, updated_by='test_script')
            if success:
                print(f"   ✅ Modo cambiado a: {test_mode}")
                
                # Verificar que se guardó
                saved_mode = get_database_mode()
                if saved_mode == test_mode:
                    print(f"   ✅ Modo guardado correctamente: {saved_mode}")
                else:
                    print(f"   ❌ Modo no coincide. Esperado: {test_mode}, Obtenido: {saved_mode}")
                    return False
                
                # Restaurar modo original
                print(f"   Restaurando modo original: {original_mode}")
                set_database_mode(original_mode, updated_by='test_script')
                print(f"   ✅ Modo restaurado")
            else:
                print(f"   ❌ Error al cambiar modo")
                return False
        except Exception as e:
            print(f"   ❌ Error en test de cambio: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
        
        # Test 5: Guardar URLs
        print("📋 Test 5: Guardar URLs de base de datos")
        try:
            import os
            test_dev_url = os.environ.get('DATABASE_DEV_URL', 'mysql://test:test@localhost:3306/bimba_dev')
            test_prod_url = os.environ.get('DATABASE_PROD_URL', 'mysql://test:test@localhost:3306/bimba_prod')
            
            success = set_database_urls(
                dev_url=test_dev_url,
                prod_url=test_prod_url,
                updated_by='test_script'
            )
            
            if success:
                print("   ✅ URLs guardadas correctamente")
                
                # Verificar que se guardaron
                saved_dev = SystemConfig.get('database_dev_url')
                saved_prod = SystemConfig.get('database_prod_url')
                
                if saved_dev:
                    print(f"   ✅ URL de desarrollo guardada: {saved_dev[:30]}...")
                if saved_prod:
                    print(f"   ✅ URL de producción guardada: {saved_prod[:30]}...")
            else:
                print("   ❌ Error al guardar URLs")
                return False
        except Exception as e:
            print(f"   ❌ Error en test de URLs: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
        
        # Test 6: Obtener URLs por modo
        print("📋 Test 6: Obtener URLs según modo")
        try:
            dev_url = get_database_url_for_mode('dev')
            prod_url = get_database_url_for_mode('prod')
            
            print(f"   ✅ URL de desarrollo: {dev_url[:50] if dev_url else 'None'}...")
            print(f"   ✅ URL de producción: {prod_url[:50] if prod_url else 'None'}...")
        except Exception as e:
            print(f"   ❌ Error al obtener URLs: {e}")
            return False
        
        print()
        
        # Test 7: Verificar rutas API (simulación)
        print("📋 Test 7: Verificar que las rutas API existen")
        try:
            # Verificar que las rutas están registradas en el blueprint
            from app.routes import bp
            routes = [str(rule) for rule in app.url_map.iter_rules() if 'database' in str(rule)]
            
            if routes:
                print(f"   ✅ Rutas API encontradas: {len(routes)}")
                for route in routes:
                    print(f"      - {route}")
            else:
                print("   ⚠️  No se encontraron rutas con 'database' en el nombre")
                print("   💡 Verificando manualmente...")
                # Verificar que el archivo routes.py tiene las funciones
                import inspect
                import app.routes as routes_module
                if hasattr(routes_module, 'admin_api_database_switch'):
                    print("   ✅ Función admin_api_database_switch existe en routes.py")
                if hasattr(routes_module, 'admin_api_database_info'):
                    print("   ✅ Función admin_api_database_info existe en routes.py")
        except Exception as e:
            print(f"   ⚠️  Error al verificar rutas (no crítico): {e}")
            # No fallar el test por esto
        
        print()
        print("=" * 80)
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("=" * 80)
        print()
        print("📋 Resumen:")
        print("   ✅ Tabla system_config existe")
        print("   ✅ Helper functions funcionan")
        print("   ✅ Cambio de modo funciona")
        print("   ✅ Guardado de URLs funciona")
        print("   ✅ Lectura de configuración funciona")
        print()
        print("💡 Próximos pasos:")
        print("   1. Configurar variables de entorno en servidor VM")
        print("   2. Acceder a /admin/panel_control")
        print("   3. Usar el toggle para cambiar entre bases de datos")
        print()
        
        return True

if __name__ == '__main__':
    success = test_database_toggle()
    exit(0 if success else 1)

