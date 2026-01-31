-- Script de optimización de base de datos para BIMBA
-- Índices para mejorar rendimiento de consultas

-- Índices para tablas de ventas (consultas frecuentes)
CREATE INDEX IF NOT EXISTS idx_pos_sales_register_id ON pos_sales(register_id);
CREATE INDEX IF NOT EXISTS idx_pos_sales_created_at ON pos_sales(created_at);
CREATE INDEX IF NOT EXISTS idx_pos_sales_employee_id ON pos_sales(employee_id);
CREATE INDEX IF NOT EXISTS idx_pos_sales_status ON pos_sales(status);

-- Índices para items de venta
CREATE INDEX IF NOT EXISTS idx_pos_sale_items_sale_id ON pos_sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_pos_sale_items_item_id ON pos_sale_items(item_id);

-- Índices para empleados (búsquedas frecuentes)
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(active) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_employees_cargo_id ON employees(cargo_id);

-- Índices para jornadas y planillas
CREATE INDEX IF NOT EXISTS idx_jornadas_fecha ON jornadas(fecha);
CREATE INDEX IF NOT EXISTS idx_planilla_trabajador_jornada_id ON planilla_trabajadores(jornada_id);
CREATE INDEX IF NOT EXISTS idx_planilla_trabajador_employee_id ON planilla_trabajadores(employee_id);

-- Índices para turnos
CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(date);
CREATE INDEX IF NOT EXISTS idx_shifts_is_open ON shifts(is_open) WHERE is_open = true;
CREATE INDEX IF NOT EXISTS idx_employee_shifts_employee_id ON employee_shifts(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_shifts_shift_id ON employee_shifts(shift_id);
CREATE INDEX IF NOT EXISTS idx_employee_shifts_date ON employee_shifts(date);

-- Índices para entregas (deliveries)
CREATE INDEX IF NOT EXISTS idx_deliveries_sale_id ON deliveries(sale_id);
CREATE INDEX IF NOT EXISTS idx_deliveries_created_at ON deliveries(created_at);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON deliveries(status);
CREATE INDEX IF NOT EXISTS idx_ticket_scans_ticket_id ON ticket_scans(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_scans_created_at ON ticket_scans(created_at);

-- Índices para auditoría y logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_api_connection_logs_created_at ON api_connection_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_api_connection_logs_status ON api_connection_logs(status);

-- Índices para inventario
CREATE INDEX IF NOT EXISTS idx_inventory_items_name ON inventory_items(name);
CREATE INDEX IF NOT EXISTS idx_inventory_items_category ON inventory_items(category);
CREATE INDEX IF NOT EXISTS idx_inventory_stock_ingredient_id ON ingredient_stock(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_ingredient_id ON inventory_movements(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_created_at ON inventory_movements(created_at);

-- Índices para pagos de empleados
CREATE INDEX IF NOT EXISTS idx_employee_payments_employee_id ON employee_payments(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_payments_date ON employee_payments(date);
CREATE INDEX IF NOT EXISTS idx_employee_advances_employee_id ON employee_advances(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_advances_date ON employee_advances(date);

-- Índices para sesiones de caja
CREATE INDEX IF NOT EXISTS idx_register_sessions_register_id ON register_sessions(register_id);
CREATE INDEX IF NOT EXISTS idx_register_sessions_created_at ON register_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_register_closes_register_id ON register_closes(register_id);
CREATE INDEX IF NOT EXISTS idx_register_closes_created_at ON register_closes(created_at);

-- Índices compuestos para consultas comunes
CREATE INDEX IF NOT EXISTS idx_pos_sales_date_status ON pos_sales(created_at, status);
CREATE INDEX IF NOT EXISTS idx_deliveries_date_status ON deliveries(created_at, status);
CREATE INDEX IF NOT EXISTS idx_employee_shifts_employee_date ON employee_shifts(employee_id, date);

-- Optimización de PostgreSQL
ALTER DATABASE bimba SET work_mem = '64MB';
ALTER DATABASE bimba SET maintenance_work_mem = '256MB';
ALTER DATABASE bimba SET effective_cache_size = '2GB';
ALTER DATABASE bimba SET random_page_cost = 1.1;

-- Actualizar estadísticas
ANALYZE;

-- Mensaje de confirmación
SELECT '✅ Base de datos optimizada con índices y configuración de rendimiento' AS status;
