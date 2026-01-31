-- Migración: Agregar columnas inventory_applied e inventory_applied_at a pos_sales
-- Fecha: 2024-12-17
-- Descripción: Flag para evitar doble descuento de inventario

-- Agregar columnas
ALTER TABLE pos_sales 
ADD COLUMN IF NOT EXISTS inventory_applied BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS inventory_applied_at TIMESTAMP NULL;

-- Crear índice para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_pos_sales_inventory_applied ON pos_sales(inventory_applied);

-- Comentarios
COMMENT ON COLUMN pos_sales.inventory_applied IS 'Flag para evitar doble descuento de inventario. True si el inventario ya fue aplicado para esta venta.';
COMMENT ON COLUMN pos_sales.inventory_applied_at IS 'Timestamp de cuándo se aplicó el inventario por primera vez.';




