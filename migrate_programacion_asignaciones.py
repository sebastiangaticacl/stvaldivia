#!/usr/bin/env python3
"""
Migración: Crear tabla programacion_asignaciones
Ejecutar una sola vez para crear la tabla.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text

def migrate_programacion_asignaciones():
    """Crea la tabla programacion_asignaciones"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar si la tabla ya existe
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print("=" * 60)
            print("🔄 Migración: Crear tabla programacion_asignaciones")
            print("=" * 60)
            print()
            
            if 'programacion_asignaciones' in existing_tables:
                print("  ⏭️  La tabla ya existe")
                print("=" * 60)
                return True
            
            # Crear tabla usando SQLAlchemy (mejor que SQL directo)
            from app.models.programacion_models import ProgramacionAsignacion
            db.create_all()
            
            print("  ✅ Tabla programacion_asignaciones creada")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_programacion_asignaciones()
    sys.exit(0 if success else 1)











