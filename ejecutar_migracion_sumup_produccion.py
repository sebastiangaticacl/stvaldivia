#!/usr/bin/env python3
"""
Script para ejecutar la migración de SumUp en producción
Ejecuta las sentencias SQL de la migración de forma segura
"""
import mysql.connector
from mysql.connector import Error
import sys
import re

# Configuración de base de datos
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'bimba_user',
    'password': 'a0LVWyEuWwZ0WDg2CL3bGmGY4',
    'database': 'bimba_db'
}

def ejecutar_migracion():
    """Ejecuta la migración de SumUp"""
    print("=" * 60)
    print("🔄 EJECUTANDO MIGRACIÓN SUMUP")
    print("=" * 60)
    print()
    
    try:
        # Conectar a la base de datos
        print("📡 Conectando a base de datos...")
        conn = mysql.connector.connect(**DB_CONFIG)
        
        if not conn.is_connected():
            print("❌ No se pudo conectar a la base de datos")
            return False
        
        print("✅ Conectado a base de datos")
        cursor = conn.cursor()
        
        # Verificar que la tabla pagos existe
        cursor.execute("SHOW TABLES LIKE 'pagos'")
        if not cursor.fetchone():
            print("❌ La tabla 'pagos' no existe")
            cursor.close()
            conn.close()
            return False
        
        print("✅ Tabla 'pagos' existe")
        
        # Verificar campos actuales
        cursor.execute("DESCRIBE pagos")
        columns = {col[0]: col for col in cursor.fetchall()}
        
        campos_requeridos = {
            'sumup_checkout_id': 'VARCHAR(100)',
            'sumup_checkout_url': 'TEXT',
            'sumup_merchant_code': 'VARCHAR(50)'
        }
        
        campos_faltantes = {k: v for k, v in campos_requeridos.items() if k not in columns}
        
        if not campos_faltantes:
            print("✅ Todos los campos SumUp ya existen")
            cursor.close()
            conn.close()
            return True
        
        print(f"📝 Campos a agregar: {list(campos_faltantes.keys())}")
        print()
        
        # Leer archivo de migración
        with open('migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql', 'r') as f:
            migration_sql = f.read()
        
        # Ejecutar migración usando un enfoque más simple
        # Agregar campos directamente si no existen
        for campo, tipo in campos_faltantes.items():
            try:
                if campo == 'sumup_checkout_id':
                    sql = "ALTER TABLE pagos ADD COLUMN sumup_checkout_id VARCHAR(100) NULL COMMENT 'ID del checkout de SumUp'"
                elif campo == 'sumup_checkout_url':
                    sql = "ALTER TABLE pagos ADD COLUMN sumup_checkout_url TEXT NULL COMMENT 'URL del checkout de SumUp para generar QR'"
                elif campo == 'sumup_merchant_code':
                    sql = "ALTER TABLE pagos ADD COLUMN sumup_merchant_code VARCHAR(50) NULL COMMENT 'Código del comerciante SumUp'"
                else:
                    continue
                
                cursor.execute(sql)
                conn.commit()
                print(f"✅ Campo '{campo}' agregado")
                
            except Error as e:
                if 'Duplicate column name' in str(e):
                    print(f"⚠️  Campo '{campo}' ya existe (saltando)")
                else:
                    print(f"❌ Error al agregar campo '{campo}': {e}")
                    cursor.close()
                    conn.close()
                    return False
        
        # Crear índice si no existe
        try:
            cursor.execute("SHOW INDEX FROM pagos WHERE Key_name = 'idx_pagos_sumup_checkout_id'")
            if not cursor.fetchone():
                cursor.execute("CREATE INDEX idx_pagos_sumup_checkout_id ON pagos (sumup_checkout_id)")
                conn.commit()
                print("✅ Índice 'idx_pagos_sumup_checkout_id' creado")
            else:
                print("✅ Índice 'idx_pagos_sumup_checkout_id' ya existe")
        except Error as e:
            if 'Duplicate key name' in str(e):
                print("⚠️  Índice ya existe (saltando)")
            else:
                print(f"⚠️  Error al crear índice: {e}")
        
        # Verificar resultado final
        cursor.execute("DESCRIBE pagos")
        columns_after = {col[0]: col for col in cursor.fetchall()}
        
        todos_presentes = all(campo in columns_after for campo in campos_requeridos.keys())
        
        if todos_presentes:
            print()
            print("=" * 60)
            print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            print()
            print("Campos SumUp en tabla 'pagos':")
            for campo in campos_requeridos.keys():
                if campo in columns_after:
                    print(f"  ✅ {campo}")
            return True
        else:
            print()
            print("⚠️  Algunos campos pueden no haberse agregado correctamente")
            return False
        
    except Error as e:
        print(f"❌ Error de base de datos: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            if 'conn' in locals() and conn.is_connected():
                if 'cursor' in locals():
                    cursor.close()
                conn.close()
                print()
                print("📡 Conexión cerrada")
        except:
            pass

if __name__ == '__main__':
    success = ejecutar_migracion()
    sys.exit(0 if success else 1)

