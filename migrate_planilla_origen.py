"""
Migración: Agregar campo origen a planilla_trabajadores
"""
from app import create_app
from app.models import db

def migrate():
    app = create_app()
    with app.app_context():
        try:
            # Verificar si la columna ya existe
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('planilla_trabajadores')]
            
            if 'origen' not in columns:
                print("📝 Agregando columna 'origen' a planilla_trabajadores...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE planilla_trabajadores ADD COLUMN origen VARCHAR(20) DEFAULT 'manual'"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_planilla_origen ON planilla_trabajadores(origen)"))
                    conn.commit()
                print("✅ Columna 'origen' agregada correctamente")
            else:
                print("ℹ️  La columna 'origen' ya existe")
            
            # Actualizar registros existentes a 'manual' si son NULL
            with db.engine.connect() as conn:
                conn.execute(text("UPDATE planilla_trabajadores SET origen = 'manual' WHERE origen IS NULL"))
                conn.commit()
            print("✅ Migración completada")
            
        except Exception as e:
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    migrate()

