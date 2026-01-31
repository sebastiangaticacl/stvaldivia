-- ============================================================================
-- MIGRACIÓN: PaymentIntent - Sistema de intenciones de pago para GETNET
-- Fecha: 2025-01-15
-- Versión: MySQL
-- Descripción: Tabla para gestionar intenciones de pago con agente local
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- mysqldump -u usuario -p bimba_db > backup_antes_payment_intents_$(date +%Y%m%d_%H%M%S).sql

START TRANSACTION;

-- ============================================================================
-- TABLA: payment_intents
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_intents (
    id CHAR(36) PRIMARY KEY,
    
    -- Contexto de la transacción
    register_id VARCHAR(50) NOT NULL,
    register_session_id INT NULL,
    employee_id VARCHAR(50) NOT NULL,
    employee_name VARCHAR(200) NOT NULL,
    
    -- Monto y moneda
    amount_total DECIMAL(10, 2) NOT NULL,
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
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    
    -- Metadata adicional (JSON)
    metadata_json TEXT NULL,
    
    -- Comentarios (MySQL usa ALTER TABLE para comentarios de tabla)
    INDEX idx_payment_intents_register (register_id),
    INDEX idx_payment_intents_session (register_session_id),
    INDEX idx_payment_intents_status (status),
    INDEX idx_payment_intents_cart_hash (cart_hash),
    INDEX idx_payment_intents_created_at (created_at),
    INDEX idx_payment_intents_register_status (register_id, status),
    INDEX idx_payment_intents_pending (register_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Intenciones de pago para procesamiento con agente local (GETNET Serial)';

-- Comentarios de columnas (MySQL requiere ALTER TABLE)
ALTER TABLE payment_intents 
    MODIFY COLUMN cart_hash VARCHAR(64) NOT NULL COMMENT 'Hash del carrito para idempotencia (SHA256 del cart_json)',
    MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'CREATED' COMMENT 'CREATED, READY, IN_PROGRESS, APPROVED, DECLINED, ERROR, CANCELLED',
    MODIFY COLUMN locked_by_agent VARCHAR(200) NULL COMMENT 'Identificador del agente que tomó el intent (para evitar duplicados)',
    MODIFY COLUMN locked_at TIMESTAMP NULL COMMENT 'Timestamp cuando el agente tomó el intent';

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
WHERE table_schema = DATABASE()
  AND table_name = 'payment_intents'
ORDER BY ordinal_position;

SELECT 
    index_name, 
    column_name,
    seq_in_index
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'payment_intents'
ORDER BY index_name, seq_in_index;

