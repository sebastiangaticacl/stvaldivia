-- ============================================================================
-- MIGRACIÓN: PaymentAgent - Sistema de monitoreo de agentes de pago Getnet
-- Fecha: 2025-12-18
-- Descripción: Tabla para monitorear estado de agentes Windows que comunican con pinpad Getnet
-- Compatibilidad: PostgreSQL (idempotente, seguro para producción)
-- ============================================================================

-- IMPORTANTE: Hacer backup antes de ejecutar
-- pg_dump -U postgres -d bimba > backup_antes_payment_agents_$(date +%Y%m%d_%H%M%S).sql

BEGIN;

-- ============================================================================
-- TABLA: payment_agents
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificación del agente
    register_id VARCHAR(50) NOT NULL,
    agent_name VARCHAR(200) NOT NULL,
    
    -- Estado de conectividad
    last_heartbeat TIMESTAMP NOT NULL,
    last_ip VARCHAR(100) NULL,
    
    -- Estado del pinpad Getnet
    last_getnet_status VARCHAR(20) NULL,  -- 'OK', 'ERROR', 'UNKNOWN'
    last_getnet_message TEXT NULL,
    
    -- Healthcheck adicional
    last_healthcheck_at TIMESTAMP NULL,
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ÍNDICES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_payment_agents_register_id ON payment_agents(register_id);
CREATE INDEX IF NOT EXISTS idx_payment_agents_last_heartbeat ON payment_agents(last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_payment_agents_register_heartbeat ON payment_agents(register_id, last_heartbeat);
CREATE INDEX IF NOT EXISTS idx_payment_agents_register_agent ON payment_agents(register_id, agent_name);

-- ============================================================================
-- COMENTARIOS
-- ============================================================================

COMMENT ON TABLE payment_agents IS 'Estado de agentes de pago (Windows) que comunican con pinpad Getnet';
COMMENT ON COLUMN payment_agents.register_id IS 'ID de la caja/register (ej: "1", "TEST001")';
COMMENT ON COLUMN payment_agents.agent_name IS 'Nombre del agente/PC (ej: "POS-CAJA-TEST")';
COMMENT ON COLUMN payment_agents.last_heartbeat IS 'Último heartbeat recibido del agente';
COMMENT ON COLUMN payment_agents.last_getnet_status IS 'Estado del pinpad Getnet: OK, ERROR, UNKNOWN';
COMMENT ON COLUMN payment_agents.last_getnet_message IS 'Mensaje descriptivo del estado de Getnet';

COMMIT;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================

-- Verificar que la tabla se creó correctamente
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'payment_agents'
ORDER BY ordinal_position;














