"""
Script para migrar campos adicionales de TPV a la base de datos
Ejecutar: python3 migrar_tpv_campos_adicionales.py
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar que estamos en el entorno correcto
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    print("❌ ERROR: DATABASE_URL no configurado")
    sys.exit(1)

print("="*60)
print("🔄 MIGRACIÓN: Campos adicionales para TPV")
print("="*60)

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    # Conectar a la base de datos
    print(f"\n📡 Conectando a base de datos...")
    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("✅ Conectado a la base de datos\n")
    
    # Leer y ejecutar migración SQL
    migration_sql = """
    -- Agregar nuevos campos
    ALTER TABLE pos_registers 
    ADD COLUMN IF NOT EXISTS location VARCHAR(200),
    ADD COLUMN IF NOT EXISTS tpv_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS default_location VARCHAR(100),
    ADD COLUMN IF NOT EXISTS printer_config TEXT,
    ADD COLUMN IF NOT EXISTS max_concurrent_sessions INTEGER DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS requires_cash_count BOOLEAN DEFAULT TRUE NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    
    -- Crear índices
    CREATE INDEX IF NOT EXISTS idx_pos_registers_type ON pos_registers(tpv_type, is_active);
    CREATE INDEX IF NOT EXISTS idx_pos_registers_location ON pos_registers(location);
    
    -- Actualizar updated_at con created_at para registros existentes
    UPDATE pos_registers SET updated_at = created_at WHERE updated_at IS NULL;
    """
    
    print("🔧 Ejecutando migración...")
    cursor.execute(migration_sql)
    
    print("✅ Migración ejecutada exitosamente\n")
    
    # Verificar que los campos se agregaron
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'pos_registers'
        AND column_name IN ('location', 'tpv_type', 'default_location', 'printer_config', 
                           'max_concurrent_sessions', 'requires_cash_count', 'updated_at')
        ORDER BY column_name;
    """)
    
    columns = cursor.fetchall()
    if columns:
        print("📋 Campos agregados:")
        for col in columns:
            print(f"   ✅ {col[0]} ({col[1]})")
    else:
        print("⚠️  No se encontraron los nuevos campos")
    
    # Verificar índices
    cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'pos_registers' 
        AND indexname LIKE 'idx_pos_registers_%'
        ORDER BY indexname;
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        print("\n📊 Índices creados:")
        for idx in indexes:
            print(f"   ✅ {idx[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

