#!/usr/bin/env python3
"""
Script de diagnóstico para verificar cajas y ventas en producción
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.pos_models import PosRegister, PosSale
from datetime import datetime, timedelta

def main():
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🔍 DIAGNÓSTICO: CAJAS Y VENTAS")
        print("=" * 60)
        print()
        
        # 1) Verificar cajas
        print("📦 CAJAS REGISTRADAS:")
        print("-" * 60)
        registers = PosRegister.query.filter_by(is_active=True).order_by(PosRegister.created_at.desc()).all()
        
        if not registers:
            print("   ❌ NO HAY CAJAS ACTIVAS")
        else:
            print(f"   ✅ Total de cajas activas: {len(registers)}")
            for reg in registers:
                is_test = getattr(reg, 'is_test', False)
                test_marker = " 🧪 TEST" if is_test else ""
                print(f"   - ID: {reg.id} | Código: {reg.code} | Nombre: {reg.name}{test_marker}")
                print(f"     Creada: {reg.created_at} | Superadmin: {reg.superadmin_only}")
        
        print()
        
        # 2) Verificar ventas (últimas 30 días)
        print("💰 VENTAS (ÚLTIMOS 30 DÍAS):")
        print("-" * 60)
        fecha_limite = datetime.utcnow() - timedelta(days=30)
        sales = PosSale.query.filter(
            PosSale.created_at >= fecha_limite
        ).order_by(PosSale.created_at.desc()).all()
        
        if not sales:
            print("   ❌ NO HAY VENTAS EN LOS ÚLTIMOS 30 DÍAS")
        else:
            print(f"   ✅ Total de ventas: {len(sales)}")
            
            # Agrupar por is_test
            test_sales = [s for s in sales if getattr(s, 'is_test', False)]
            real_sales = [s for s in sales if not getattr(s, 'is_test', False)]
            
            print(f"   - Ventas reales: {len(real_sales)}")
            print(f"   - Ventas de prueba: {len(test_sales)}")
            print()
            
            # Mostrar últimas 10 ventas
            print("   ÚLTIMAS 10 VENTAS:")
            for sale in sales[:10]:
                is_test = getattr(sale, 'is_test', False)
                is_cancelled = getattr(sale, 'is_cancelled', False)
                test_marker = " 🧪 TEST" if is_test else ""
                cancelled_marker = " ❌ CANCELADA" if is_cancelled else ""
                print(f"   - ID: {sale.id} | Caja: {sale.register_name} ({sale.register_id}) | "
                      f"Total: ${sale.total_amount} | Fecha: {sale.created_at}{test_marker}{cancelled_marker}")
                print(f"     Empleado: {sale.employee_name} | Tipo: {sale.payment_type}")
        
        print()
        
        # 3) Verificar ventas por caja
        print("📊 VENTAS POR CAJA (ÚLTIMOS 30 DÍAS):")
        print("-" * 60)
        if registers:
            for reg in registers:
                reg_sales = [s for s in sales if str(s.register_id) == str(reg.id)]
                test_count = len([s for s in reg_sales if getattr(s, 'is_test', False)])
                real_count = len(reg_sales) - test_count
                print(f"   - {reg.name} (ID: {reg.id}): {len(reg_sales)} ventas totales "
                      f"({real_count} reales, {test_count} prueba)")
        
        print()
        
        # 4) Verificar ventas de hoy
        print("📅 VENTAS DE HOY:")
        print("-" * 60)
        hoy = datetime.utcnow().date()
        sales_hoy = [s for s in sales if s.created_at.date() == hoy]
        
        if not sales_hoy:
            print("   ❌ NO HAY VENTAS HOY")
        else:
            print(f"   ✅ Total de ventas hoy: {len(sales_hoy)}")
            test_hoy = [s for s in sales_hoy if getattr(s, 'is_test', False)]
            real_hoy = [s for s in sales_hoy if not getattr(s, 'is_test', False)]
            print(f"   - Ventas reales: {len(real_hoy)}")
            print(f"   - Ventas de prueba: {len(test_hoy)}")
        
        print()
        print("=" * 60)
        print("✅ DIAGNÓSTICO COMPLETADO")
        print("=" * 60)
        print()
        print("NOTAS:")
        print("- Las ventas de prueba (is_test=True) se excluyen del resumen financiero")
        print("- Las ventas canceladas (is_cancelled=True) se excluyen de los totales")
        print("- El resumen general (/resumen) muestra TODAS las ventas")
        print("- El resumen de caja individual excluye pruebas y cortesías")
        print()

if __name__ == '__main__':
    main()

