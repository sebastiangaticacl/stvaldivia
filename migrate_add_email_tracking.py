#!/usr/bin/env python3
"""
Migración: Agregar campos de seguimiento de email a la tabla entradas
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging antes de importar app
import logging
logging.basicConfig(level=logging.ERROR)

# Configurar variables de entorno para evitar problemas
os.environ['FLASK_ENV'] = 'production'
os.environ['LOG_FILE'] = '/dev/null'

from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Configurar logging para evitar problemas de permisos
        import logging
        logging.basicConfig(level=logging.ERROR)
        
        # Verificar si las columnas ya existen usando SQL directo
        try:
            result = db.session.execute(text("SHOW COLUMNS FROM entradas LIKE 'email_resumen_enviado'"))
            col_exists = result.fetchone() is not None
        except:
            col_exists = False
        
        if not col_exists:
            print("Agregando columna email_resumen_enviado...")
            try:
                db.session.execute(text("""
                    ALTER TABLE entradas 
                    ADD COLUMN email_resumen_enviado BOOLEAN DEFAULT 0 NOT NULL
                """))
                db.session.commit()
                print("✅ Columna email_resumen_enviado agregada")
            except Exception as e:
                print(f"⚠️ Error al agregar columna email_resumen_enviado: {e}")
                db.session.rollback()
        else:
            print("✅ Columna email_resumen_enviado ya existe")
        
        # Verificar segunda columna
        try:
            result = db.session.execute(text("SHOW COLUMNS FROM entradas LIKE 'email_resumen_enviado_at'"))
            col_exists = result.fetchone() is not None
        except:
            col_exists = False
        
        if not col_exists:
            print("Agregando columna email_resumen_enviado_at...")
            try:
                db.session.execute(text("""
                    ALTER TABLE entradas 
                    ADD COLUMN email_resumen_enviado_at DATETIME
                """))
                db.session.commit()
                print("✅ Columna email_resumen_enviado_at agregada")
            except Exception as e:
                print(f"⚠️ Error al agregar columna email_resumen_enviado_at: {e}")
                db.session.rollback()
        else:
            print("✅ Columna email_resumen_enviado_at ya existe")
        
        # Crear índice para búsquedas rápidas
        try:
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_entradas_email_enviado 
                ON entradas(email_resumen_enviado)
            """))
            db.session.commit()
            print("✅ Índice creado")
        except Exception as idx_error:
            print(f"⚠️ Índice ya existe o error: {idx_error}")
        
        print("\n✅ Migración completada exitosamente")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error en migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

