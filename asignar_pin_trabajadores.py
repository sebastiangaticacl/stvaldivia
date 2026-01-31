#!/usr/bin/env python3
"""
Script para asignar PIN 1234 a todos los trabajadores
"""
from app import create_app
from app.models import db
from app.models.pos_models import Employee

def main():
    app = create_app()
    with app.app_context():
        print("🔐 Asignando PIN 1234 a todos los trabajadores...")
        print("=" * 60)
        
        # Obtener todos los trabajadores activos
        trabajadores = Employee.query.filter_by(is_active=True).all()
        
        pin_asignado = 0
        pin_ya_existente = 0
        
        for trabajador in trabajadores:
            if trabajador.pin != '1234':
                trabajador.pin = '1234'
                pin_asignado += 1
                print(f"✅ PIN asignado a: {trabajador.name} (ID: {trabajador.id})")
            else:
                pin_ya_existente += 1
                print(f"⏭️  PIN ya era 1234: {trabajador.name} (ID: {trabajador.id})")
        
        if pin_asignado > 0:
            db.session.commit()
            print("\n" + "=" * 60)
            print(f"✅ Proceso completado:")
            print(f"   - PINs asignados: {pin_asignado}")
            print(f"   - PINs que ya eran 1234: {pin_ya_existente}")
            print(f"   - Total de trabajadores: {len(trabajadores)}")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print(f"ℹ️  Todos los trabajadores ya tenían PIN 1234")
            print(f"   - Total de trabajadores: {len(trabajadores)}")
            print("=" * 60)

if __name__ == '__main__':
    main()











