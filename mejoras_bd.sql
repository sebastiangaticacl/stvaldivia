-- =====================================================
-- MEJORAS DE ARQUITECTURA DE BASE DE DATOS - BIMBA
-- Fecha: 2025-12-17
-- =====================================================

BEGIN;

-- =====================================================
-- 1. ELIMINAR ÍNDICES DUPLICADOS
-- =====================================================

-- alerta_fuga_turno: Eliminar índices duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_alerta_fuga_turno_atendida;
DROP INDEX IF EXISTS ix_alerta_fuga_turno_criticidad;
DROP INDEX IF EXISTS ix_alerta_fuga_turno_fecha_hora;
DROP INDEX IF EXISTS ix_alerta_fuga_turno_insumo_id;
DROP INDEX IF EXISTS ix_alerta_fuga_turno_turno_id;
DROP INDEX IF EXISTS ix_alerta_fuga_turno_ubicacion;

-- aperturas_cajas: Eliminar duplicados
DROP INDEX IF EXISTS ix_aperturas_cajas_id_caja;
DROP INDEX IF EXISTS ix_aperturas_cajas_jornada_id;

-- audit_logs: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_audit_logs_action;
DROP INDEX IF EXISTS ix_audit_logs_entity_id;
DROP INDEX IF EXISTS ix_audit_logs_timestamp;
DROP INDEX IF EXISTS ix_audit_logs_user_id;

-- bot_logs: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_bot_logs_canal;
DROP INDEX IF EXISTS ix_bot_logs_conversation_id;
DROP INDEX IF EXISTS ix_bot_logs_direction;
DROP INDEX IF EXISTS ix_bot_logs_status;
DROP INDEX IF EXISTS ix_bot_logs_timestamp;

-- cargo_salary_audit_logs: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_cargo_salary_audit_logs_cargo_nombre;
DROP INDEX IF EXISTS ix_cargo_salary_audit_logs_changed_by;
DROP INDEX IF EXISTS ix_cargo_salary_audit_logs_created_at;

-- cargo_salary_configs: Mantener solo uno (uq_)
DROP INDEX IF EXISTS ix_cargo_salary_configs_cargo;

-- cargos: Eliminar duplicados
DROP INDEX IF EXISTS ix_cargos_activo;

-- deliveries: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_deliveries_admin_user;
DROP INDEX IF EXISTS ix_deliveries_barra;
DROP INDEX IF EXISTS ix_deliveries_bartender;
DROP INDEX IF EXISTS ix_deliveries_sale_id;
DROP INDEX IF EXISTS ix_deliveries_timestamp;

-- delivery_items: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_delivery_items_bartender_id;
DROP INDEX IF EXISTS ix_delivery_items_delivered_at;
DROP INDEX IF EXISTS ix_delivery_items_delivery_id;
DROP INDEX IF EXISTS ix_delivery_items_delivery_type;
DROP INDEX IF EXISTS ix_delivery_items_location;
DROP INDEX IF EXISTS ix_delivery_items_product_id;
DROP INDEX IF EXISTS ix_delivery_items_product_name;
DROP INDEX IF EXISTS ix_delivery_items_sale_id;

-- delivery_logs: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_delivery_logs_action;
DROP INDEX IF EXISTS ix_delivery_logs_bartender_user_id;
DROP INDEX IF EXISTS ix_delivery_logs_created_at;
DROP INDEX IF EXISTS ix_delivery_logs_item_id;
DROP INDEX IF EXISTS ix_delivery_logs_scanner_device_id;
DROP INDEX IF EXISTS ix_delivery_logs_ticket_id;

-- employee_advances: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_employee_advances_aplicado;
DROP INDEX IF EXISTS ix_employee_advances_employee_id;
DROP INDEX IF EXISTS ix_employee_advances_fecha_abono;

-- employee_payments: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_employee_payments_employee_id;
DROP INDEX IF EXISTS ix_employee_payments_fecha_pago;
DROP INDEX IF EXISTS ix_employee_payments_tipo_pago;

-- employee_shifts: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_employee_shifts_employee_id;
DROP INDEX IF EXISTS ix_employee_shifts_fecha_turno;
DROP INDEX IF EXISTS ix_employee_shifts_hora_inicio;
DROP INDEX IF EXISTS ix_employee_shifts_jornada_id;
DROP INDEX IF EXISTS ix_employee_shifts_pagado;

-- employees: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_employees_cargo;
DROP INDEX IF EXISTS ix_employees_employee_id;
DROP INDEX IF EXISTS ix_employees_is_active;
DROP INDEX IF EXISTS ix_employees_is_bartender;
DROP INDEX IF EXISTS ix_employees_is_cashier;
DROP INDEX IF EXISTS ix_employees_last_synced_at;
DROP INDEX IF EXISTS ix_employees_person_id;
DROP INDEX IF EXISTS ix_employees_pin_hash;

-- ficha_review_logs: Eliminar duplicados (mantener idx_)
DROP INDEX IF EXISTS ix_ficha_review_logs_employee_id;
DROP INDEX IF EXISTS ix_ficha_review_logs_reviewed_at;

-- Continuar con más tablas si es necesario...

-- =====================================================
-- 2. MIGRAR CAMPOS JSON DE TEXT A JSONB
-- =====================================================

-- delivery_items.ingredients_consumed
ALTER TABLE delivery_items 
ALTER COLUMN ingredients_consumed TYPE JSONB 
USING ingredients_consumed::JSONB;

-- sale_delivery_status.items_detail
ALTER TABLE sale_delivery_status 
ALTER COLUMN items_detail TYPE JSONB 
USING items_detail::JSONB;

-- employees.custom_fields (si contiene JSON)
-- Nota: Verificar primero si contiene JSON válido antes de migrar
-- ALTER TABLE employees 
-- ALTER COLUMN custom_fields TYPE JSONB 
-- USING CASE 
--     WHEN custom_fields IS NULL OR custom_fields = '' THEN NULL
--     ELSE custom_fields::JSONB 
-- END;

-- =====================================================
-- 3. AGREGAR ÍNDICES PARA JSONB
-- =====================================================

-- Índice GIN para búsquedas en JSONB
CREATE INDEX IF NOT EXISTS idx_delivery_items_ingredients_consumed_gin 
ON delivery_items USING GIN (ingredients_consumed);

CREATE INDEX IF NOT EXISTS idx_sale_delivery_status_items_detail_gin 
ON sale_delivery_status USING GIN (items_detail);

-- =====================================================
-- 4. AGREGAR CLAVES FORÁNEAS FALTANTES
-- =====================================================

-- Nota: Primero debemos estandarizar tipos de datos
-- Por ahora, solo agregamos las que son compatibles

-- delivery_items.delivery_id ya tiene FK
-- delivery_logs.ticket_id ya tiene FK
-- delivery_logs.item_id ya tiene FK

-- =====================================================
-- 5. CREAR ÍNDICES COMPUESTOS ADICIONALES PARA RENDIMIENTO
-- =====================================================

-- Índices compuestos para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_pos_sales_jornada_created 
ON pos_sales (jornada_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_employee_shifts_employee_fecha_estado 
ON employee_shifts (employee_id, fecha_turno, estado);

CREATE INDEX IF NOT EXISTS idx_bartender_turnos_fecha_estado 
ON bartender_turnos (fecha_hora_apertura, estado);

CREATE INDEX IF NOT EXISTS idx_delivery_items_sale_delivered 
ON delivery_items (sale_id, delivered_at DESC);

-- =====================================================
-- 6. ANALIZAR TABLAS PARA OPTIMIZAR ESTADÍSTICAS
-- =====================================================

ANALYZE pos_sales;
ANALYZE employee_shifts;
ANALYZE bartender_turnos;
ANALYZE delivery_items;
ANALYZE ingredients;
ANALYZE employees;

COMMIT;

-- =====================================================
-- VERIFICACIONES POST-MIGRACIÓN
-- =====================================================

-- Verificar índices restantes
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
    AND indexname LIKE 'ix_%'
ORDER BY tablename, indexname;

-- Verificar tipos JSONB
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
    AND data_type = 'jsonb'
ORDER BY table_name, column_name;




