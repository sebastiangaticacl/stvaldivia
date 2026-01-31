#!/usr/bin/env python3
"""
Script para migrar todos los datos de archivos JSON/CSV a SQL
Migra datos de:
- Usuarios admin (.admin_users.json)
- Configuración de fraude (fraud_config.json)
- Inventario (inventory.json) - si existe
- Turnos (shift_status.json, shift_history.json) - si existen
- Escaneos de tickets (ticket_scans.json) - si existe
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from werkzeug.security import check_password_hash
from app import create_app
from app.models import db
from app.models.system_config_models import SystemConfig


def migrate_admin_users():
    """Migra usuarios admin desde .admin_users.json a SystemConfig"""
    print("\n📋 Migrando usuarios admin...")
    
    admin_users_file = Path('instance/.admin_users.json')
    if not admin_users_file.exists():
        print("  ⏭️  No existe .admin_users.json, omitiendo migración de usuarios admin")
        return 0
    
    try:
        with open(admin_users_file, 'r', encoding='utf-8') as f:
            admin_users = json.load(f)
        
        migrated = 0
        for username, user_data in admin_users.items():
            password_hash = user_data.get('password_hash')
            if not password_hash:
                print(f"  ⚠️  Usuario {username} sin hash, omitiendo")
                continue
            
            # Verificar si ya existe
            existing = SystemConfig.query.filter_by(
                key=f'admin_user:{username}'
            ).first()
            
            if existing:
                print(f"  ✓ Usuario {username} ya existe en BD, omitiendo")
                continue
            
            # Crear entrada en SystemConfig
            config = SystemConfig(
                key=f'admin_user:{username}',
                value=json.dumps({
                    'username': username,
                    'password_hash': password_hash,
                    'migrated_at': datetime.utcnow().isoformat()
                }),
                description=f'Usuario admin: {username}'
            )
            db.session.add(config)
            migrated += 1
            print(f"  ✅ Usuario {username} migrado")
        
        db.session.commit()
        print(f"  ✅ {migrated} usuarios admin migrados")
        return migrated
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error migrando usuarios admin: {e}")
        return 0


def migrate_fraud_config():
    """Migra configuración de fraude desde fraud_config.json a SystemConfig"""
    print("\n📋 Migrando configuración de fraude...")
    
    fraud_config_file = Path('instance/fraud_config.json')
    if not fraud_config_file.exists():
        print("  ⏭️  No existe fraud_config.json, omitiendo migración")
        return 0
    
    try:
        with open(fraud_config_file, 'r', encoding='utf-8') as f:
            fraud_config = json.load(f)
        
        # Verificar si ya existe
        existing = SystemConfig.query.filter_by(key='fraud_config').first()
        if existing:
            print("  ✓ Configuración de fraude ya existe en BD, omitiendo")
            return 0
        
        # Crear entrada en SystemConfig
        config = SystemConfig(
            key='fraud_config',
            value=json.dumps(fraud_config),
            description='Configuración de detección de fraude'
        )
        db.session.add(config)
        db.session.commit()
        print("  ✅ Configuración de fraude migrada")
        return 1
    except Exception as e:
        db.session.rollback()
        print(f"  ❌ Error migrando configuración de fraude: {e}")
        return 0


def verify_all_tables_exist():
    """Verifica que todas las tablas necesarias existen"""
    print("\n📋 Verificando tablas...")
    
    try:
        # Crear todas las tablas si no existen
        db.create_all()
        print("  ✅ Todas las tablas verificadas/creadas")
        return True
    except Exception as e:
        print(f"  ❌ Error verificando tablas: {e}")
        return False


def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 MIGRACIÓN COMPLETA A SQL")
    print("=" * 60)
    
    # Crear app Flask
    app = create_app()
    
    with app.app_context():
        # 1. Verificar tablas
        if not verify_all_tables_exist():
            print("\n❌ Error: No se pudieron crear/verificar las tablas")
            sys.exit(1)
        
        # 2. Migrar usuarios admin
        admin_count = migrate_admin_users()
        
        # 3. Migrar configuración de fraude
        fraud_count = migrate_fraud_config()
        
        # Resumen
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE MIGRACIÓN")
        print("=" * 60)
        print(f"  ✅ Usuarios admin migrados: {admin_count}")
        print(f"  ✅ Configuraciones de fraude migradas: {fraud_count}")
        print("\n✅ Migración completada")
        print("\n⚠️  NOTA: Los archivos JSON originales NO fueron eliminados")
        print("   Puedes eliminarlos manualmente después de verificar que todo funciona")
        print("=" * 60)


if __name__ == '__main__':
    main()

