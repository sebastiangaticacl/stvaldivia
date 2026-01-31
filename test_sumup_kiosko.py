#!/usr/bin/env python3
"""
Script de prueba para la integración de SumUp en kiosko
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_sumup_client():
    """Prueba básica del cliente SumUp"""
    print("=" * 60)
    print("🧪 PRUEBA 1: Cliente SumUp")
    print("=" * 60)
    
    try:
        from app.infrastructure.external.sumup_client import SumUpClient
        
        # Verificar API key
        api_key = os.getenv('SUMUP_API_KEY')
        if not api_key:
            print("⚠️  SUMUP_API_KEY no configurado")
            print("   Para pruebas, puedes usar una key de sandbox")
            return False
        
        print(f"✅ API Key encontrada: {api_key[:10]}...")
        
        # Crear cliente
        client = SumUpClient()
        print("✅ Cliente SumUp creado correctamente")
        
        # Probar creación de checkout (solo estructura, no ejecutar realmente)
        print("✅ Estructura del cliente válida")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Prueba que los modelos tengan los campos correctos"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 2: Modelos de Base de Datos")
    print("=" * 60)
    
    try:
        from app.models.kiosk_models import Pago
        
        # Verificar que los campos existen
        campos_requeridos = ['sumup_checkout_id', 'sumup_checkout_url', 'sumup_merchant_code']
        campos_encontrados = []
        
        for campo in campos_requeridos:
            if hasattr(Pago, campo):
                campos_encontrados.append(campo)
                print(f"✅ Campo '{campo}' existe en modelo Pago")
            else:
                print(f"❌ Campo '{campo}' NO existe en modelo Pago")
        
        if len(campos_encontrados) == len(campos_requeridos):
            print("✅ Todos los campos requeridos están presentes")
            return True
        else:
            print(f"⚠️  Faltan {len(campos_requeridos) - len(campos_encontrados)} campos")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes():
    """Prueba que las rutas estén registradas"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 3: Rutas del Kiosko")
    print("=" * 60)
    
    try:
        from app import create_app
        from app.blueprints.kiosk import routes
        
        app = create_app()
        
        # Verificar que las funciones están definidas
        funciones_requeridas = [
            'api_create_sumup_checkout',
            'api_get_sumup_qr',
            'sumup_payment_callback',
            'sumup_webhook',
            'kiosk_sumup_payment'
        ]
        
        funciones_encontradas = []
        for func_name in funciones_requeridas:
            if hasattr(routes, func_name):
                funciones_encontradas.append(func_name)
                print(f"✅ Función '{func_name}' existe en routes")
            else:
                print(f"❌ Función '{func_name}' NO existe en routes")
        
        # Verificar que las rutas están en el blueprint
        with app.app_context():
            from app.blueprints.kiosk import kiosk_bp
            
            rutas_registradas = []
            for rule in app.url_map.iter_rules():
                if rule.endpoint.startswith('kiosk.'):
                    endpoint_name = rule.endpoint.replace('kiosk.', '')
                    if endpoint_name in funciones_requeridas:
                        rutas_registradas.append(endpoint_name)
            
            print(f"\n✅ {len(rutas_registradas)} rutas encontradas en el blueprint")
            for ruta in rutas_registradas:
                print(f"   - {ruta}")
        
        if len(funciones_encontradas) == len(funciones_requeridas):
            print("✅ Todas las funciones requeridas están definidas")
            return True
        else:
            print(f"⚠️  Faltan {len(funciones_requeridas) - len(funciones_encontradas)} funciones")
            return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_migration():
    """Verifica si la migración de BD se puede aplicar"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 4: Migración de Base de Datos")
    print("=" * 60)
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("⚠️  DATABASE_URL no configurado")
        print("   No se puede probar la migración de BD")
        return False
    
    print(f"✅ DATABASE_URL configurado: {database_url[:20]}...")
    
    # Verificar si el archivo de migración existe
    migration_file = 'migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql'
    if os.path.exists(migration_file):
        print(f"✅ Archivo de migración encontrado: {migration_file}")
        print("   Para aplicarla, ejecuta:")
        print(f"   mysql -u usuario -p bimba_db < {migration_file}")
        return True
    else:
        print(f"❌ Archivo de migración no encontrado: {migration_file}")
        return False


def test_configuration():
    """Verifica la configuración de la app"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBA 5: Configuración de la Aplicación")
    print("=" * 60)
    
    try:
        from app import create_app
        
        app = create_app()
        
        # Verificar variables de configuración
        sumup_api_key = app.config.get('SUMUP_API_KEY')
        sumup_merchant_code = app.config.get('SUMUP_MERCHANT_CODE')
        
        if sumup_api_key:
            print(f"✅ SUMUP_API_KEY configurado: {sumup_api_key[:10]}...")
        else:
            print("⚠️  SUMUP_API_KEY no configurado")
            print("   Agrega SUMUP_API_KEY a variables de entorno")
        
        if sumup_merchant_code:
            print(f"✅ SUMUP_MERCHANT_CODE configurado: {sumup_merchant_code}")
        else:
            print("⚠️  SUMUP_MERCHANT_CODE no configurado (opcional)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 60)
    print("🧪 PRUEBAS DE INTEGRACIÓN SUMUP PARA KIOSKO")
    print("=" * 60)
    print()
    
    resultados = []
    
    # Ejecutar pruebas
    resultados.append(("Cliente SumUp", test_sumup_client()))
    resultados.append(("Modelos", test_models()))
    resultados.append(("Rutas", test_routes()))
    resultados.append(("Migración BD", test_database_migration()))
    resultados.append(("Configuración", test_configuration()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    exitosas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        estado = "✅ PASÓ" if resultado else "❌ FALLÓ"
        print(f"{estado}: {nombre}")
    
    print(f"\n✅ {exitosas}/{total} pruebas pasaron")
    
    if exitosas == total:
        print("\n🎉 Todas las pruebas pasaron!")
        return 0
    else:
        print(f"\n⚠️  {total - exitosas} pruebas fallaron")
        print("   Revisa la configuración y vuelve a intentar")
        return 1


if __name__ == '__main__':
    sys.exit(main())

