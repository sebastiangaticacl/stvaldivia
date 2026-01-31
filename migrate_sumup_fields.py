#!/usr/bin/env python3
"""
Migración: Agregar campos SumUp a tabla pagos
Ejecutar una sola vez para agregar los campos necesarios para SumUp
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text

def migrate_sumup_fields():
    """Agrega campos SumUp a la tabla pagos"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 60)
            print("🔄 Migración: Agregar campos SumUp a tabla pagos")
            print("=" * 60)
            print()
            
            # Verificar si la tabla existe
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'pagos' not in existing_tables:
                print("❌ La tabla 'pagos' no existe")
                print("=" * 60)
                return False
            
            print("✅ Tabla 'pagos' encontrada")
            
            # Obtener columnas actuales
            columns = [col['name'] for col in inspector.get_columns('pagos')]
            print(f"   Columnas actuales: {len(columns)}")
            
            # Campos a agregar
            campos_sumup = {
                'sumup_checkout_id': {
                    'type': 'VARCHAR(100)',
                    'nullable': True,
                    'comment': 'ID del checkout de SumUp'
                },
                'sumup_checkout_url': {
                    'type': 'TEXT',
                    'nullable': True,
                    'comment': 'URL del checkout de SumUp para generar QR'
                },
                'sumup_merchant_code': {
                    'type': 'VARCHAR(50)',
                    'nullable': True,
                    'comment': 'Código del comerciante SumUp'
                }
            }
            
            # Verificar qué campos faltan
            campos_faltantes = {k: v for k, v in campos_sumup.items() if k not in columns}
            
            if not campos_faltantes:
                print("✅ Todos los campos SumUp ya existen")
                
                # Verificar índice
                indexes = [idx['name'] for idx in inspector.get_indexes('pagos')]
                if 'idx_pagos_sumup_checkout_id' in indexes:
                    print("✅ Índice 'idx_pagos_sumup_checkout_id' ya existe")
                else:
                    print("⚠️  Índice 'idx_pagos_sumup_checkout_id' no existe, creando...")
                    try:
                        db.session.execute(text(
                            "CREATE INDEX idx_pagos_sumup_checkout_id ON pagos (sumup_checkout_id)"
                        ))
                        db.session.commit()
                        print("✅ Índice creado")
                    except Exception as e:
                        if 'Duplicate key name' not in str(e):
                            print(f"⚠️  Error al crear índice: {e}")
                        else:
                            print("✅ Índice ya existe")
                
                print("=" * 60)
                return True
            
            print(f"📝 Campos a agregar: {list(campos_faltantes.keys())}")
            print()
            
            # Detectar tipo de base de datos
            db_type = db.engine.dialect.name
            supports_comments = db_type == 'mysql'
            
            # Agregar cada campo faltante
            for campo, config in campos_faltantes.items():
                try:
                    sql = f"ALTER TABLE pagos ADD COLUMN {campo} {config['type']}"
                    if not config['nullable']:
                        sql += " NOT NULL"
                    else:
                        sql += " NULL"
                    
                    if config.get('comment') and supports_comments:
                        sql += f" COMMENT '{config['comment']}'"
                    
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✅ Campo '{campo}' agregado")
                    
                except Exception as e:
                    if 'Duplicate column name' in str(e):
                        print(f"⚠️  Campo '{campo}' ya existe (saltando)")
                    else:
                        print(f"❌ Error al agregar campo '{campo}': {e}")
                        db.session.rollback()
                        return False
            
            # Crear índice
            try:
                indexes = [idx['name'] for idx in inspector.get_indexes('pagos')]
                if 'idx_pagos_sumup_checkout_id' not in indexes:
                    db.session.execute(text(
                        "CREATE INDEX idx_pagos_sumup_checkout_id ON pagos (sumup_checkout_id)"
                    ))
                    db.session.commit()
                    print()
                    print("✅ Índice 'idx_pagos_sumup_checkout_id' creado")
            except Exception as e:
                if 'Duplicate key name' not in str(e):
                    print(f"⚠️  Error al crear índice: {e}")
                else:
                    print("✅ Índice ya existe")
            
            # Verificación final
            print()
            print("=" * 60)
            print("✅ VERIFICACIÓN FINAL")
            print("=" * 60)
            
            inspector = db.inspect(db.engine)
            columns_final = [col['name'] for col in inspector.get_columns('pagos')]
            
            for campo in campos_sumup.keys():
                if campo in columns_final:
                    print(f"✅ {campo}")
                else:
                    print(f"❌ {campo} - FALTA")
            
            indexes_final = [idx['name'] for idx in inspector.get_indexes('pagos')]
            if 'idx_pagos_sumup_checkout_id' in indexes_final:
                print("✅ idx_pagos_sumup_checkout_id (índice)")
            else:
                print("⚠️  idx_pagos_sumup_checkout_id - FALTA")
            
            print()
            print("=" * 60)
            print("✅ Migración completada exitosamente")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error en migración: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_sumup_fields()
    sys.exit(0 if success else 1)

