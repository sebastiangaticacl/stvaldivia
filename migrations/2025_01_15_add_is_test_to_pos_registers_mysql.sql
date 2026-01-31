-- ============================================================================
-- MIGRACIÓN: Agregar campo is_test a pos_registers
-- Fecha: 2025-01-15
-- Versión: MySQL
-- Descripción: Agrega flag para identificar cajas de prueba
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para producción)
-- ============================================================================

START TRANSACTION;

-- Agregar columna is_test (MySQL no soporta IF NOT EXISTS en ALTER TABLE)
-- Verificar si existe antes de agregar
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'is_test'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE pos_registers ADD COLUMN is_test TINYINT(1) NOT NULL DEFAULT 0',
    'SELECT "Columna is_test ya existe" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Crear índice para filtrado rápido
CREATE INDEX IF NOT EXISTS idx_pos_registers_is_test ON pos_registers(is_test);

-- Comentario (MySQL usa ALTER TABLE para comentarios de columna)
ALTER TABLE pos_registers 
MODIFY COLUMN is_test TINYINT(1) NOT NULL DEFAULT 0 
COMMENT 'Flag para identificar cajas de prueba (no usar en operación real)';

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
WHERE table_schema = DATABASE()
  AND table_name = 'pos_registers'
  AND column_name = 'is_test';

SELECT 
    index_name, 
    column_name,
    seq_in_index
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'pos_registers'
  AND index_name = 'idx_pos_registers_is_test';

