#!/usr/bin/env python3
"""
Migración: Agregar campo allowed_categories a pos_registers
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text, inspect

def migrate_allowed_categories():
    """Agrega el campo allowed_categories a la tabla pos_registers"""
    app = create_app()
    
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pos_registers')]
            
            print("=" * 60)
            print("🔄 Migración: Campo allowed_categories en pos_registers")
            print("=" * 60)
            print()
            
            if 'allowed_categories' in columns:
                print("  ⏭️  Campo allowed_categories ya existe")
                return
            
            # Agregar columna
            db.session.execute(text("""
                ALTER TABLE pos_registers
                ADD COLUMN allowed_categories TEXT NULL
            """))
            db.session.commit()
            
            print("  ✅ Campo allowed_categories agregado exitosamente")
            print()
            print("=" * 60)
            print("✅ Migración completada")
            print("=" * 60)
            
        except Exception as e:
            db.session.rollback()
            print(f"  ❌ Error: {e}")
            raise

if __name__ == '__main__':
    migrate_allowed_categories()


