#!/usr/bin/env python3
"""
Script para verificar y crear cajas si no existen
Uso: python scripts/verify_and_seed_cajas.py
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.pos_models import PosRegister
from app.helpers.seed_test_data import seed_test_register_and_product, seed_test_cashier_user

def main():
    print("=" * 60)
    print("🔍 VERIFICACIÓN Y SEED DE CAJAS")
    print("=" * 60)
    print("")
    
    app = create_app()
    
    with app.app_context():
        # Verificar cajas existentes
        print("📋 Verificando cajas existentes...")
        all_registers = PosRegister.query.filter_by(is_active=True).all()
        print(f"   Total de cajas activas: {len(all_registers)}")
        
        if all_registers:
            print("\n   Cajas encontradas:")
            for reg in all_registers:
                is_test = getattr(reg, 'is_test', False)
                test_marker = " 🧪 TEST" if is_test else ""
                print(f"   - ID: {reg.id}, Código: {getattr(reg, 'code', 'N/A')}, Nombre: {reg.name}{test_marker}")
        else:
            print("   ⚠️  No se encontraron cajas activas")
        
        # Verificar si existe caja TEST
        test_register = PosRegister.query.filter(
            (PosRegister.code == "TEST001") | (PosRegister.name == "CAJA TEST BIMBA")
        ).first()
        
        if test_register:
            print(f"\n✅ Caja TEST encontrada: {test_register.name} (ID: {test_register.id})")
        else:
            print("\n⚠️  Caja TEST no encontrada")
            print("   Ejecutando seed de datos de prueba...")
            
            try:
                success, message, register, product = seed_test_register_and_product(db)
                if success:
                    db.session.commit()
                    print(f"   ✅ {message}")
                    if register:
                        print(f"   ✅ Caja creada: {register.name} (ID: {register.id})")
                    if product:
                        print(f"   ✅ Producto creado: {product.name} (ID: {product.id})")
                else:
                    print(f"   ❌ Error: {message}")
                    return 1
            except Exception as e:
                print(f"   ❌ Error al ejecutar seed: {e}")
                db.session.rollback()
                return 1
        
        # Verificar y crear empleado test
        print("\n📋 Verificando empleado test...")
        from app.models.pos_models import Employee
        test_employee = Employee.query.get("TEST0000")
        
        if test_employee:
            print(f"   ✅ Empleado TEST encontrado: {test_employee.name} (PIN: {test_employee.pin})")
        else:
            print("   ⚠️  Empleado TEST no encontrado")
            print("   Creando empleado test...")
            
            try:
                success_emp, message_emp, employee = seed_test_cashier_user(db)
                if success_emp:
                    db.session.commit()
                    print(f"   ✅ {message_emp}")
                else:
                    print(f"   ⚠️  {message_emp}")
            except Exception as e:
                print(f"   ❌ Error al crear empleado test: {e}")
                db.session.rollback()
        
        # Verificar productos
        print("\n📋 Verificando productos...")
        from app.models.product_models import Product
        all_products = Product.query.filter_by(is_active=True).all()
        print(f"   Total de productos activos: {len(all_products)}")
        
        test_product = Product.query.filter(
            (Product.external_id == "TEST100") | (Product.name == "TEST PRODUCTO $100")
        ).first()
        
        if test_product:
            print(f"   ✅ Producto TEST encontrado: {test_product.name} (Precio: ${test_product.price})")
        else:
            print("   ⚠️  Producto TEST no encontrado")
            print("   Ejecutando seed de producto...")
            
            try:
                success, message, register, product = seed_test_register_and_product(db)
                if success and product:
                    db.session.commit()
                    print(f"   ✅ Producto creado: {product.name}")
                else:
                    print(f"   ❌ Error: {message}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                db.session.rollback()
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN")
        print("=" * 60)
        
        final_registers = PosRegister.query.filter_by(is_active=True).all()
        final_products = Product.query.filter_by(is_active=True).all()
        
        print(f"Cajas activas: {len(final_registers)}")
        print(f"Productos activos: {len(final_products)}")
        
        if len(final_registers) == 0:
            print("\n⚠️  ADVERTENCIA: No hay cajas activas en la base de datos")
            print("   Ejecuta desde admin: http://tu-servidor/admin/cajas/ -> 'Seed Test'")
            print("   O crea cajas manualmente desde la interfaz de administración")
            return 1
        
        print("\n✅ Verificación completada")
        return 0

if __name__ == '__main__':
    sys.exit(main())

