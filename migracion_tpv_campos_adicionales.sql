-- Migración: Agregar campos adicionales a pos_registers para mejor gestión de TPV
-- Fecha: 2025-12-17

-- Agregar nuevos campos
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS location VARCHAR(200),
ADD COLUMN IF NOT EXISTS tpv_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS default_location VARCHAR(100),
ADD COLUMN IF NOT EXISTS printer_config TEXT,
ADD COLUMN IF NOT EXISTS max_concurrent_sessions INTEGER DEFAULT 1 NOT NULL,
ADD COLUMN IF NOT EXISTS requires_cash_count BOOLEAN DEFAULT TRUE NOT NULL,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Crear índices para mejorar consultas
CREATE INDEX IF NOT EXISTS idx_pos_registers_type ON pos_registers(tpv_type, is_active);
CREATE INDEX IF NOT EXISTS idx_pos_registers_location ON pos_registers(location);

-- Actualizar updated_at con created_at para registros existentes
UPDATE pos_registers SET updated_at = created_at WHERE updated_at IS NULL;

-- Comentarios
COMMENT ON COLUMN pos_registers.location IS 'Ubicación física del TPV: "Barra Principal", "Terraza", etc.';
COMMENT ON COLUMN pos_registers.tpv_type IS 'Tipo de TPV: barra, puerta, terraza, kiosko, movil, vip';
COMMENT ON COLUMN pos_registers.default_location IS 'Ubicación por defecto para descontar inventario';
COMMENT ON COLUMN pos_registers.printer_config IS 'Configuración de impresora en formato JSON';
COMMENT ON COLUMN pos_registers.max_concurrent_sessions IS 'Número máximo de sesiones simultáneas permitidas';
COMMENT ON COLUMN pos_registers.requires_cash_count IS 'Si requiere conteo de efectivo al abrir sesión';

