# Evaluación de Arquitectura de Base de Datos - BIMBA

## Resumen Ejecutivo

**Base de Datos:** PostgreSQL 14.20  
**Total de Tablas:** 67 tablas  
**Total de Índices:** 449 índices  
**Claves Foráneas:** 45 relaciones  
**Funciones:** 2 funciones almacenadas

---

## 1. Estructura General

### 1.1 Módulos Principales

La base de datos está organizada en los siguientes módulos funcionales:

#### **Gestión de Empleados**
- `employees` - Información de empleados
- `employee_shifts` - Turnos de empleados
- `employee_payments` - Pagos a empleados
- `employee_advances` - Adelantos
- `employee_salary_configs` - Configuraciones salariales
- `cargos` - Cargos/posiciones
- `cargo_salary_configs` - Configuraciones salariales por cargo
- `planilla_trabajadores` - Planilla de trabajadores

#### **Gestión de Ventas (POS)**
- `pos_sales` - Ventas principales
- `pos_sale_items` - Items de venta
- `pos_sales_backup` - Backup de ventas
- `pos_sale_items_backup` - Backup de items
- `pos_registers` - Registros de caja
- `pos_sessions` - Sesiones de caja
- `register_sessions` - Sesiones de registro
- `register_closes` - Cierres de caja
- `register_locks` - Bloqueos de caja

#### **Gestión de Inventario**
- `ingredients` - Ingredientes/insumos
- `ingredient_categories` - Categorías de ingredientes
- `ingredient_stocks` - Stock de ingredientes
- `inventory_items` - Items de inventario
- `inventory_movements` - Movimientos de inventario
- `turno_stock_inicial` - Stock inicial de turno
- `turno_stock_final` - Stock final de turno
- `turno_desviacion_inventario` - Desviaciones de inventario
- `merma_inventario` - Mermas de inventario

#### **Gestión de Productos y Recetas**
- `products` - Productos
- `recipes` - Recetas
- `recipe_ingredients` - Ingredientes de recetas
- `recipe_ingredients_legacy` - Ingredientes legacy
- `product_recipes` - Recetas de productos

#### **Gestión de Turnos de Barra**
- `bartender_turnos` - Turnos de bartender
- `alerta_fuga_turno` - Alertas de fuga
- `deliveries` - Entregas
- `delivery_items` - Items de entrega
- `delivery_logs` - Logs de entrega

#### **Gestión de Jornadas**
- `jornadas` - Jornadas de trabajo
- `shifts` - Turnos
- `aperturas_cajas` - Aperturas de cajas

#### **Sistema de Tickets**
- `ticket_entregas` - Tickets de entrega
- `ticket_entrega_items` - Items de tickets
- `ticket_scans` - Escaneos de tickets
- `sale_delivery_status` - Estado de entregas

#### **Guardarropía**
- `guardarropia_items` - Items de guardarropía
- `guardarropia_tickets` - Tickets de guardarropía
- `guardarropia_ticket_logs` - Logs de guardarropía

#### **Auditoría y Logs**
- `audit_logs` - Logs de auditoría
- `sale_audit_logs` - Logs de auditoría de ventas
- `superadmin_sale_audit` - Auditoría de superadmin
- `cargo_salary_audit_logs` - Logs de auditoría salarial
- `ficha_review_logs` - Logs de revisión de fichas
- `fraud_attempts` - Intentos de fraude
- `api_connection_logs` - Logs de conexión API
- `bot_logs` - Logs de bot

#### **Programación**
- `programacion_eventos` - Eventos programados
- `programacion_asignaciones` - Asignaciones programadas

#### **Encuestas**
- `survey_sessions` - Sesiones de encuestas
- `survey_responses` - Respuestas de encuestas

#### **Pagos**
- `pagos` - Pagos
- `pagos_items` - Items de pagos

#### **Notificaciones**
- `notifications` - Notificaciones

#### **Snapshots**
- `snapshot_cajas` - Snapshots de cajas
- `snapshot_empleados` - Snapshots de empleados

#### **Métricas y Estadísticas**
- `daily_metrics` - Métricas diarias
- `hourly_metrics` - Métricas horarias
- `employee_statistics` - Estadísticas de empleados
- `statistics_cache` - Cache de estadísticas

---

## 2. Análisis de Normalización

### 2.1 Fortalezas

✅ **Buen nivel de normalización:**
- Separación clara entre entidades (empleados, productos, ventas, inventario)
- Uso adecuado de claves foráneas (45 relaciones)
- Tablas de configuración separadas (cargo_salary_configs, employee_salary_configs)

✅ **Integridad referencial:**
- Todas las tablas tienen claves primarias
- Relaciones bien definidas con claves foráneas

### 2.2 Áreas de Mejora

⚠️ **Duplicación de datos:**
- `pos_sales_backup` y `pos_sale_items_backup` - Tablas de backup que duplican información
- `snapshot_cajas` y `snapshot_empleados` - Almacenan datos completos en JSON/texto

⚠️ **Campos redundantes:**
- `employee_shifts` tiene `employee_name` además de `employee_id`
- `delivery_items` tiene `bartender_name` además de `bartender_id`
- Varias tablas almacenan nombres además de IDs

⚠️ **Uso de TEXT para JSON:**
- `delivery_items.ingredients_consumed` (JSON)
- `sale_delivery_status.items_detail` (JSON)
- `employees.custom_fields` (TEXT)
- Considerar usar tipo JSONB nativo de PostgreSQL

---

## 3. Análisis de Índices

### 3.1 Estado Actual

**Total:** 449 índices en 67 tablas

### 3.2 Fortalezas

✅ **Índices bien distribuidos:**
- Índices en claves foráneas
- Índices compuestos para consultas frecuentes
- Índices en campos de búsqueda (fechas, estados, IDs)

✅ **Índices únicos apropiados:**
- `ix_products_name` - Nombre único de productos
- `ix_cargos_nombre` - Nombre único de cargos
- `ix_ticket_entregas_qr_token` - Token único
- `ix_ticket_entregas_sale_id` - Sale ID único

### 3.3 Áreas de Mejora

⚠️ **Índices duplicados:**
- `alerta_fuga_turno`: Tiene tanto `idx_alerta_fuga_turno_atendida` como `ix_alerta_fuga_turno_atendida`
- `bot_logs`: Múltiples índices similares (idx_ e ix_)
- `audit_logs`: Índices duplicados con diferentes prefijos

⚠️ **Índices faltantes potenciales:**
- Consultas por rangos de fechas podrían beneficiarse de índices compuestos
- Campos de búsqueda frecuente sin índices

---

## 4. Análisis de Relaciones

### 4.1 Relaciones Principales

**Jornadas (jornadas) - Tabla Central:**
- Relacionada con: `aperturas_cajas`, `employee_shifts`, `pos_sales`, `register_sessions`, `ticket_entregas`, `snapshot_cajas`, `snapshot_empleados`, `planilla_trabajadores`, `guardarropia_tickets`

**Bartender Turnos (bartender_turnos) - Tabla Central:**
- Relacionada con: `alerta_fuga_turno`, `inventory_movements`, `merma_inventario`, `turno_stock_inicial`, `turno_stock_final`, `turno_desviacion_inventario`

**Productos (products) - Tabla Central:**
- Relacionada con: `recipes`, `product_recipes`

**Ingredientes (ingredients) - Tabla Central:**
- Relacionada con: `ingredient_stocks`, `recipe_ingredients`, `alerta_fuga_turno`, `inventory_movements`, `merma_inventario`, `turno_stock_inicial`, `turno_stock_final`, `turno_desviacion_inventario`

**Ventas (pos_sales) - Tabla Central:**
- Relacionada con: `pos_sale_items`, `sale_audit_logs`, `superadmin_sale_audit`, `ticket_entregas`

### 4.2 Fortalezas

✅ **Relaciones bien definidas:**
- 45 claves foráneas establecidas
- Integridad referencial mantenida

### 4.3 Áreas de Mejora

⚠️ **Relaciones faltantes:**
- `deliveries.sale_id` no tiene clave foránea (es VARCHAR, no INTEGER)
- `fraud_attempts.sale_id` no tiene clave foránea
- `ticket_scans.sale_id` no tiene clave foránea

⚠️ **Tipos inconsistentes:**
- `sale_id` aparece como VARCHAR en algunas tablas y INTEGER en otras
- `employee_id` aparece como VARCHAR en todas las tablas (considerar normalización)

---

## 5. Análisis de Tipos de Datos

### 5.1 Fortalezas

✅ **Uso apropiado de tipos:**
- `timestamp without time zone` para fechas/horas
- `numeric` para valores monetarios
- `boolean` para flags
- `integer` para IDs secuenciales

### 5.2 Áreas de Mejora

⚠️ **Uso de VARCHAR para IDs:**
- `employees.id` es VARCHAR(50) en lugar de INTEGER/UUID
- `sale_id` mezcla VARCHAR e INTEGER
- Considerar estandarizar a UUID o INTEGER

⚠️ **Campos de fecha como VARCHAR:**
- `shifts.shift_date` es VARCHAR(10) en lugar de DATE
- `employee_shifts.fecha_turno` es VARCHAR(50) en lugar de DATE
- Considerar migrar a tipos DATE nativos

⚠️ **Uso de TEXT para JSON:**
- Considerar migrar a JSONB para mejor rendimiento y consultas

---

## 6. Funciones Almacenadas

### 6.1 Funciones Existentes

1. **`clean_expired_cache`** - Limpia cache expirado
2. **`update_daily_metrics`** - Actualiza métricas diarias

### 6.2 Recomendaciones

✅ Las funciones están bien definidas para mantenimiento automático

---

## 7. Recomendaciones Prioritarias

### 🔴 Alta Prioridad

1. **Estandarizar tipos de IDs:**
   - Migrar `sale_id` a un tipo consistente (INTEGER o UUID)
   - Considerar UUID para `employee_id` si se requiere integración externa

2. **Eliminar índices duplicados:**
   - Revisar y eliminar índices duplicados (idx_ vs ix_)
   - Consolidar índices similares

3. **Migrar campos de fecha:**
   - Convertir `shift_date` y `fecha_turno` de VARCHAR a DATE
   - Beneficios: validación automática, mejor rendimiento, consultas más eficientes

### 🟡 Media Prioridad

4. **Migrar JSON a JSONB:**
   - Convertir campos TEXT con JSON a JSONB
   - Beneficios: validación, índices, consultas más eficientes

5. **Agregar claves foráneas faltantes:**
   - Agregar FK para `deliveries.sale_id`, `fraud_attempts.sale_id`, etc.
   - Estandarizar tipos primero

6. **Optimizar tablas de backup:**
   - Considerar particionamiento o archivo para `pos_sales_backup`
   - Evaluar si realmente se necesitan ambas tablas

### 🟢 Baja Prioridad

7. **Normalizar campos redundantes:**
   - Evaluar si `employee_name` en `employee_shifts` es necesario
   - Considerar vistas materializadas para datos denormalizados

8. **Documentar relaciones complejas:**
   - Crear diagrama ER actualizado
   - Documentar flujos de datos principales

---

## 8. Métricas de Calidad

| Métrica | Valor | Evaluación |
|---------|-------|------------|
| Total de Tablas | 67 | ✅ Adecuado |
| Total de Índices | 449 | ⚠️ Alto (revisar duplicados) |
| Claves Foráneas | 45 | ✅ Bueno |
| Índices por Tabla (promedio) | 6.7 | ⚠️ Alto |
| Tablas sin FK | ~10 | ⚠️ Revisar |
| Uso de JSONB | 0 | ⚠️ Mejorar |
| Triggers | 0 | ✅ Adecuado |

---

## 9. Conclusión

La arquitectura de la base de datos es **sólida y bien estructurada** con una separación clara de responsabilidades y buenas prácticas de normalización. Las principales áreas de mejora son:

1. **Consistencia de tipos de datos** (especialmente IDs y fechas)
2. **Optimización de índices** (eliminar duplicados)
3. **Modernización** (migrar a JSONB, estandarizar tipos)

La base de datos está preparada para producción, pero estas mejoras incrementales aumentarían el rendimiento y la mantenibilidad a largo plazo.

---

**Fecha de Evaluación:** 2025-12-17  
**Evaluado por:** Sistema de Análisis Automático




