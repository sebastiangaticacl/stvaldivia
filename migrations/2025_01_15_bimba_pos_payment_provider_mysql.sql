-- ============================================================================
-- MIGRACIÓN: BIMBA POS - Payment Provider + Register Session ID
-- Fecha: 2025-01-15
-- Versión: MySQL
-- Descripción: Agrega campos para trazabilidad y conciliación de pagos
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- mysqldump -u usuario -p bimba_db > backup_antes_payment_provider_$(date +%Y%m%d_%H%M%S).sql

START TRANSACTION;

-- ============================================================================
-- TABLA: pos_sales
-- ============================================================================

-- register_session_id: Asociación con sesión de caja (trazabilidad)
-- Verificar si columna register_session_id existe
SET @col_exists_register_session_id = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_sales'
      AND column_name = 'register_session_id'
);

SET @sql_register_session_id = IF(
    @col_exists_register_session_id = 0,
    'ALTER TABLE pos_sales ADD COLUMN register_session_id INT NULL',
    'SELECT "Columna register_session_id ya existe" as message'
);

PREPARE stmt_register_session_id FROM @sql_register_session_id;
EXECUTE stmt_register_session_id;
DEALLOCATE PREPARE stmt_register_session_id;

-- Crear índice para register_session_id
CREATE INDEX IF NOT EXISTS idx_pos_sales_register_session ON pos_sales(register_session_id);

-- Agregar FK si no existe (opcional, puede fallar si register_sessions no existe aún)
-- Nota: MySQL requiere que la tabla exista, verificar antes
SET @fk_exists = (
    SELECT COUNT(*) 
    FROM information_schema.table_constraints 
    WHERE constraint_schema = DATABASE()
      AND constraint_name = 'pos_sales_register_session_id_fkey'
      AND table_name = 'pos_sales'
);

SET @register_sessions_exists = (
    SELECT COUNT(*) 
    FROM information_schema.tables 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
);

SET @sql = IF(
    @fk_exists = 0 AND @register_sessions_exists > 0,
    'ALTER TABLE pos_sales 
     ADD CONSTRAINT pos_sales_register_session_id_fkey 
     FOREIGN KEY (register_session_id) REFERENCES register_sessions(id) ON DELETE SET NULL',
    'SELECT "FK ya existe o tabla register_sessions no existe" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- payment_provider: Procesador de pago (GETNET, KLAP, NONE)
-- Separado de payment_type (método: cash/debit/credit)
-- Verificar si columna payment_provider existe
SET @col_exists_payment_provider = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_sales'
      AND column_name = 'payment_provider'
);

SET @sql_payment_provider = IF(
    @col_exists_payment_provider = 0,
    'ALTER TABLE pos_sales ADD COLUMN payment_provider VARCHAR(50) NULL',
    'SELECT "Columna payment_provider ya existe" as message'
);

PREPARE stmt_payment_provider FROM @sql_payment_provider;
EXECUTE stmt_payment_provider;
DEALLOCATE PREPARE stmt_payment_provider;

-- Crear índice para payment_provider
CREATE INDEX IF NOT EXISTS idx_pos_sales_payment_provider ON pos_sales(payment_provider);

-- Actualizar registros existentes: payment_provider = NONE para efectivo, NULL para otros
-- MySQL: usar LOWER() LIKE en lugar de ILIKE
UPDATE pos_sales 
SET payment_provider = 'NONE' 
WHERE (LOWER(payment_type) LIKE '%efectivo%' OR payment_type = 'cash')
  AND payment_provider IS NULL;

COMMIT;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- Verificar columnas agregadas
SELECT 
    'pos_sales' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'pos_sales'
  AND column_name IN ('register_session_id', 'payment_provider')
ORDER BY column_name;

-- Verificar índices
SELECT 
    index_name, 
    column_name,
    seq_in_index
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'pos_sales'
  AND index_name IN ('idx_pos_sales_register_session', 'idx_pos_sales_payment_provider')
ORDER BY index_name, seq_in_index;

