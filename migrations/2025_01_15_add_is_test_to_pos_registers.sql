-- ============================================================================
-- MIGRACIÓN: Agregar campo is_test a pos_registers
-- Fecha: 2025-01-15
-- Descripción: Agrega flag para identificar cajas de prueba
-- Compatibilidad: PostgreSQL (idempotente, seguro para producción)
-- ============================================================================

BEGIN;

-- Agregar columna is_test
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

-- Crear índice para filtrado rápido
CREATE INDEX IF NOT EXISTS idx_pos_registers_is_test ON pos_registers(is_test);

-- Comentario
COMMENT ON COLUMN pos_registers.is_test IS 'Flag para identificar cajas de prueba (no usar en operación real)';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name = 'is_test';

SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'pos_registers'
AND indexname = 'idx_pos_registers_is_test';


