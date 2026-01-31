#!/usr/bin/env python3
"""
Script simple para comparar base de datos local vs servidor
Se puede ejecutar localmente (conectándose al servidor) o en el servidor (comparando con local)
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.pos_models import PosRegister, PosSale
from app.models.product_models import Product

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def compare_registers_simple(local_app, server_db_url=None):
    """Compara cajas - versión simple"""
    print_section("📦 CAJAS (pos_registers)")
    
    with local_app.app_context():
        local_regs = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.id).all()
        print(f"\n✅ LOCAL: {len(local_regs)} cajas activas")
        for reg in local_regs:
            is_test = getattr(reg, 'is_test', False)
            test_marker = " 🧪 TEST" if is_test else ""
            print(f"   - ID: {reg.id} | Código: {getattr(reg, 'code', 'N/A')} | Nombre: {reg.name}{test_marker}")
    
    if server_db_url:
        try:
            from flask import Flask
            from app import db as db_module
            
            server_app = Flask(__name__)
            server_app.config['SQLALCHEMY_DATABASE_URI'] = server_db_url
            server_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db_module.init_app(server_app)
            
            with server_app.app_context():
                server_regs = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.id).all()
                print(f"\n✅ SERVIDOR: {len(server_regs)} cajas activas")
                for reg in server_regs:
                    is_test = getattr(reg, 'is_test', False)
                    test_marker = " 🧪 TEST" if is_test else ""
                    print(f"   - ID: {reg.id} | Código: {getattr(reg, 'code', 'N/A')} | Nombre: {reg.name}{test_marker}")
                
                # Comparar
                local_ids = {str(r.id) for r in local_regs}
                server_ids = {str(r.id) for r in server_regs}
                
                only_local = local_ids - server_ids
                only_server = server_ids - local_ids
                
                if only_local:
                    print(f"\n⚠️  Solo en LOCAL ({len(only_local)}):")
                    for reg_id in only_local:
                        reg = next((r for r in local_regs if str(r.id) == reg_id), None)
                        if reg:
                            print(f"   - {reg.name} (ID: {reg.id})")
                
                if only_server:
                    print(f"\n⚠️  Solo en SERVIDOR ({len(only_server)}):")
                    for reg_id in only_server:
                        reg = next((r for r in server_regs if str(r.id) == reg_id), None)
                        if reg:
                            print(f"   - {reg.name} (ID: {reg.id})")
                
                if not only_local and not only_server:
                    print("\n✅ Cajas idénticas en local y servidor")
        except Exception as e:
            print(f"\n❌ Error al conectar con servidor: {e}")

def compare_products_simple(local_app, server_db_url=None):
    """Compara productos - versión simple"""
    print_section("🛍️  PRODUCTOS")
    
    with local_app.app_context():
        local_prods = Product.query.filter_by(is_active=True).order_by(Product.name).all()
        print(f"\n✅ LOCAL: {len(local_prods)} productos activos")
        
        # Mostrar algunos productos clave
        test_prods = [p for p in local_prods if getattr(p, 'is_test', False)]
        if test_prods:
            print(f"   🧪 Productos de prueba: {len(test_prods)}")
            for p in test_prods[:5]:
                print(f"      - {p.name} (${p.price})")
    
    if server_db_url:
        try:
            from flask import Flask
            from app import db as db_module
            
            server_app = Flask(__name__)
            server_app.config['SQLALCHEMY_DATABASE_URI'] = server_db_url
            server_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db_module.init_app(server_app)
            
            with server_app.app_context():
                server_prods = Product.query.filter_by(is_active=True).order_by(Product.name).all()
                print(f"\n✅ SERVIDOR: {len(server_prods)} productos activos")
                
                test_prods = [p for p in server_prods if getattr(p, 'is_test', False)]
                if test_prods:
                    print(f"   🧪 Productos de prueba: {len(test_prods)}")
                    for p in test_prods[:5]:
                        print(f"      - {p.name} (${p.price})")
                
                # Comparar
                local_names = {p.name for p in local_prods}
                server_names = {p.name for p in server_prods}
                
                only_local = local_names - server_names
                only_server = server_names - local_names
                
                if only_local:
                    print(f"\n⚠️  Solo en LOCAL ({len(only_local)} productos):")
                    for name in list(only_local)[:10]:
                        print(f"   - {name}")
                    if len(only_local) > 10:
                        print(f"   ... y {len(only_local) - 10} más")
                
                if only_server:
                    print(f"\n⚠️  Solo en SERVIDOR ({len(only_server)} productos):")
                    for name in list(only_server)[:10]:
                        print(f"   - {name}")
                    if len(only_server) > 10:
                        print(f"   ... y {len(only_server) - 10} más")
        except Exception as e:
            print(f"\n❌ Error al conectar con servidor: {e}")

def compare_sales_simple(local_app, server_db_url=None, days=30):
    """Compara ventas - versión simple"""
    print_section(f"💰 VENTAS (ÚLTIMOS {days} DÍAS)")
    
    fecha_limite = datetime.utcnow() - timedelta(days=days)
    
    with local_app.app_context():
        local_sales = PosSale.query.filter(
            PosSale.created_at >= fecha_limite
        ).order_by(PosSale.created_at.desc()).all()
        
        local_test = [s for s in local_sales if getattr(s, 'is_test', False)]
        local_real = [s for s in local_sales if not getattr(s, 'is_test', False)]
        
        print(f"\n✅ LOCAL: {len(local_sales)} ventas totales")
        print(f"   - Reales: {len(local_real)}")
        print(f"   - Prueba: {len(local_test)}")
        
        # Por caja
        by_register = {}
        for sale in local_sales:
            reg_id = str(sale.register_id)
            if reg_id not in by_register:
                by_register[reg_id] = 0
            by_register[reg_id] += 1
        
        if by_register:
            print(f"\n   Por caja:")
            for reg_id, count in sorted(by_register.items()):
                print(f"      - Caja {reg_id}: {count} ventas")
    
    if server_db_url:
        try:
            from flask import Flask
            from app import db as db_module
            
            server_app = Flask(__name__)
            server_app.config['SQLALCHEMY_DATABASE_URI'] = server_db_url
            server_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            db_module.init_app(server_app)
            
            with server_app.app_context():
                server_sales = PosSale.query.filter(
                    PosSale.created_at >= fecha_limite
                ).order_by(PosSale.created_at.desc()).all()
                
                server_test = [s for s in server_sales if getattr(s, 'is_test', False)]
                server_real = [s for s in server_sales if not getattr(s, 'is_test', False)]
                
                print(f"\n✅ SERVIDOR: {len(server_sales)} ventas totales")
                print(f"   - Reales: {len(server_real)}")
                print(f"   - Prueba: {len(server_test)}")
                
                # Por caja
                by_register = {}
                for sale in server_sales:
                    reg_id = str(sale.register_id)
                    if reg_id not in by_register:
                        by_register[reg_id] = 0
                    by_register[reg_id] += 1
                
                if by_register:
                    print(f"\n   Por caja:")
                    for reg_id, count in sorted(by_register.items()):
                        print(f"      - Caja {reg_id}: {count} ventas")
                
                # Comparar
                diff = len(local_sales) - len(server_sales)
                if diff != 0:
                    print(f"\n⚠️  Diferencia: {abs(diff)} ventas {'más en local' if diff > 0 else 'más en servidor'}")
                else:
                    print(f"\n✅ Mismo número de ventas")
        except Exception as e:
            print(f"\n❌ Error al conectar con servidor: {e}")

def main():
    print("=" * 80)
    print("🔍 COMPARACIÓN: BASE DE DATOS LOCAL vs SERVIDOR")
    print("=" * 80)
    
    local_app = create_app()
    
    # Obtener URL del servidor desde variable de entorno o argumento
    server_db_url = os.environ.get('SERVER_DATABASE_URL')
    if len(sys.argv) > 1:
        server_db_url = sys.argv[1]
    
    if not server_db_url:
        print("\n⚠️  No se proporcionó URL de servidor")
        print("   Uso: python3 scripts/compare_db_simple.py [DATABASE_URL_SERVIDOR]")
        print("   O: export SERVER_DATABASE_URL='postgresql://...'")
        print("\n📋 Mostrando solo datos LOCALES:\n")
    
    compare_registers_simple(local_app, server_db_url)
    compare_products_simple(local_app, server_db_url)
    compare_sales_simple(local_app, server_db_url, days=30)
    
    print("\n" + "=" * 80)
    print("✅ COMPARACIÓN COMPLETADA")
    print("=" * 80)
    print()

if __name__ == '__main__':
    main()

