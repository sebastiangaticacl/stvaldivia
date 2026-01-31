-- ============================================================================
-- MIGRACIÓN: PaymentAgent - Sistema de monitoreo de agentes de pago Getnet
-- Fecha: 2025-12-18
-- Versión: MySQL
-- Descripción: Tabla para monitorear estado de agentes Windows que comunican con pinpad Getnet
-- Compatibilidad: MySQL 8.0+ (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- mysqldump -u usuario -p bimba_db > backup_antes_payment_agents_$(date +%Y%m%d_%H%M%S).sql

START TRANSACTION;

-- ============================================================================
-- TABLA: payment_agents
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_agents (
    id CHAR(36) PRIMARY KEY,
    
    -- Identificación del agente
    register_id VARCHAR(50) NOT NULL,
    agent_name VARCHAR(200) NOT NULL,
    
    -- Estado de conectividad
    last_heartbeat TIMESTAMP NOT NULL,
    last_ip VARCHAR(100) NULL,
    
    -- Estado del pinpad Getnet
    last_getnet_status VARCHAR(20) NULL COMMENT 'OK, ERROR, UNKNOWN',
    last_getnet_message TEXT NULL,
    
    -- Healthcheck adicional
    last_healthcheck_at TIMESTAMP NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_payment_agents_register_id (register_id),
    INDEX idx_payment_agents_last_heartbeat (last_heartbeat),
    INDEX idx_payment_agents_register_heartbeat (register_id, last_heartbeat),
    INDEX idx_payment_agents_register_agent (register_id, agent_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Estado de agentes de pago (Windows) que comunican con pinpad Getnet';

-- Comentarios de columnas
ALTER TABLE payment_agents 
    MODIFY COLUMN register_id VARCHAR(50) NOT NULL COMMENT 'ID de la caja/register (ej: "1", "TEST001")',
    MODIFY COLUMN agent_name VARCHAR(200) NOT NULL COMMENT 'Nombre del agente/PC (ej: "POS-CAJA-TEST")',
    MODIFY COLUMN last_heartbeat TIMESTAMP NOT NULL COMMENT 'Último heartbeat recibido del agente',
    MODIFY COLUMN last_getnet_status VARCHAR(20) NULL COMMENT 'Estado del pinpad Getnet: OK, ERROR, UNKNOWN',
    MODIFY COLUMN last_getnet_message TEXT NULL COMMENT 'Mensaje descriptivo del estado de Getnet';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'payment_agents'
ORDER BY ordinal_position;

