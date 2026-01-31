-- Migración MVP1: Agregar campos nuevos para sistema de cajas BIMBA
-- Fecha: 2025-01-15
-- Descripción: Agrega campos para configuración de cajas (PosRegister) y sesiones (RegisterSession)

-- ============================================
-- TABLA: pos_registers
-- ============================================

-- register_type: Tipo de caja (TOTEM, HUMANA, OFICINA, VIRTUAL)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS register_type VARCHAR(50) NULL;

CREATE INDEX IF NOT EXISTS idx_pos_registers_register_type ON pos_registers(register_type);

-- devices: JSON con dispositivos asociados (POS, impresora, gaveta)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS devices TEXT NULL;

-- operation_mode: JSON con modo de operación (venta normal, cortesía, precompra)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS operation_mode TEXT NULL;

-- payment_methods: JSON array con métodos de pago habilitados
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_methods TEXT NULL;

-- responsible_user_id: Usuario responsable de la caja
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS responsible_user_id VARCHAR(50) NULL;

CREATE INDEX IF NOT EXISTS idx_pos_registers_responsible_user ON pos_registers(responsible_user_id);

-- responsible_role: Rol del responsable
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS responsible_role VARCHAR(50) NULL;

-- operational_status: Estado operativo (active, maintenance, offline, error)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS operational_status VARCHAR(50) NOT NULL DEFAULT 'active';

CREATE INDEX IF NOT EXISTS idx_pos_registers_operational_status ON pos_registers(operational_status);

-- fallback_config: JSON con configuración de fallback
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fallback_config TEXT NULL;

-- fast_lane_config: JSON con configuración de fast lane
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fast_lane_config TEXT NULL;

-- ============================================
-- TABLA: register_sessions
-- ============================================

-- cash_count: JSON con conteo de efectivo por denominación
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS cash_count TEXT NULL;

-- payment_totals: JSON con snapshot de totales por método de pago
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_totals TEXT NULL;

-- ticket_count: Contador de tickets emitidos
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS ticket_count INTEGER NOT NULL DEFAULT 0;

-- cash_difference: Diferencia entre efectivo contado y esperado
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS cash_difference NUMERIC(10, 2) NULL;

-- incidents: JSON array con incidentes durante la sesión
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS incidents TEXT NULL;

-- close_notes: Notas del cierre
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS close_notes TEXT NULL;

-- ============================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- ============================================

COMMENT ON COLUMN pos_registers.register_type IS 'Tipo de caja: TOTEM, HUMANA, OFICINA, VIRTUAL';
COMMENT ON COLUMN pos_registers.devices IS 'JSON: {"pos": "modelo", "printer": "modelo", "drawer": true/false}';
COMMENT ON COLUMN pos_registers.operation_mode IS 'JSON: {"mode": "normal|courtesy|prepurchase"}';
COMMENT ON COLUMN pos_registers.payment_methods IS 'JSON array: ["cash", "debit", "credit", "qr"]';
COMMENT ON COLUMN pos_registers.operational_status IS 'Estado operativo: active, maintenance, offline, error';
COMMENT ON COLUMN register_sessions.cash_count IS 'JSON: {"1000": 10, "2000": 5, "5000": 2, "total": 25000}';
COMMENT ON COLUMN register_sessions.payment_totals IS 'JSON: {"cash": 100000, "debit": 50000, "credit": 30000}';
COMMENT ON COLUMN register_sessions.ticket_count IS 'Número de tickets emitidos en esta sesión';
COMMENT ON COLUMN register_sessions.cash_difference IS 'Diferencia: efectivo_contado - (initial_cash + ventas_efectivo)';

-- ============================================
-- VERIFICACIÓN
-- ============================================

-- Verificar que las columnas se agregaron correctamente
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name IN ('register_type', 'devices', 'operation_mode', 'payment_methods', 
                     'responsible_user_id', 'responsible_role', 'operational_status', 
                     'fallback_config', 'fast_lane_config')
ORDER BY column_name;

SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'register_sessions'
AND column_name IN ('cash_count', 'payment_totals', 'ticket_count', 'cash_difference', 
                     'incidents', 'close_notes')
ORDER BY column_name;


