-- ============================================================================
-- MIGRACIÓN UNIFICADA: BIMBA Cajas MVP1 + Payment Stack (GETNET + KLAP)
-- Fecha: 2025-01-15
-- Descripción: Agrega campos para sistema de cajas MVP1 y estrategia de pagos
-- Compatibilidad: PostgreSQL (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- pg_dump -U postgres -d bimba_db > backup_antes_mvp1_$(date +%Y%m%d_%H%M%S).sql

BEGIN;

-- ============================================================================
-- TABLA: pos_registers
-- ============================================================================

-- MVP1: Campos de configuración de cajas
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS register_type VARCHAR(50) NULL;

CREATE INDEX IF NOT EXISTS idx_pos_registers_register_type ON pos_registers(register_type);

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS devices TEXT NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS operation_mode TEXT NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_methods TEXT NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS responsible_user_id VARCHAR(50) NULL;

CREATE INDEX IF NOT EXISTS idx_pos_registers_responsible_user ON pos_registers(responsible_user_id);

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS responsible_role VARCHAR(50) NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS operational_status VARCHAR(50) NOT NULL DEFAULT 'active';

CREATE INDEX IF NOT EXISTS idx_pos_registers_operational_status ON pos_registers(operational_status);

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fallback_config TEXT NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fast_lane_config TEXT NULL;

-- Payment Stack BIMBA: GETNET + KLAP
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_provider_primary VARCHAR(50) NOT NULL DEFAULT 'GETNET';

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_provider_backup VARCHAR(50) NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS provider_config TEXT NULL;

ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fallback_policy TEXT NULL;

-- Asegurar default para registros existentes (si la columna ya existe pero sin default)
DO $$
BEGIN
    -- Si hay registros sin payment_provider_primary, actualizar
    UPDATE pos_registers 
    SET payment_provider_primary = 'GETNET' 
    WHERE payment_provider_primary IS NULL;
    
    -- Si hay registros sin operational_status, actualizar
    UPDATE pos_registers 
    SET operational_status = 'active' 
    WHERE operational_status IS NULL;
END $$;

-- ============================================================================
-- TABLA: register_sessions
-- ============================================================================

-- MVP1: Campos de cierre con arqueo
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS cash_count TEXT NULL;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_totals TEXT NULL;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS ticket_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS cash_difference NUMERIC(10, 2) NULL;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS incidents TEXT NULL;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS close_notes TEXT NULL;

-- Payment Stack BIMBA: Tracking de providers y fallback
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_provider_used_primary_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_provider_used_backup_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS fallback_events TEXT NULL;

-- Asegurar defaults para registros existentes
DO $$
BEGIN
    UPDATE register_sessions 
    SET ticket_count = 0 
    WHERE ticket_count IS NULL;
    
    UPDATE register_sessions 
    SET payment_provider_used_primary_count = 0 
    WHERE payment_provider_used_primary_count IS NULL;
    
    UPDATE register_sessions 
    SET payment_provider_used_backup_count = 0 
    WHERE payment_provider_used_backup_count IS NULL;
END $$;

-- ============================================================================
-- VERIFICACIÓN FINAL
-- ============================================================================

-- Verificar columnas en pos_registers
DO $$
DECLARE
    missing_cols TEXT[];
    col_name TEXT;
    required_cols TEXT[] := ARRAY[
        'register_type', 'devices', 'operation_mode', 'payment_methods',
        'responsible_user_id', 'responsible_role', 'operational_status',
        'fallback_config', 'fast_lane_config',
        'payment_provider_primary', 'payment_provider_backup', 'provider_config', 'fallback_policy'
    ];
BEGIN
    FOREACH col_name IN ARRAY required_cols
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'pos_registers' AND column_name = col_name
        ) THEN
            missing_cols := array_append(missing_cols, col_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_cols, 1) > 0 THEN
        RAISE EXCEPTION 'Columnas faltantes en pos_registers: %', array_to_string(missing_cols, ', ');
    END IF;
END $$;

-- Verificar columnas en register_sessions
DO $$
DECLARE
    missing_cols TEXT[];
    col_name TEXT;
    required_cols TEXT[] := ARRAY[
        'cash_count', 'payment_totals', 'ticket_count', 'cash_difference',
        'incidents', 'close_notes',
        'payment_provider_used_primary_count', 'payment_provider_used_backup_count', 'fallback_events'
    ];
BEGIN
    FOREACH col_name IN ARRAY required_cols
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'register_sessions' AND column_name = col_name
        ) THEN
            missing_cols := array_append(missing_cols, col_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_cols, 1) > 0 THEN
        RAISE EXCEPTION 'Columnas faltantes en register_sessions: %', array_to_string(missing_cols, ', ');
    END IF;
END $$;

COMMIT;

-- ============================================================================
-- REPORTE FINAL
-- ============================================================================

-- Mostrar resumen de columnas agregadas
SELECT 
    'pos_registers' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name IN (
    'register_type', 'devices', 'operation_mode', 'payment_methods',
    'responsible_user_id', 'responsible_role', 'operational_status',
    'fallback_config', 'fast_lane_config',
    'payment_provider_primary', 'payment_provider_backup', 'provider_config', 'fallback_policy'
)
ORDER BY column_name;

SELECT 
    'register_sessions' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'register_sessions'
AND column_name IN (
    'cash_count', 'payment_totals', 'ticket_count', 'cash_difference',
    'incidents', 'close_notes',
    'payment_provider_used_primary_count', 'payment_provider_used_backup_count', 'fallback_events'
)
ORDER BY column_name;


