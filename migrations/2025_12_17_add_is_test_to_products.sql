-- ============================================================================
-- MIGRACIÓN: Agregar campo is_test a products
-- Fecha: 2025-12-17
-- Descripción: Agrega flag para identificar productos de prueba (QA)
-- Compatibilidad: PostgreSQL (idempotente, seguro para ejecutar múltiples veces)
-- ============================================================================

BEGIN;

-- Agregar columna is_test
ALTER TABLE products
ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE;

-- Índice para filtrado rápido (opcional)
CREATE INDEX IF NOT EXISTS idx_products_is_test ON products(is_test);

-- Comentario
COMMENT ON COLUMN products.is_test IS 'Flag para identificar productos de prueba (no usar en operación real)';

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
WHERE table_name = 'products'
  AND column_name = 'is_test';


