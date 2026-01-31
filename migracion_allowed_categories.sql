-- Migración: Agregar campo allowed_categories a pos_registers
-- Este campo almacena un JSON array con las categorías de productos permitidas para cada caja
-- NULL = todas las categorías permitidas

ALTER TABLE pos_registers
ADD COLUMN allowed_categories TEXT NULL;

COMMENT ON COLUMN pos_registers.allowed_categories IS 'JSON array de categorías de productos permitidas. NULL = todas las categorías permitidas.';


