#!/usr/bin/env python3
"""
Migración: Agregar campos de snapshot de pago a planilla_trabajadores
Ejecutar una sola vez para agregar las nuevas columnas.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text

def migrate_planilla_snapshot():
    """Agrega campos de snapshot a planilla_trabajadores"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar qué columnas existen
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('planilla_trabajadores')]
            
            print("=" * 60)
            print("🔄 Migración: Agregar campos de snapshot a planilla_trabajadores")
            print("=" * 60)
            print()
            
            # Campos a agregar
            campos_nuevos = {
                'cargo_id': "INTEGER REFERENCES cargos(id)",
                'sueldo_snapshot': "NUMERIC(10, 2)",
                'bono_snapshot': "NUMERIC(10, 2) DEFAULT 0.0",
                'pago_total': "NUMERIC(10, 2)",
                'override': "BOOLEAN DEFAULT FALSE",
                'override_motivo': "TEXT",
                'override_por': "VARCHAR(200)",
                'override_en': "TIMESTAMP"
            }
            
            campos_agregados = 0
            
            for campo, tipo in campos_nuevos.items():
                if campo not in existing_columns:
                    try:
                        sql = f"ALTER TABLE planilla_trabajadores ADD COLUMN {campo} {tipo};"
                        db.session.execute(text(sql))
                        print(f"  ✅ Agregado: {campo}")
                        campos_agregados += 1
                    except Exception as e:
                        print(f"  ⚠️  Error agregando {campo}: {e}")
                else:
                    print(f"  ⏭️  Ya existe: {campo}")
            
            # Crear índices
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_planilla_override ON planilla_trabajadores(override);"))
                print("  ✅ Índice override creado")
            except:
                pass
            
            try:
                db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_planilla_cargo ON planilla_trabajadores(cargo_id);"))
                print("  ✅ Índice cargo_id creado")
            except:
                pass
            
            db.session.commit()
            
            print()
            print("=" * 60)
            print(f"✅ Migración completada: {campos_agregados} campos agregados")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_planilla_snapshot()
    sys.exit(0 if success else 1)











