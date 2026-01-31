#!/usr/bin/env python3
"""
Script para comparar base de datos local vs servidor
Compara estructura, cajas, productos y ventas
"""
import sys
import os
from datetime import datetime, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.pos_models import PosRegister, PosSale, Product
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

def get_table_info(engine, table_name):
    """Obtiene información de columnas de una tabla"""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return None
    
    columns = {}
    for col in inspector.get_columns(table_name):
        columns[col['name']] = {
            'type': str(col['type']),
            'nullable': col['nullable'],
            'default': col.get('default')
        }
    return columns

def compare_tables(local_engine, server_engine, table_name):
    """Compara estructura de una tabla entre local y servidor"""
    local_info = get_table_info(local_engine, table_name)
    server_info = get_table_info(server_engine, table_name)
    
    if local_info is None and server_info is None:
        return None, None, None
    
    if local_info is None:
        return None, server_info, "Solo en servidor"
    if server_info is None:
        return local_info, None, "Solo en local"
    
    # Comparar columnas
    local_cols = set(local_info.keys())
    server_cols = set(server_info.keys())
    
    only_local = local_cols - server_cols
    only_server = server_cols - local_cols
    common = local_cols & server_cols
    
    differences = []
    for col in common:
        local_col = local_info[col]
        server_col = server_info[col]
        if local_col['type'] != server_col['type'] or local_col['nullable'] != server_col['nullable']:
            differences.append({
                'column': col,
                'local': local_col,
                'server': server_col
            })
    
    return {
        'local_only': list(only_local),
        'server_only': list(only_server),
        'differences': differences,
        'local_info': local_info,
        'server_info': server_info
    }, None, None

def compare_registers(local_app, server_app):
    """Compara cajas entre local y servidor"""
    with local_app.app_context():
        local_regs = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.id).all()
        local_dict = {str(r.id): r for r in local_regs}
    
    with server_app.app_context():
        server_regs = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.id).all()
        server_dict = {str(r.id): r for r in server_regs}
    
    local_ids = set(local_dict.keys())
    server_ids = set(server_dict.keys())
    
    only_local = local_ids - server_ids
    only_server = server_ids - local_ids
    common = local_ids & server_ids
    
    differences = []
    for reg_id in common:
        local_reg = local_dict[reg_id]
        server_reg = server_dict[reg_id]
        
        diff_fields = []
        if local_reg.name != server_reg.name:
            diff_fields.append(f"name: '{local_reg.name}' vs '{server_reg.name}'")
        if getattr(local_reg, 'code', None) != getattr(server_reg, 'code', None):
            diff_fields.append(f"code: '{getattr(local_reg, 'code', None)}' vs '{getattr(server_reg, 'code', None)}'")
        if getattr(local_reg, 'is_test', False) != getattr(server_reg, 'is_test', False):
            diff_fields.append(f"is_test: {getattr(local_reg, 'is_test', False)} vs {getattr(server_reg, 'is_test', False)}")
        if local_reg.is_active != server_reg.is_active:
            diff_fields.append(f"is_active: {local_reg.is_active} vs {server_reg.is_active}")
        
        if diff_fields:
            differences.append({
                'id': reg_id,
                'fields': diff_fields
            })
    
    return {
        'only_local': [local_dict[r].name for r in only_local],
        'only_server': [server_dict[r].name for r in only_server],
        'differences': differences,
        'local_count': len(local_regs),
        'server_count': len(server_regs)
    }

def compare_products(local_app, server_app):
    """Compara productos entre local y servidor"""
    with local_app.app_context():
        local_prods = Product.query.filter_by(is_active=True).order_by(Product.id).all()
        local_dict = {p.name: p for p in local_prods}
    
    with server_app.app_context():
        server_prods = Product.query.filter_by(is_active=True).order_by(Product.id).all()
        server_dict = {p.name: p for p in server_prods}
    
    local_names = set(local_dict.keys())
    server_names = set(server_dict.keys())
    
    only_local = local_names - server_names
    only_server = server_names - local_names
    common = local_names & local_names
    
    differences = []
    for name in common:
        local_prod = local_dict[name]
        server_prod = server_dict[name]
        
        diff_fields = []
        if local_prod.price != server_prod.price:
            diff_fields.append(f"price: {local_prod.price} vs {server_prod.price}")
        if getattr(local_prod, 'is_test', False) != getattr(server_prod, 'is_test', False):
            diff_fields.append(f"is_test: {getattr(local_prod, 'is_test', False)} vs {getattr(server_prod, 'is_test', False)}")
        
        if diff_fields:
            differences.append({
                'name': name,
                'fields': diff_fields
            })
    
    return {
        'only_local': list(only_local),
        'only_server': list(only_server),
        'differences': differences,
        'local_count': len(local_prods),
        'server_count': len(server_prods)
    }

def compare_sales(local_app, server_app, days=30):
    """Compara ventas entre local y servidor"""
    fecha_limite = datetime.utcnow() - timedelta(days=days)
    
    with local_app.app_context():
        local_sales = PosSale.query.filter(
            PosSale.created_at >= fecha_limite
        ).order_by(PosSale.created_at.desc()).all()
        local_count = len(local_sales)
        local_by_register = {}
        for sale in local_sales:
            reg_id = str(sale.register_id)
            if reg_id not in local_by_register:
                local_by_register[reg_id] = 0
            local_by_register[reg_id] += 1
    
    with server_app.app_context():
        server_sales = PosSale.query.filter(
            PosSale.created_at >= fecha_limite
        ).order_by(PosSale.created_at.desc()).all()
        server_count = len(server_sales)
        server_by_register = {}
        for sale in server_sales:
            reg_id = str(sale.register_id)
            if reg_id not in server_by_register:
                server_by_register[reg_id] = 0
            server_by_register[reg_id] += 1
    
    return {
        'local_count': local_count,
        'server_count': server_count,
        'local_by_register': local_by_register,
        'server_by_register': server_by_register
    }

def main():
    print("=" * 80)
    print("🔍 COMPARACIÓN: BASE DE DATOS LOCAL vs SERVIDOR")
    print("=" * 80)
    print()
    
    # Crear apps
    local_app = create_app()
    
    # Para servidor, necesitamos cargar configuración diferente
    # Asumimos que hay una variable de entorno o archivo .env.server
    print("📋 Cargando configuración...")
    
    # Intentar cargar configuración del servidor
    server_app = None
    server_db_url = os.environ.get('SERVER_DATABASE_URL')
    
    if not server_db_url:
        print("⚠️  SERVER_DATABASE_URL no está configurado")
        print("   Usando solo base de datos local para comparación")
        print()
        server_app = None
    else:
        # Crear app con URL de servidor
        from flask import Flask
        server_app = Flask(__name__)
        server_app.config['SQLALCHEMY_DATABASE_URI'] = server_db_url
        server_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(server_app)
        print("✅ Configuración de servidor cargada")
        print()
    
    # 1) Comparar estructura de tablas
    print("=" * 80)
    print("1️⃣  ESTRUCTURA DE TABLAS")
    print("=" * 80)
    print()
    
    tables_to_check = ['pos_registers', 'products', 'pos_sales', 'pos_sale_items']
    
    with local_app.app_context():
        local_engine = db.engine
        
        if server_app:
            with server_app.app_context():
                server_engine = db.engine
                
                for table in tables_to_check:
                    print(f"📊 Tabla: {table}")
                    result, only_local, only_server = compare_tables(local_engine, server_engine, table)
                    
                    if only_local:
                        print(f"   ⚠️  Solo en local: {only_local}")
                    elif only_server:
                        print(f"   ⚠️  Solo en servidor: {only_server}")
                    elif result:
                        if result['local_only']:
                            print(f"   ⚠️  Columnas solo en local: {result['local_only']}")
                        if result['server_only']:
                            print(f"   ⚠️  Columnas solo en servidor: {result['server_only']}")
                        if result['differences']:
                            print(f"   ⚠️  Diferencias en columnas:")
                            for diff in result['differences']:
                                print(f"      - {diff['column']}: tipo local={diff['local']['type']}, servidor={diff['server']['type']}")
                        if not result['local_only'] and not result['server_only'] and not result['differences']:
                            print(f"   ✅ Estructura idéntica")
                    else:
                        print(f"   ❌ Tabla no encontrada en ninguna BD")
                    print()
        else:
            print("⚠️  No se puede comparar estructura (falta configuración de servidor)")
            print()
    
    # 2) Comparar cajas
    print("=" * 80)
    print("2️⃣  CAJAS (pos_registers)")
    print("=" * 80)
    print()
    
    if server_app:
        regs_compare = compare_registers(local_app, server_app)
        print(f"📦 Local: {regs_compare['local_count']} cajas activas")
        print(f"📦 Servidor: {regs_compare['server_count']} cajas activas")
        print()
        
        if regs_compare['only_local']:
            print(f"⚠️  Cajas solo en local ({len(regs_compare['only_local'])}):")
            for name in regs_compare['only_local']:
                print(f"   - {name}")
            print()
        
        if regs_compare['only_server']:
            print(f"⚠️  Cajas solo en servidor ({len(regs_compare['only_server'])}):")
            for name in regs_compare['only_server']:
                print(f"   - {name}")
            print()
        
        if regs_compare['differences']:
            print(f"⚠️  Cajas con diferencias ({len(regs_compare['differences'])}):")
            for diff in regs_compare['differences']:
                print(f"   - ID {diff['id']}: {', '.join(diff['fields'])}")
            print()
        
        if not regs_compare['only_local'] and not regs_compare['only_server'] and not regs_compare['differences']:
            print("✅ Cajas idénticas")
            print()
    else:
        with local_app.app_context():
            local_regs = PosRegister.query.filter_by(is_active=True).all()
            print(f"📦 Local: {len(local_regs)} cajas activas")
            for reg in local_regs:
                is_test = getattr(reg, 'is_test', False)
                test_marker = " 🧪 TEST" if is_test else ""
                print(f"   - {reg.name} (ID: {reg.id}, Código: {getattr(reg, 'code', 'N/A')}){test_marker}")
            print()
    
    # 3) Comparar productos
    print("=" * 80)
    print("3️⃣  PRODUCTOS")
    print("=" * 80)
    print()
    
    if server_app:
        prods_compare = compare_products(local_app, server_app)
        print(f"📦 Local: {prods_compare['local_count']} productos activos")
        print(f"📦 Servidor: {prods_compare['server_count']} productos activos")
        print()
        
        if prods_compare['only_local']:
            print(f"⚠️  Productos solo en local ({len(prods_compare['only_local'])}):")
            for name in prods_compare['only_local'][:10]:  # Limitar a 10
                print(f"   - {name}")
            if len(prods_compare['only_local']) > 10:
                print(f"   ... y {len(prods_compare['only_local']) - 10} más")
            print()
        
        if prods_compare['only_server']:
            print(f"⚠️  Productos solo en servidor ({len(prods_compare['only_server'])}):")
            for name in prods_compare['only_server'][:10]:
                print(f"   - {name}")
            if len(prods_compare['only_server']) > 10:
                print(f"   ... y {len(prods_compare['only_server']) - 10} más")
            print()
        
        if prods_compare['differences']:
            print(f"⚠️  Productos con diferencias ({len(prods_compare['differences'])}):")
            for diff in prods_compare['differences'][:10]:
                print(f"   - {diff['name']}: {', '.join(diff['fields'])}")
            if len(prods_compare['differences']) > 10:
                print(f"   ... y {len(prods_compare['differences']) - 10} más")
            print()
    else:
        with local_app.app_context():
            local_prods = Product.query.filter_by(is_active=True).all()
            print(f"📦 Local: {len(local_prods)} productos activos")
            print()
    
    # 4) Comparar ventas
    print("=" * 80)
    print("4️⃣  VENTAS (ÚLTIMOS 30 DÍAS)")
    print("=" * 80)
    print()
    
    if server_app:
        sales_compare = compare_sales(local_app, server_app, days=30)
        print(f"💰 Local: {sales_compare['local_count']} ventas")
        print(f"💰 Servidor: {sales_compare['server_count']} ventas")
        print()
        
        print("📊 Ventas por caja (Local):")
        for reg_id, count in sales_compare['local_by_register'].items():
            print(f"   - Caja {reg_id}: {count} ventas")
        print()
        
        print("📊 Ventas por caja (Servidor):")
        for reg_id, count in sales_compare['server_by_register'].items():
            print(f"   - Caja {reg_id}: {count} ventas")
        print()
    else:
        with local_app.app_context():
            fecha_limite = datetime.utcnow() - timedelta(days=30)
            local_sales = PosSale.query.filter(
                PosSale.created_at >= fecha_limite
            ).count()
            print(f"💰 Local: {local_sales} ventas en últimos 30 días")
            print()
    
    print("=" * 80)
    print("✅ COMPARACIÓN COMPLETADA")
    print("=" * 80)
    print()
    print("NOTAS:")
    print("- Para comparar con servidor, configura SERVER_DATABASE_URL")
    print("- Ejemplo: export SERVER_DATABASE_URL='postgresql://user:pass@server:5432/dbname'")
    print()

if __name__ == '__main__':
    main()

