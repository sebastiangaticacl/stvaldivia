#!/usr/bin/env python3
"""
Script para limpiar ventas de test de una caja específica
Uso: python limpiar_ventas_test_register.py <register_id>
"""
import sys
from app import create_app
from app.models import db
from app.models.pos_models import PosSale

def limpiar_ventas_test(register_id):
    """Limpiar ventas de test de una caja"""
    app = create_app()
    
    with app.app_context():
        print(f"Buscando ventas de test en caja {register_id}...")
        
        # Buscar ventas de test en esta caja
        ventas_test = PosSale.query.filter_by(
            register_id=str(register_id),
            is_test=True
        ).all()
        
        if not ventas_test:
            print(f"✅ No hay ventas de test en la caja {register_id}")
            return
        
        print(f"Encontradas {len(ventas_test)} ventas de test:")
        for v in ventas_test:
            print(f"  - ID: {v.id}, Empleado: {v.employee_name}, Total: ${v.total_amount}, Fecha: {v.created_at}")
        
        respuesta = input("\n¿Deseas cancelar estas ventas? (s/n): ").strip().lower()
        
        if respuesta == 's':
            for v in ventas_test:
                v.is_cancelled = True
                print(f"  ✓ Cancelada: {v.id}")
            
            db.session.commit()
            print(f"\n✅ {len(ventas_test)} ventas de test canceladas correctamente")
        else:
            print("Operación cancelada")
            return

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python limpiar_ventas_test_register.py <register_id>")
        print("Ejemplo: python limpiar_ventas_test_register.py 1")
        sys.exit(1)
    
    register_id = sys.argv[1]
    limpiar_ventas_test(register_id)














