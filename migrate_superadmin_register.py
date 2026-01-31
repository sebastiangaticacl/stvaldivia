#!/usr/bin/env python3
"""
Migración: Crear tabla pos_registers y agregar campos a pos_sales
Ejecutar una sola vez.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from app.models.pos_models import PosRegister
from sqlalchemy import text, inspect

def migrate_superadmin_register():
    """Crea tabla pos_registers y agrega campos a pos_sales"""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print("=" * 60)
            print("🔄 Migración: Caja SUPERADMIN")
            print("=" * 60)
            print()
            
            # 1. Crear tabla pos_registers si no existe
            if 'pos_registers' not in existing_tables:
                db.create_all()
                print("  ✅ Tabla pos_registers creada")
            else:
                print("  ⏭️  Tabla pos_registers ya existe")
            
            # 2. Agregar campos a pos_sales si no existen
            if 'pos_sales' in existing_tables:
                columns = [col['name'] for col in inspector.get_columns('pos_sales')]
                
                if 'is_courtesy' not in columns:
                    try:
                        db.session.execute(text("ALTER TABLE pos_sales ADD COLUMN is_courtesy BOOLEAN DEFAULT FALSE NOT NULL;"))
                        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_pos_sales_is_courtesy ON pos_sales(is_courtesy);"))
                        print("  ✅ Campo is_courtesy agregado a pos_sales")
                    except Exception as e:
                        print(f"  ⚠️  Error agregando is_courtesy: {e}")
                else:
                    print("  ⏭️  Campo is_courtesy ya existe")
                
                if 'is_test' not in columns:
                    try:
                        db.session.execute(text("ALTER TABLE pos_sales ADD COLUMN is_test BOOLEAN DEFAULT FALSE NOT NULL;"))
                        db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_pos_sales_is_test ON pos_sales(is_test);"))
                        print("  ✅ Campo is_test agregado a pos_sales")
                    except Exception as e:
                        print(f"  ⚠️  Error agregando is_test: {e}")
                else:
                    print("  ⏭️  Campo is_test ya existe")
            
            # 3. Crear tabla superadmin_sale_audit si no existe
            if 'superadmin_sale_audit' not in existing_tables:
                db.create_all()
                print("  ✅ Tabla superadmin_sale_audit creada")
            else:
                print("  ⏭️  Tabla superadmin_sale_audit ya existe")
            
            # 4. Crear caja SUPERADMIN si no existe
            superadmin_register = PosRegister.query.filter_by(code='SUPERADMIN').first()
            if not superadmin_register:
                superadmin_register = PosRegister(
                    name='SUPERADMIN',
                    code='SUPERADMIN',
                    is_active=True,
                    superadmin_only=True
                )
                db.session.add(superadmin_register)
                print("  ✅ Caja SUPERADMIN creada")
            else:
                # Asegurar que tenga los valores correctos
                superadmin_register.name = 'SUPERADMIN'
                superadmin_register.code = 'SUPERADMIN'
                superadmin_register.is_active = True
                superadmin_register.superadmin_only = True
                db.session.add(superadmin_register)
                print("  ✅ Caja SUPERADMIN actualizada")
            
            db.session.commit()
            
            print()
            print("=" * 60)
            print("✅ Migración completada")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_superadmin_register()
    sys.exit(0 if success else 1)











