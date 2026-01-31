#!/usr/bin/env python3
"""
Script de migración para crear la tabla system_config
"""
from app import create_app
from app.models import db
from app.models.system_config_models import SystemConfig

def migrate_system_config():
    """Crea la tabla system_config si no existe"""
    app = create_app()
    
    with app.app_context():
        try:
            # Crear todas las tablas (solo creará las que no existen)
            db.create_all()
            
            # Verificar que la tabla existe
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'system_config' in tables:
                print("✅ Tabla 'system_config' existe")
                
                # Verificar si hay configuraciones
                count = SystemConfig.query.count()
                print(f"   Configuraciones existentes: {count}")
                
                # Inicializar URLs si están en variables de entorno
                import os
                dev_url = os.environ.get('DATABASE_DEV_URL')
                prod_url = os.environ.get('DATABASE_PROD_URL')
                
                if dev_url:
                    SystemConfig.set('database_dev_url', dev_url, 'URL de base de datos de desarrollo', 'migration')
                    print(f"✅ URL de desarrollo guardada")
                
                if prod_url:
                    SystemConfig.set('database_prod_url', prod_url, 'URL de base de datos de producción', 'migration')
                    print(f"✅ URL de producción guardada")
                
                # Establecer modo por defecto si no existe
                current_mode = SystemConfig.get('database_mode')
                if not current_mode:
                    SystemConfig.set('database_mode', 'prod', 'Modo de base de datos actual', 'migration')
                    print("✅ Modo por defecto establecido: prod")
                else:
                    print(f"✅ Modo actual: {current_mode}")
                
            else:
                print("❌ Error: La tabla 'system_config' no se pudo crear")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Error al crear tabla system_config: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_system_config()
    if success:
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n❌ Migración falló")
        exit(1)

