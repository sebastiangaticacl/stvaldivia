-- ============================================================================
-- MIGRACIÓN: PaymentIntent - Sistema de intenciones de pago para GETNET
-- Fecha: 2025-01-15
-- Descripción: Tabla para gestionar intenciones de pago con agente local
-- Compatibilidad: PostgreSQL (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- pg_dump -U postgres -d bimba_db > backup_antes_payment_intents_$(date +%Y%m%d_%H%M%S).sql

BEGIN;

-- ============================================================================
-- TABLA: payment_intents
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Contexto de la transacción
    register_id VARCHAR(50) NOT NULL,
    register_session_id INTEGER NULL,
    employee_id VARCHAR(50) NOT NULL,
    employee_name VARCHAR(200) NOT NULL,
    
    -- Monto y moneda
    amount_total NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CLP',
    
    -- Carrito (JSON) y hash para idempotencia
    cart_json TEXT NOT NULL,
    cart_hash VARCHAR(64) NOT NULL,
    
    -- Provider y estado
    provider VARCHAR(50) NOT NULL DEFAULT 'GETNET',
    status VARCHAR(20) NOT NULL DEFAULT 'CREATED',
    
    -- Referencias del provider
    provider_ref VARCHAR(200) NULL,
    auth_code VARCHAR(50) NULL,
    
    -- Errores
    error_code VARCHAR(50) NULL,
    error_message TEXT NULL,
    
    -- Locking para agente
    locked_by_agent VARCHAR(200) NULL,
    locked_at TIMESTAMP NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    
    -- Metadata adicional (JSON)
    metadata_json TEXT NULL
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_payment_intents_register ON payment_intents(register_id);
CREATE INDEX IF NOT EXISTS idx_payment_intents_session ON payment_intents(register_session_id);
CREATE INDEX IF NOT EXISTS idx_payment_intents_status ON payment_intents(status);
CREATE INDEX IF NOT EXISTS idx_payment_intents_cart_hash ON payment_intents(cart_hash);
CREATE INDEX IF NOT EXISTS idx_payment_intents_created_at ON payment_intents(created_at);
CREATE INDEX IF NOT EXISTS idx_payment_intents_register_status ON payment_intents(register_id, status);

-- Índice compuesto para búsqueda de intents pendientes por register
CREATE INDEX IF NOT EXISTS idx_payment_intents_pending ON payment_intents(register_id, status, created_at) 
WHERE status IN ('READY', 'IN_PROGRESS');

-- Comentarios
COMMENT ON TABLE payment_intents IS 'Intenciones de pago para procesamiento con agente local (GETNET Serial)';
COMMENT ON COLUMN payment_intents.cart_hash IS 'Hash del carrito para idempotencia (SHA256 del cart_json)';
COMMENT ON COLUMN payment_intents.status IS 'CREATED, READY, IN_PROGRESS, APPROVED, DECLINED, ERROR, CANCELLED';
COMMENT ON COLUMN payment_intents.locked_by_agent IS 'Identificador del agente que tomó el intent (para evitar duplicados)';
COMMENT ON COLUMN payment_intents.locked_at IS 'Timestamp cuando el agente tomó el intent';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    'payment_intents' as tabla,
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'payment_intents'
ORDER BY ordinal_position;

SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'payment_intents'
ORDER BY indexname;


