-- ============================================================================
-- MIGRACIÓN UNIFICADA: BIMBA Cajas MVP1 + Payment Stack (GETNET + KLAP)
-- Fecha: 2025-01-15
-- Versión: MySQL
-- Descripción: Agrega campos para sistema de cajas MVP1 y estrategia de pagos
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- mysqldump -u usuario -p bimba_db > backup_antes_mvp1_$(date +%Y%m%d_%H%M%S).sql

START TRANSACTION;

-- ============================================================================
-- TABLA: pos_registers
-- ============================================================================

-- MVP1: Campos de configuración de cajas
-- Verificar si columna register_type existe antes de agregar
SET @col_exists_register_type = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'register_type'
);

SET @sql_register_type = IF(
    @col_exists_register_type = 0,
    'ALTER TABLE pos_registers ADD COLUMN register_type VARCHAR(50) NULL',
    'SELECT "Columna register_type ya existe" as message'
);

PREPARE stmt_register_type FROM @sql_register_type;
EXECUTE stmt_register_type;
DEALLOCATE PREPARE stmt_register_type;

CREATE INDEX IF NOT EXISTS idx_pos_registers_register_type ON pos_registers(register_type);

-- Verificar si columna devices existe antes de agregar
SET @col_exists_devices = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'devices'
);

SET @sql_devices = IF(
    @col_exists_devices = 0,
    'ALTER TABLE pos_registers ADD COLUMN devices TEXT NULL',
    'SELECT "Columna devices ya existe" as message'
);

PREPARE stmt_devices FROM @sql_devices;
EXECUTE stmt_devices;
DEALLOCATE PREPARE stmt_devices;

-- Verificar si columna operation_mode existe antes de agregar
SET @col_exists_operation_mode = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'operation_mode'
);

SET @sql_operation_mode = IF(
    @col_exists_operation_mode = 0,
    'ALTER TABLE pos_registers ADD COLUMN operation_mode TEXT NULL',
    'SELECT "Columna operation_mode ya existe" as message'
);

PREPARE stmt_operation_mode FROM @sql_operation_mode;
EXECUTE stmt_operation_mode;
DEALLOCATE PREPARE stmt_operation_mode;

-- Verificar si columna payment_methods existe antes de agregar
SET @col_exists_payment_methods = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'payment_methods'
);

SET @sql_payment_methods = IF(
    @col_exists_payment_methods = 0,
    'ALTER TABLE pos_registers ADD COLUMN payment_methods TEXT NULL',
    'SELECT "Columna payment_methods ya existe" as message'
);

PREPARE stmt_payment_methods FROM @sql_payment_methods;
EXECUTE stmt_payment_methods;
DEALLOCATE PREPARE stmt_payment_methods;

-- Verificar si columna responsible_user_id existe antes de agregar
SET @col_exists_responsible_user_id = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'responsible_user_id'
);

SET @sql_responsible_user_id = IF(
    @col_exists_responsible_user_id = 0,
    'ALTER TABLE pos_registers ADD COLUMN responsible_user_id VARCHAR(50) NULL',
    'SELECT "Columna responsible_user_id ya existe" as message'
);

PREPARE stmt_responsible_user_id FROM @sql_responsible_user_id;
EXECUTE stmt_responsible_user_id;
DEALLOCATE PREPARE stmt_responsible_user_id;

CREATE INDEX IF NOT EXISTS idx_pos_registers_responsible_user ON pos_registers(responsible_user_id);

-- Verificar si columna responsible_role existe antes de agregar
SET @col_exists_responsible_role = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'responsible_role'
);

SET @sql_responsible_role = IF(
    @col_exists_responsible_role = 0,
    'ALTER TABLE pos_registers ADD COLUMN responsible_role VARCHAR(50) NULL',
    'SELECT "Columna responsible_role ya existe" as message'
);

PREPARE stmt_responsible_role FROM @sql_responsible_role;
EXECUTE stmt_responsible_role;
DEALLOCATE PREPARE stmt_responsible_role;

-- Verificar si columna operational_status existe antes de agregar
SET @col_exists_operational_status = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'operational_status'
);

SET @sql_operational_status = IF(
    @col_exists_operational_status = 0,
    'ALTER TABLE pos_registers ADD COLUMN operational_status VARCHAR(50) NOT NULL DEFAULT 'active'',
    'SELECT "Columna operational_status ya existe" as message'
);

PREPARE stmt_operational_status FROM @sql_operational_status;
EXECUTE stmt_operational_status;
DEALLOCATE PREPARE stmt_operational_status;

CREATE INDEX IF NOT EXISTS idx_pos_registers_operational_status ON pos_registers(operational_status);

-- Verificar si columna fallback_config existe antes de agregar
SET @col_exists_fallback_config = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'fallback_config'
);

SET @sql_fallback_config = IF(
    @col_exists_fallback_config = 0,
    'ALTER TABLE pos_registers ADD COLUMN fallback_config TEXT NULL',
    'SELECT "Columna fallback_config ya existe" as message'
);

PREPARE stmt_fallback_config FROM @sql_fallback_config;
EXECUTE stmt_fallback_config;
DEALLOCATE PREPARE stmt_fallback_config;

-- Verificar si columna fast_lane_config existe antes de agregar
SET @col_exists_fast_lane_config = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'fast_lane_config'
);

SET @sql_fast_lane_config = IF(
    @col_exists_fast_lane_config = 0,
    'ALTER TABLE pos_registers ADD COLUMN fast_lane_config TEXT NULL',
    'SELECT "Columna fast_lane_config ya existe" as message'
);

PREPARE stmt_fast_lane_config FROM @sql_fast_lane_config;
EXECUTE stmt_fast_lane_config;
DEALLOCATE PREPARE stmt_fast_lane_config;

-- Payment Stack BIMBA: GETNET + KLAP
-- Verificar si columna payment_provider_primary existe antes de agregar
SET @col_exists_payment_provider_primary = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'payment_provider_primary'
);

SET @sql_payment_provider_primary = IF(
    @col_exists_payment_provider_primary = 0,
    'ALTER TABLE pos_registers ADD COLUMN payment_provider_primary VARCHAR(50) NOT NULL DEFAULT 'GETNET'',
    'SELECT "Columna payment_provider_primary ya existe" as message'
);

PREPARE stmt_payment_provider_primary FROM @sql_payment_provider_primary;
EXECUTE stmt_payment_provider_primary;
DEALLOCATE PREPARE stmt_payment_provider_primary;

-- Verificar si columna payment_provider_backup existe antes de agregar
SET @col_exists_payment_provider_backup = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'payment_provider_backup'
);

SET @sql_payment_provider_backup = IF(
    @col_exists_payment_provider_backup = 0,
    'ALTER TABLE pos_registers ADD COLUMN payment_provider_backup VARCHAR(50) NULL',
    'SELECT "Columna payment_provider_backup ya existe" as message'
);

PREPARE stmt_payment_provider_backup FROM @sql_payment_provider_backup;
EXECUTE stmt_payment_provider_backup;
DEALLOCATE PREPARE stmt_payment_provider_backup;

-- Verificar si columna provider_config existe antes de agregar
SET @col_exists_provider_config = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'provider_config'
);

SET @sql_provider_config = IF(
    @col_exists_provider_config = 0,
    'ALTER TABLE pos_registers ADD COLUMN provider_config TEXT NULL',
    'SELECT "Columna provider_config ya existe" as message'
);

PREPARE stmt_provider_config FROM @sql_provider_config;
EXECUTE stmt_provider_config;
DEALLOCATE PREPARE stmt_provider_config;

-- Verificar si columna fallback_policy existe antes de agregar
SET @col_exists_fallback_policy = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'pos_registers'
      AND column_name = 'fallback_policy'
);

SET @sql_fallback_policy = IF(
    @col_exists_fallback_policy = 0,
    'ALTER TABLE pos_registers ADD COLUMN fallback_policy TEXT NULL',
    'SELECT "Columna fallback_policy ya existe" as message'
);

PREPARE stmt_fallback_policy FROM @sql_fallback_policy;
EXECUTE stmt_fallback_policy;
DEALLOCATE PREPARE stmt_fallback_policy;

-- Asegurar default para registros existentes (MySQL: ejecutar directamente)
UPDATE pos_registers 
SET payment_provider_primary = 'GETNET' 
WHERE payment_provider_primary IS NULL;

UPDATE pos_registers 
SET operational_status = 'active' 
WHERE operational_status IS NULL;

-- ============================================================================
-- TABLA: register_sessions
-- ============================================================================

-- MVP1: Campos de cierre con arqueo
-- Verificar si columna cash_count existe antes de agregar
SET @col_exists_cash_count = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'cash_count'
);

SET @sql_cash_count = IF(
    @col_exists_cash_count = 0,
    'ALTER TABLE register_sessions ADD COLUMN cash_count TEXT NULL',
    'SELECT "Columna cash_count ya existe" as message'
);

PREPARE stmt_cash_count FROM @sql_cash_count;
EXECUTE stmt_cash_count;
DEALLOCATE PREPARE stmt_cash_count;

-- Verificar si columna payment_totals existe antes de agregar
SET @col_exists_payment_totals = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'payment_totals'
);

SET @sql_payment_totals = IF(
    @col_exists_payment_totals = 0,
    'ALTER TABLE register_sessions ADD COLUMN payment_totals TEXT NULL',
    'SELECT "Columna payment_totals ya existe" as message'
);

PREPARE stmt_payment_totals FROM @sql_payment_totals;
EXECUTE stmt_payment_totals;
DEALLOCATE PREPARE stmt_payment_totals;

-- Verificar si columna ticket_count existe antes de agregar
SET @col_exists_ticket_count = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'ticket_count'
);

SET @sql_ticket_count = IF(
    @col_exists_ticket_count = 0,
    'ALTER TABLE register_sessions ADD COLUMN ticket_count INT NOT NULL DEFAULT 0',
    'SELECT "Columna ticket_count ya existe" as message'
);

PREPARE stmt_ticket_count FROM @sql_ticket_count;
EXECUTE stmt_ticket_count;
DEALLOCATE PREPARE stmt_ticket_count;

-- Verificar si columna cash_difference existe antes de agregar
SET @col_exists_cash_difference = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'cash_difference'
);

SET @sql_cash_difference = IF(
    @col_exists_cash_difference = 0,
    'ALTER TABLE register_sessions ADD COLUMN cash_difference DECIMAL(10, 2) NULL',
    'SELECT "Columna cash_difference ya existe" as message'
);

PREPARE stmt_cash_difference FROM @sql_cash_difference;
EXECUTE stmt_cash_difference;
DEALLOCATE PREPARE stmt_cash_difference;

-- Verificar si columna incidents existe antes de agregar
SET @col_exists_incidents = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'incidents'
);

SET @sql_incidents = IF(
    @col_exists_incidents = 0,
    'ALTER TABLE register_sessions ADD COLUMN incidents TEXT NULL',
    'SELECT "Columna incidents ya existe" as message'
);

PREPARE stmt_incidents FROM @sql_incidents;
EXECUTE stmt_incidents;
DEALLOCATE PREPARE stmt_incidents;

-- Verificar si columna close_notes existe antes de agregar
SET @col_exists_close_notes = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'close_notes'
);

SET @sql_close_notes = IF(
    @col_exists_close_notes = 0,
    'ALTER TABLE register_sessions ADD COLUMN close_notes TEXT NULL',
    'SELECT "Columna close_notes ya existe" as message'
);

PREPARE stmt_close_notes FROM @sql_close_notes;
EXECUTE stmt_close_notes;
DEALLOCATE PREPARE stmt_close_notes;

-- Payment Stack BIMBA: Tracking de providers y fallback
-- Verificar si columna payment_provider_used_primary_count existe antes de agregar
SET @col_exists_payment_provider_used_primary_count = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'payment_provider_used_primary_count'
);

SET @sql_payment_provider_used_primary_count = IF(
    @col_exists_payment_provider_used_primary_count = 0,
    'ALTER TABLE register_sessions ADD COLUMN payment_provider_used_primary_count INT NOT NULL DEFAULT 0',
    'SELECT "Columna payment_provider_used_primary_count ya existe" as message'
);

PREPARE stmt_payment_provider_used_primary_count FROM @sql_payment_provider_used_primary_count;
EXECUTE stmt_payment_provider_used_primary_count;
DEALLOCATE PREPARE stmt_payment_provider_used_primary_count;

-- Verificar si columna payment_provider_used_backup_count existe antes de agregar
SET @col_exists_payment_provider_used_backup_count = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'payment_provider_used_backup_count'
);

SET @sql_payment_provider_used_backup_count = IF(
    @col_exists_payment_provider_used_backup_count = 0,
    'ALTER TABLE register_sessions ADD COLUMN payment_provider_used_backup_count INT NOT NULL DEFAULT 0',
    'SELECT "Columna payment_provider_used_backup_count ya existe" as message'
);

PREPARE stmt_payment_provider_used_backup_count FROM @sql_payment_provider_used_backup_count;
EXECUTE stmt_payment_provider_used_backup_count;
DEALLOCATE PREPARE stmt_payment_provider_used_backup_count;

-- Verificar si columna fallback_events existe antes de agregar
SET @col_exists_fallback_events = (
    SELECT COUNT(*) 
    FROM information_schema.columns 
    WHERE table_schema = DATABASE()
      AND table_name = 'register_sessions'
      AND column_name = 'fallback_events'
);

SET @sql_fallback_events = IF(
    @col_exists_fallback_events = 0,
    'ALTER TABLE register_sessions ADD COLUMN fallback_events TEXT NULL',
    'SELECT "Columna fallback_events ya existe" as message'
);

PREPARE stmt_fallback_events FROM @sql_fallback_events;
EXECUTE stmt_fallback_events;
DEALLOCATE PREPARE stmt_fallback_events;

-- Asegurar defaults para registros existentes
UPDATE register_sessions 
SET ticket_count = 0 
WHERE ticket_count IS NULL;

UPDATE register_sessions 
SET payment_provider_used_primary_count = 0 
WHERE payment_provider_used_primary_count IS NULL;

UPDATE register_sessions 
SET payment_provider_used_backup_count = 0 
WHERE payment_provider_used_backup_count IS NULL;

COMMIT;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- Verificar columnas en pos_registers
SELECT 
    'pos_registers' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'pos_registers'
  AND column_name IN (
    'register_type', 'devices', 'operation_mode', 'payment_methods',
    'responsible_user_id', 'responsible_role', 'operational_status',
    'fallback_config', 'fast_lane_config',
    'payment_provider_primary', 'payment_provider_backup', 'provider_config', 'fallback_policy'
  )
ORDER BY column_name;

-- Verificar columnas en register_sessions
SELECT 
    'register_sessions' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'register_sessions'
  AND column_name IN (
    'cash_count', 'payment_totals', 'ticket_count', 'cash_difference',
    'incidents', 'close_notes',
    'payment_provider_used_primary_count', 'payment_provider_used_backup_count', 'fallback_events'
  )
ORDER BY column_name;

