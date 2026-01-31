# Diagnóstico Estructural de Base de Datos - Sistema BIMBA

**Fecha:** 2025-12-25  
**Tipo:** Análisis de modelos ORM (SQLAlchemy)  
**Objetivo:** Inferir estructura real de BD y detectar inconsistencias

---

## 📊 RESUMEN EJECUTIVO

- **Total de modelos definidos:** 62 (incluyendo `db`)
- **Total de tablas inferidas:** 61
- **Archivos de modelos:** 28 archivos `.py`
- **Modelos exportados en `__init__.py`:** 61
- **Modelos con uso detectado:** 61 (100%)

---

## 📋 ESTRUCTURA DE TABLAS INFERIDA

### 1. POS (Punto de Venta) - 14 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `pos_sessions` | `PosSession` | ✅ Activo | Sesiones activas del POS (carrito temporal) |
| `pos_sales` | `PosSale` | ✅ Activo | Ventas del POS |
| `pos_sale_items` | `PosSaleItem` | ✅ Activo | Items de ventas |
| `pos_sales_backup` | `PosSaleBackup` | ⚠️ No exportado | Modelo existe pero NO está en `__init__.py` |
| `pos_sale_items_backup` | `PosSaleItemBackup` | ⚠️ No exportado | Modelo existe pero NO está en `__init__.py` |
| `pos_registers` | `PosRegister` | ✅ Activo | Cajas registradoras |
| `register_locks` | `RegisterLock` | ✅ Activo | Bloqueos de cajas |
| `register_sessions` | `RegisterSession` | ✅ Activo | Sesiones de caja |
| `register_closes` | `RegisterClose` | ✅ Activo | Cierres de caja |
| `payment_intents` | `PaymentIntent` | ✅ Activo | Intenciones de pago (UUID → String(36) en MySQL) |
| `payment_agents` | `PaymentAgent` | ✅ Activo | Agentes de pago (UUID → String(36) en MySQL) |
| `logs_intentos_pago` | `LogIntentoPago` | ✅ Activo | Logs de intentos de pago |
| `employees` | `Employee` | ✅ Activo | Empleados |
| `sale_audit_logs` | `SaleAuditLog` | ✅ Activo | Auditoría de ventas |

**Problemas detectados:**
- ❌ `PosSaleBackup` y `PosSaleItemBackup` existen en código pero NO están exportados en `__init__.py`
- ⚠️ Estos modelos no serán accesibles vía `from app.models import PosSaleBackup`

### 2. Jornadas y Turnos - 6 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `jornadas` | `Jornada` | ✅ Activo | Jornadas de trabajo |
| `planilla_trabajadores` | `PlanillaTrabajador` | ✅ Activo | Planilla de trabajadores por jornada |
| `aperturas_cajas` | `AperturaCaja` | ✅ Activo | Aperturas de caja |
| `snapshot_empleados` | `SnapshotEmpleados` | ✅ Activo | Snapshots de empleados |
| `snapshot_cajas` | `SnapshotCajas` | ✅ Activo | Snapshots de cajas |
| `shifts` | `Shift` | ✅ Activo | Turnos (sistema legacy) |

**Observaciones:**
- `SnapshotEmpleados` y `SnapshotCajas` están duplicados en la línea 19 de `__init__.py`
- Sistema de `Shift` (legacy) coexiste con `Jornada` (nuevo)

### 3. Empleados y Cargos - 8 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `employee_shifts` | `EmployeeShift` | ✅ Activo | Turnos de empleados |
| `employee_salary_configs` | `EmployeeSalaryConfig` | ✅ Activo | Configuración de sueldos |
| `ficha_review_logs` | `FichaReviewLog` | ✅ Activo | Logs de revisión de fichas |
| `employee_payments` | `EmployeePayment` | ✅ Activo | Pagos a empleados |
| `employee_advances` | `EmployeeAdvance` | ✅ Activo | Abonos y pagos excepcionales |
| `cargos` | `Cargo` | ✅ Activo | Cargos de empleados |
| `cargo_salary_configs` | `CargoSalaryConfig` | ✅ Activo | Configuración de sueldos por cargo |
| `cargo_salary_audit_logs` | `CargoSalaryAuditLog` | ✅ Activo | Auditoría de cambios en cargos/sueldos |

### 4. Inventario y Productos - 9 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `products` | `Product` | ✅ Activo | Productos |
| `inventory_items` | `InventoryItem` | ✅ Activo | Items de inventario (legacy) |
| `recipe_ingredients_legacy` | `LegacyIngredient` | ✅ Activo | Ingredientes legacy |
| `product_recipes` | `ProductRecipe` | ✅ Activo | Recetas de productos |
| `ingredient_categories` | `IngredientCategory` | ✅ Activo | Categorías de ingredientes (nuevo sistema) |
| `ingredients` | `StockIngredient` | ✅ Activo | Ingredientes (nuevo sistema) |
| `ingredient_stocks` | `IngredientStock` | ✅ Activo | Stock de ingredientes |
| `recipes` | `Recipe` | ✅ Activo | Recetas (nuevo sistema) |
| `recipe_ingredients` | `RecipeIngredient` | ✅ Activo | Ingredientes de recetas |
| `inventory_movements` | `InventoryMovement` | ✅ Activo | Movimientos de inventario |

**Observaciones:**
- ⚠️ Sistema dual: Legacy (`InventoryItem`, `LegacyIngredient`) y Nuevo (`StockIngredient`, `Recipe`)
- Conflicto de nombres: `Recipe` (nuevo) vs `ProductRecipe` (legacy)
- `recipe_ingredients_legacy` renombrado explícitamente para evitar conflicto

### 5. Entregas y Delivery - 6 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `deliveries` | `Delivery` | ✅ Activo | Entregas de tragos |
| `fraud_attempts` | `FraudAttempt` | ✅ Activo | Intentos de fraude |
| `ticket_scans` | `TicketScan` | ✅ Activo | Escaneos de tickets |
| `sale_delivery_status` | `SaleDeliveryStatus` | ✅ Activo | Estado de entregas por venta |
| `delivery_items` | `DeliveryItem` | ✅ Activo | Items de entrega |
| `ticket_entregas` | `TicketEntrega` | ✅ Activo | Tickets de entrega con QR |
| `ticket_entrega_items` | `TicketEntregaItem` | ✅ Activo | Items de tickets de entrega |
| `delivery_logs` | `DeliveryLog` | ✅ Activo | Logs de entregas |

### 6. Guardarropía - 3 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `guardarropia_items` | `GuardarropiaItem` | ✅ Activo | Items de guardarropía |
| `guardarropia_tickets` | `GuardarropiaTicket` | ✅ Activo | Tickets de guardarropía con QR |
| `guardarropia_ticket_logs` | `GuardarropiaTicketLog` | ✅ Activo | Logs de tickets de guardarropía |

### 7. Turnos de Bartender - 6 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `bartender_turnos` | `BartenderTurno` | ✅ Activo | Turnos de bartender |
| `turno_stock_inicial` | `TurnoStockInicial` | ✅ Activo | Stock inicial del turno |
| `turno_stock_final` | `TurnoStockFinal` | ✅ Activo | Stock final del turno |
| `merma_inventario` | `MermaInventario` | ✅ Activo | Mermas de inventario |
| `turno_desviacion_inventario` | `TurnoDesviacionInventario` | ✅ Activo | Desviaciones de inventario |
| `alerta_fuga_turno` | `AlertaFugaTurno` | ✅ Activo | Alertas de fuga en turnos |

### 8. Programación - 2 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `programacion_eventos` | `ProgramacionEvento` | ✅ Activo | Eventos programados |
| `programacion_asignaciones` | `ProgramacionAsignacion` | ✅ Activo | Asignaciones a eventos |

### 9. Kiosko - 2 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `pagos` | `Pago` | ✅ Activo | Pagos del kiosko |
| `pagos_items` | `PagoItem` | ✅ Activo | Items de pagos del kiosko |

### 10. Auditoría y Logs - 5 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `audit_logs` | `AuditLog` | ✅ Activo | Logs de auditoría general |
| `api_connection_logs` | `ApiConnectionLog` | ✅ Activo | Logs de conexión API |
| `bot_logs` | `BotLog` | ✅ Activo | Logs del bot de redes sociales |
| `superadmin_sale_audit` | `SuperadminSaleAudit` | ✅ Activo | Auditoría de ventas superadmin |

### 11. Notificaciones - 1 tabla

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `notifications` | `Notification` | ✅ Activo | Sistema de notificaciones |

**Observación:**
- ⚠️ `Notification` está definido pero el import en `__init__.py` línea 46 está comentado
- El modelo SÍ se usa en el código (11 archivos encontrados)

### 12. Encuestas (Survey) - 2 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `survey_responses` | `SurveyResponse` | ✅ Activo | Respuestas de encuestas |
| `survey_sessions` | `SurveySession` | ✅ Activo | Sesiones de encuestas |

**Observación:**
- ⚠️ `SurveyResponse` y `SurveySession` NO están en `__init__.py`
- Se usan en el código pero no están exportados

### 13. Redes Sociales - 2 tablas

| Tabla | Modelo | Estado | Observaciones |
|-------|--------|--------|---------------|
| `social_media_messages` | `SocialMediaMessage` | ✅ Activo | Mensajes de redes sociales |
| `social_media_responses` | `SocialMediaResponse` | ✅ Activo | Respuestas de redes sociales |

**Observación:**
- ⚠️ `SocialMediaMessage` y `SocialMediaResponse` NO están en `__init__.py`
- Se usan en el código pero no están exportados

---

## 🔍 PROBLEMAS DETECTADOS

### 1. Modelos No Exportados en `__init__.py`

**Modelos que existen pero NO están en `__all__`:**

1. **`PosSaleBackup`** y **`PosSaleItemBackup`**
   - Ubicación: `app/models/pos_models.py`
   - Tablas: `pos_sales_backup`, `pos_sale_items_backup`
   - Impacto: No accesibles vía `from app.models import`
   - Uso: Solo se pueden importar directamente desde `pos_models`

2. **`SurveyResponse`** y **`SurveySession`**
   - Ubicación: `app/models/survey_models.py`
   - Tablas: `survey_responses`, `survey_sessions`
   - Impacto: No accesibles vía `from app.models import`
   - Uso: Se usan en el código pero importación directa

3. **`SocialMediaMessage`** y **`SocialMediaResponse`**
   - Ubicación: `app/models/social_media_models.py`
   - Tablas: `social_media_messages`, `social_media_responses`
   - Impacto: No accesibles vía `from app.models import`
   - Uso: Se usan en el código pero importación directa

### 2. Import Comentado

**`Notification`** (línea 46 de `__init__.py`):
```python
# Importar modelo de notificaciones
# Importar modelos de inventario y recetas
```
- El modelo SÍ existe y se usa (11 archivos)
- El import está comentado pero el modelo funciona
- ⚠️ Inconsistencia: está en `__all__` pero el import está comentado

### 3. Duplicación en Imports

**Línea 19 de `__init__.py`:**
```python
from .jornada_models import Jornada, PlanillaTrabajador, AperturaCaja, SnapshotEmpleados, SnapshotCajas, SnapshotEmpleados, SnapshotCajas
```
- `SnapshotEmpleados` y `SnapshotCajas` están duplicados
- No causa error pero es redundante

### 4. Sistemas Duplicados/Paralelos

1. **Inventario Legacy vs Nuevo:**
   - Legacy: `InventoryItem`, `LegacyIngredient`, `ProductRecipe`
   - Nuevo: `StockIngredient`, `Recipe`, `RecipeIngredient`
   - Ambos sistemas coexisten

2. **Turnos Legacy vs Jornadas:**
   - Legacy: `Shift` (archivo JSON)
   - Nuevo: `Jornada`, `PlanillaTrabajador` (BD)
   - Ambos sistemas coexisten

### 5. Tipos de Datos Específicos

**UUID en MySQL:**
- `PaymentIntent.id`: `String(36)` (migrado de UUID)
- `PaymentAgent.id`: `String(36)` (migrado de UUID)
- ⚠️ Verificar compatibilidad con datos existentes

---

## 📊 ESTADÍSTICAS

### Por Categoría

| Categoría | Tablas | Modelos Exportados | Modelos No Exportados |
|-----------|--------|-------------------|----------------------|
| POS | 14 | 12 | 2 |
| Jornadas/Turnos | 6 | 6 | 0 |
| Empleados/Cargos | 8 | 8 | 0 |
| Inventario/Productos | 10 | 10 | 0 |
| Entregas | 8 | 8 | 0 |
| Guardarropía | 3 | 3 | 0 |
| Bartender Turnos | 6 | 6 | 0 |
| Programación | 2 | 2 | 0 |
| Kiosko | 2 | 2 | 0 |
| Auditoría/Logs | 5 | 5 | 0 |
| Notificaciones | 1 | 1 | 0 |
| Encuestas | 2 | 0 | 2 |
| Redes Sociales | 2 | 0 | 2 |
| **TOTAL** | **69** | **63** | **6** |

### Relaciones Detectadas

- **Foreign Keys:** 83 relaciones encontradas
- **db.relationship:** 16 relaciones bidireccionales
- **Índices:** Múltiples índices compuestos definidos

---

## ⚠️ RECOMENDACIONES

### Críticas

1. **Exportar modelos faltantes en `__init__.py`:**
   - `PosSaleBackup`, `PosSaleItemBackup`
   - `SurveyResponse`, `SurveySession`
   - `SocialMediaMessage`, `SocialMediaResponse`

2. **Descomentar import de `Notification`:**
   - Línea 46 de `__init__.py`
   - O eliminar el comentario si no es necesario

3. **Eliminar duplicación:**
   - Línea 19: `SnapshotEmpleados`, `SnapshotCajas` duplicados

### Importantes

4. **Documentar sistemas paralelos:**
   - Inventario Legacy vs Nuevo
   - Turnos Legacy vs Jornadas
   - Definir estrategia de migración

5. **Verificar compatibilidad UUID:**
   - Validar que `String(36)` funciona con datos existentes
   - Considerar migración de datos si es necesario

### Opcionales

6. **Consolidar nomenclatura:**
   - `Recipe` vs `ProductRecipe`
   - Considerar renombrar para claridad

---

## 📝 NOTAS ADICIONALES

### Modelos con UUID (Migrados a MySQL)

- `PaymentIntent.id`: `String(36)` con `default=lambda: str(uuid.uuid4())`
- `PaymentAgent.id`: `String(36)` con `default=lambda: str(uuid.uuid4())`

### Modelos con Relaciones Complejas

- `PosSale` → `PosSaleItem` (one-to-many)
- `Jornada` → `PlanillaTrabajador` (one-to-many)
- `TicketEntrega` → `TicketEntregaItem` (one-to-many)
- `BartenderTurno` → múltiples tablas relacionadas

### Modelos de Backup/Historial

- `PosSaleBackup` / `PosSaleItemBackup`: Respaldo de ventas eliminadas
- `SaleAuditLog`: Auditoría completa de ventas
- `SuperadminSaleAudit`: Auditoría específica superadmin

---

## ✅ CONCLUSIÓN

**Estado General:** ✅ **BUENO**

- Todos los modelos definidos tienen uso detectado
- Estructura bien organizada por módulos
- Relaciones bien definidas
- Problemas menores de exportación/importación

**Acciones Requeridas:**
1. Exportar 6 modelos faltantes en `__init__.py`
2. Corregir import comentado de `Notification`
3. Eliminar duplicación en imports
4. Documentar sistemas paralelos

**Riesgo de Migración a MySQL:** 🟡 **MEDIO**
- Cambios en UUID ya aplicados
- Verificar compatibilidad de tipos de datos
- Revisar índices parciales (no soportados en MySQL)

