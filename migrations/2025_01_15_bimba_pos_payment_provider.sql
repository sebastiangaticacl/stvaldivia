-- ============================================================================
-- MIGRACIÓN: BIMBA POS - Payment Provider + Register Session ID
-- Fecha: 2025-01-15
-- Descripción: Agrega campos para trazabilidad y conciliación de pagos
-- Compatibilidad: PostgreSQL (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- pg_dump -U postgres -d bimba_db > backup_antes_payment_provider_$(date +%Y%m%d_%H%M%S).sql

BEGIN;

-- ============================================================================
-- TABLA: pos_sales
-- ============================================================================

-- register_session_id: Asociación con sesión de caja (trazabilidad)
ALTER TABLE pos_sales 
ADD COLUMN IF NOT EXISTS register_session_id INTEGER NULL;

-- Crear índice para register_session_id
CREATE INDEX IF NOT EXISTS idx_pos_sales_register_session ON pos_sales(register_session_id);

-- Agregar FK si no existe (opcional, puede fallar si register_sessions no existe aún)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'pos_sales_register_session_id_fkey'
        AND table_name = 'pos_sales'
    ) THEN
        ALTER TABLE pos_sales 
        ADD CONSTRAINT pos_sales_register_session_id_fkey 
        FOREIGN KEY (register_session_id) REFERENCES register_sessions(id) ON DELETE SET NULL;
    END IF;
END $$;

-- payment_provider: Procesador de pago (GETNET, KLAP, NONE)
-- Separado de payment_type (método: cash/debit/credit)
ALTER TABLE pos_sales 
ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(50) NULL;

-- Crear índice para payment_provider
CREATE INDEX IF NOT EXISTS idx_pos_sales_payment_provider ON pos_sales(payment_provider);

-- Actualizar registros existentes: payment_provider = NONE para efectivo, NULL para otros
DO $$
BEGIN
    -- Efectivo siempre es NONE (no hay procesador)
    UPDATE pos_sales 
    SET payment_provider = 'NONE' 
    WHERE payment_type ILIKE '%efectivo%' OR payment_type = 'cash'
    AND payment_provider IS NULL;
    
    -- Débito/Crédito sin provider específico = NULL (se completará en integración real)
    -- Por ahora dejamos NULL para no asumir provider
END $$;

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
WHERE table_name = 'pos_sales'
AND column_name IN ('register_session_id', 'payment_provider')
ORDER BY column_name;

-- Verificar índices
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'pos_sales'
AND indexname IN ('idx_pos_sales_register_session', 'idx_pos_sales_payment_provider');


