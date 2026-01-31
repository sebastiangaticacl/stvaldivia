#!/usr/bin/env python3
"""
Script para desbloquear una caja específica
Uso: python desbloquear_caja.py <register_id>
"""
import sys
from app import create_app
from app.models import db
from app.models.pos_models import RegisterLock

def desbloquear_caja(register_id):
    """Desbloquear una caja eliminando su bloqueo"""
    app = create_app()
    
    with app.app_context():
        print(f"Buscando bloqueo de caja {register_id}...")
        
        lock = RegisterLock.query.get(register_id)
        
        if not lock:
            print(f"✅ La caja {register_id} no está bloqueada")
            return True
        
        employee_name = lock.employee_name
        employee_id = lock.employee_id
        
        print(f"⚠️  Caja {register_id} bloqueada por:")
        print(f"   - Empleado: {employee_name} (ID: {employee_id})")
        print(f"   - Bloqueado desde: {lock.locked_at}")
        
        respuesta = input(f"\n¿Deseas desbloquear la caja {register_id}? (s/n): ").strip().lower()
        
        if respuesta == 's':
            db.session.delete(lock)
            db.session.commit()
            print(f"✅ Caja {register_id} desbloqueada correctamente")
            return True
        else:
            print("Operación cancelada")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python desbloquear_caja.py <register_id>")
        print("Ejemplo: python desbloquear_caja.py 1")
        sys.exit(1)
    
    register_id = sys.argv[1]
    desbloquear_caja(register_id)














