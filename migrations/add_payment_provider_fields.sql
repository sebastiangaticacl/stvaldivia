-- Migración: Agregar campos de Payment Stack BIMBA (GETNET + KLAP)
-- Fecha: 2025-01-15
-- Descripción: Campos para estrategia de pagos GETNET principal + KLAP backup

-- ============================================
-- TABLA: pos_registers
-- ============================================

-- payment_provider_primary: Provider principal (default GETNET)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_provider_primary VARCHAR(50) NOT NULL DEFAULT 'GETNET';

-- payment_provider_backup: Provider backup (KLAP o null)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS payment_provider_backup VARCHAR(50) NULL;

-- provider_config: JSON con configuración por proveedor (terminal_id, merchant_id, etc)
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS provider_config TEXT NULL;

-- fallback_policy: JSON con reglas de cuándo usar backup
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS fallback_policy TEXT NULL;

-- ============================================
-- TABLA: register_sessions
-- ============================================

-- payment_provider_used_primary_count: Contador de transacciones con provider principal
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_provider_used_primary_count INTEGER NOT NULL DEFAULT 0;

-- payment_provider_used_backup_count: Contador de transacciones con provider backup
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS payment_provider_used_backup_count INTEGER NOT NULL DEFAULT 0;

-- fallback_events: JSON array con eventos de fallback
ALTER TABLE register_sessions 
ADD COLUMN IF NOT EXISTS fallback_events TEXT NULL;

-- ============================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- ============================================

COMMENT ON COLUMN pos_registers.payment_provider_primary IS 'Provider principal de pagos: GETNET (default), KLAP, SUMUP';
COMMENT ON COLUMN pos_registers.payment_provider_backup IS 'Provider backup: KLAP (recomendado), null si no hay backup';
COMMENT ON COLUMN pos_registers.provider_config IS 'JSON: {"GETNET": {"terminal_id": "...", "merchant_id": "..."}, "KLAP": {"merchant_id": "...", "api_key": "..."}}';
COMMENT ON COLUMN pos_registers.fallback_policy IS 'JSON: {"enabled": true, "trigger_events": ["pos_offline", "pos_error"], "max_switch_time_seconds": 60, "backup_devices_required": 2}';
COMMENT ON COLUMN register_sessions.payment_provider_used_primary_count IS 'Número de transacciones procesadas con provider principal';
COMMENT ON COLUMN register_sessions.payment_provider_used_backup_count IS 'Número de transacciones procesadas con provider backup';
COMMENT ON COLUMN register_sessions.fallback_events IS 'JSON array: [{"timestamp": "2025-01-15T22:30:00", "reason": "pos_offline", "from_provider": "GETNET", "to_provider": "KLAP", "handled_by_user_id": "user123"}]';

-- ============================================
-- VERIFICACIÓN
-- ============================================

SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name IN ('payment_provider_primary', 'payment_provider_backup', 'provider_config', 'fallback_policy')
ORDER BY column_name;

SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'register_sessions'
AND column_name IN ('payment_provider_used_primary_count', 'payment_provider_used_backup_count', 'fallback_events')
ORDER BY column_name;


