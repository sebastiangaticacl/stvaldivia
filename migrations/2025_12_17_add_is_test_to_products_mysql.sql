-- ============================================================================
-- MIGRACIÓN: Agregar campo is_test a products
-- Fecha: 2025-12-17
-- Versión: MySQL
-- Descripción: Agrega flag para identificar productos de prueba (QA)
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para ejecutar múltiples veces)
-- ============================================================================

START TRANSACTION;

-- Agregar columna is_test (MySQL no soporta IF NOT EXISTS en ALTER TABLE)
SET @col_exists = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'products'
      AND column_name = 'is_test'
);

SET @sql = IF(
    @col_exists = 0,
    'ALTER TABLE products ADD COLUMN is_test TINYINT(1) DEFAULT 0',
    'SELECT "Columna is_test ya existe" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Índice para filtrado rápido (opcional)
CREATE INDEX IF NOT EXISTS idx_products_is_test ON products(is_test);

-- Comentario (MySQL usa ALTER TABLE para comentarios de columna)
ALTER TABLE products
MODIFY COLUMN is_test TINYINT(1) DEFAULT 0 
COMMENT 'Flag para identificar productos de prueba (no usar en operación real)';

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
  AND table_name = 'products'
  AND column_name = 'is_test';

