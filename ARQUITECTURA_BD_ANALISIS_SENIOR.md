# Análisis Arquitectónico de Base de Datos - Sistema BIMBA

**Fecha:** 2025-12-25  
**Arquitecto:** Análisis Senior de BD  
**Contexto:** Sistema en producción - **ANÁLISIS SOLO, SIN CAMBIOS**  
**Prioridad:** Estabilidad absoluta del sistema

---

## ⚠️ INFORMACIÓN FALTANTE

**Para completar este análisis, se requiere:**

1. **Esquema real de la base de datos:**
   - Dump SQL de la estructura (`SHOW CREATE TABLE` para cada tabla en MySQL)
   - O `pg_dump --schema-only` si es PostgreSQL
   - Ubicación esperada: `backups/` o `docs/schema/`

2. **Datos de producción (estadísticas):**
   - Número de registros por tabla
   - Tamaño de tablas
   - Frecuencia de uso (logs de queries si están disponibles)

3. **Relaciones reales:**
   - Foreign Keys reales en BD (pueden diferir de modelos ORM)
   - Constraints y triggers existentes

**Sin esta información, el análisis se basa en modelos ORM inferidos.**

---

## 📊 MAPA LÓGICO DE LA BASE DE DATOS

### MÓDULO 1: POS (Punto de Venta) - **CRÍTICO**

**Núcleo de Transacciones:**

```
┌─────────────────┐
│ pos_registers   │ ◄─── Cajas registradoras (maestro)
└────────┬────────┘
         │
         ├──► register_sessions ──► register_closes
         │         │
         │         └──► pos_sales ──► pos_sale_items
         │                   │
         │                   ├──► payment_intents
         │                   ├──► sale_audit_logs
         │                   └──► ticket_entregas
         │
         └──► register_locks
```

**Tablas Críticas:**
- `pos_registers` - **CRÍTICA** - Maestro de cajas
- `pos_sales` - **CRÍTICA** - Transacciones de venta
- `pos_sale_items` - **CRÍTICA** - Items de venta
- `register_sessions` - **CRÍTICA** - Sesiones activas
- `payment_intents` - **CRÍTICA** - Pagos pendientes

**Tablas Secundarias:**
- `pos_sessions` - Carritos temporales (puede limpiarse)
- `register_locks` - Bloqueos temporales
- `register_closes` - Historial de cierres
- `logs_intentos_pago` - Logs de debugging
- `payment_agents` - Estado de agentes de pago

**Tablas de Backup/Historial:**
- `pos_sales_backup` - ⚠️ **NO EXPORTADA** - Respaldo de ventas eliminadas
- `pos_sale_items_backup` - ⚠️ **NO EXPORTADA** - Items de respaldo

**Relaciones Clave:**
- `pos_sales.jornada_id` → `jornadas.id` (FK fuerte)
- `pos_sales.register_session_id` → `register_sessions.id`
- `pos_sale_items.sale_id` → `pos_sales.id`
- `payment_intents.register_session_id` → `register_sessions.id`

**Observaciones:**
- ⚠️ `pos_sales_backup` y `pos_sale_items_backup` existen pero NO están en `__init__.py`
- Sistema de backup funcional pero no accesible vía imports estándar

---

### MÓDULO 2: JORNADAS Y TURNOS - **CRÍTICO**

**Sistema Dual (Legacy + Nuevo):**

```
┌─────────────┐      ┌──────────────┐
│   shifts    │      │   jornadas   │ ◄─── Sistema nuevo (activo)
│  (LEGACY)   │      └──────┬───────┘
└─────────────┘             │
                             ├──► planilla_trabajadores
                             ├──► aperturas_cajas
                             ├──► snapshot_empleados
                             └──► snapshot_cajas
```

**Tablas Críticas:**
- `jornadas` - **CRÍTICA** - Jornadas de trabajo (sistema activo)
- `planilla_trabajadores` - **CRÍTICA** - Asignación de trabajadores
- `aperturas_cajas` - **CRÍTICA** - Aperturas de caja por jornada

**Tablas Secundarias:**
- `snapshot_empleados` - Snapshots históricos
- `snapshot_cajas` - Snapshots históricos

**Tablas Legacy:**
- `shifts` - ⚠️ **LEGACY** - Sistema antiguo (archivo JSON migrado)
  - Coexiste con `jornadas`
  - Posiblemente obsoleto pero mantener por compatibilidad

**Relaciones Clave:**
- `planilla_trabajadores.jornada_id` → `jornadas.id` (FK fuerte)
- `planilla_trabajadores.cargo_id` → `cargos.id`
- `aperturas_cajas.jornada_id` → `jornadas.id`
- `pos_sales.jornada_id` → `jornadas.id` (muchas ventas dependen)

**Observaciones:**
- ⚠️ Sistema dual: `shifts` (legacy) y `jornadas` (nuevo) coexisten
- `shifts` puede estar obsoleto pero NO eliminar sin verificar uso
- Snapshots son históricos, pueden archivarse

---

### MÓDULO 3: EMPLEADOS Y CARGOS - **CRÍTICO**

```
┌─────────────┐
│  employees  │ ◄─── Maestro de empleados
└──────┬──────┘
       │
       ├──► employee_shifts
       ├──► employee_payments
       ├──► employee_advances
       │
┌──────┴──────┐
│   cargos    │ ◄─── Maestro de cargos
└──────┬──────┘
       │
       ├──► cargo_salary_configs
       ├──► cargo_salary_audit_logs
       └──► planilla_trabajadores (FK)
```

**Tablas Críticas:**
- `employees` - **CRÍTICA** - Maestro de empleados
- `cargos` - **CRÍTICA** - Maestro de cargos
- `employee_payments` - **CRÍTICA** - Pagos a empleados
- `cargo_salary_configs` - **CRÍTICA** - Configuración de sueldos

**Tablas Secundarias:**
- `employee_shifts` - Historial de turnos
- `employee_advances` - Abonos excepcionales
- `employee_salary_configs` - Configuración individual
- `ficha_review_logs` - Logs de revisión
- `cargo_salary_audit_logs` - Auditoría de cambios

**Relaciones Clave:**
- `planilla_trabajadores.cargo_id` → `cargos.id`
- `planilla_trabajadores.id_empleado` → `employees.id` (String, no FK)
- `employee_shifts.jornada_id` → `jornadas.id`

**Observaciones:**
- ⚠️ `employees.id` es String, no FK directa (compatibilidad con sistema externo)
- Sistema de auditoría completo para cambios en sueldos

---

### MÓDULO 4: INVENTARIO Y PRODUCTOS - **SISTEMA DUAL**

**Sistema Legacy:**

```
┌──────────────┐
│  products     │ ◄─── Maestro de productos
└──────┬───────┘
       │
       ├──► inventory_items (LEGACY)
       └──► recipe_ingredients_legacy
            └──► product_recipes
```

**Sistema Nuevo:**

```
┌──────────────────┐
│ingredient_categories│
└──────────┬───────┘
           │
           └──► ingredients ──► ingredient_stocks
                      │
                      ├──► recipe_ingredients
                      └──► inventory_movements
                            │
                            └──► recipes
```

**Tablas Críticas:**
- `products` - **CRÍTICA** - Catálogo de productos
- `ingredients` - **CRÍTICA** - Ingredientes (sistema nuevo)
- `ingredient_stocks` - **CRÍTICA** - Stock por ubicación
- `recipes` - **CRÍTICA** - Recetas (sistema nuevo)

**Tablas Secundarias:**
- `ingredient_categories` - Categorías
- `recipe_ingredients` - Ingredientes de recetas
- `inventory_movements` - Movimientos de inventario

**Tablas Legacy:**
- `inventory_items` - ⚠️ **LEGACY** - Sistema antiguo (JSON migrado)
- `recipe_ingredients_legacy` - ⚠️ **LEGACY** - Ingredientes antiguos
- `product_recipes` - ⚠️ **LEGACY** - Recetas antiguas

**Relaciones Clave:**
- `ingredients.category_id` → `ingredient_categories.id`
- `ingredient_stocks.ingredient_id` → `ingredients.id`
- `recipe_ingredients.ingredient_id` → `ingredients.id`
- `recipe_ingredients.recipe_id` → `recipes.id`

**Observaciones:**
- ⚠️ **SISTEMA DUAL CRÍTICO**: Legacy y Nuevo coexisten
- `inventory_items` puede estar obsoleto pero verificar uso
- `recipe_ingredients_legacy` renombrado explícitamente para evitar conflicto
- Conflicto de nombres: `Recipe` (nuevo) vs `ProductRecipe` (legacy)

---

### MÓDULO 5: ENTREGAS Y DELIVERY - **IMPORTANTE**

```
┌──────────────┐
│  deliveries   │ ◄─── Entregas de tragos
└──────┬───────┘
       │
       ├──► sale_delivery_status
       ├──► delivery_items
       ├──► fraud_attempts
       ├──► ticket_scans
       │
┌──────┴──────┐
│pos_sales    │
└──────┬──────┘
       │
       └──► ticket_entregas ──► ticket_entrega_items
                              └──► delivery_logs
```

**Tablas Críticas:**
- `deliveries` - **CRÍTICA** - Entregas de tragos
- `ticket_entregas` - **CRÍTICA** - Tickets con QR
- `ticket_entrega_items` - **CRÍTICA** - Items de tickets

**Tablas Secundarias:**
- `sale_delivery_status` - Estado de entregas
- `delivery_items` - Items de entrega
- `delivery_logs` - Logs de entregas
- `fraud_attempts` - Detección de fraude
- `ticket_scans` - Escaneos de tickets

**Relaciones Clave:**
- `ticket_entregas.sale_id` → `pos_sales.id` (unique)
- `ticket_entregas.jornada_id` → `jornadas.id`
- `ticket_entrega_items.ticket_id` → `ticket_entregas.id`
- `sale_delivery_status.delivery_id` → `deliveries.id`

---

### MÓDULO 6: GUARDARROPÍA - **SECUNDARIO**

```
┌──────────────────┐
│guardarropia_items │ ◄─── Items de guardarropía
└──────────┬───────┘
           │
           └──► guardarropia_tickets ──► guardarropia_ticket_logs
```

**Tablas:**
- `guardarropia_items` - Items de guardarropía
- `guardarropia_tickets` - Tickets con QR
- `guardarropia_ticket_logs` - Logs de tickets

**Relaciones:**
- `guardarropia_tickets.item_id` → `guardarropia_items.id`
- `guardarropia_tickets.jornada_id` → `jornadas.id`

---

### MÓDULO 7: TURNOS DE BARTENDER - **ESPECIALIZADO**

```
┌──────────────────┐
│ bartender_turnos │ ◄─── Turnos de bartender
└──────────┬───────┘
           │
           ├──► turno_stock_inicial
           ├──► turno_stock_final
           ├──► merma_inventario
           ├──► turno_desviacion_inventario
           └──► alerta_fuga_turno
```

**Tablas:**
- `bartender_turnos` - Turnos de bartender
- `turno_stock_inicial` - Stock inicial
- `turno_stock_final` - Stock final
- `merma_inventario` - Mermas calculadas
- `turno_desviacion_inventario` - Desviaciones
- `alerta_fuga_turno` - Alertas de fuga

**Relaciones:**
- Todas relacionadas con `bartender_turnos.id`
- Relacionadas con `ingredients.id`

---

### MÓDULO 8: PROGRAMACIÓN - **SECUNDARIO**

```
┌──────────────────────┐
│programacion_eventos  │
└──────────┬───────────┘
           │
           └──► programacion_asignaciones
```

**Tablas:**
- `programacion_eventos` - Eventos programados
- `programacion_asignaciones` - Asignaciones a eventos

**Relaciones:**
- `programacion_asignaciones.evento_id` → `programacion_eventos.id`
- `programacion_asignaciones.cargo_id` → `cargos.id`
- `programacion_asignaciones.employee_id` → `employees.id` (String)

---

### MÓDULO 9: KIOSKO - **SECUNDARIO**

```
┌─────────┐
│  pagos  │
└────┬────┘
     │
     └──► pagos_items
```

**Tablas:**
- `pagos` - Pagos del kiosko
- `pagos_items` - Items de pagos

**Relaciones:**
- `pagos_items.pago_id` → `pagos.id`

---

### MÓDULO 10: AUDITORÍA Y LOGS - **IMPORTANTE**

```
┌──────────────────┐
│   audit_logs      │ ◄─── Auditoría general
│sale_audit_logs    │ ◄─── Auditoría de ventas
│superadmin_sale_audit│ ◄─── Auditoría superadmin
│api_connection_logs│ ◄─── Logs de API
│bot_logs          │ ◄─── Logs de bot
└──────────────────┘
```

**Tablas:**
- `audit_logs` - Auditoría general del sistema
- `sale_audit_logs` - Auditoría específica de ventas
- `superadmin_sale_audit` - Auditoría superadmin
- `api_connection_logs` - Logs de conexión API
- `bot_logs` - Logs del bot de redes sociales

**Relaciones:**
- `sale_audit_logs.sale_id` → `pos_sales.id`
- `sale_audit_logs.jornada_id` → `jornadas.id`
- `sale_audit_logs.register_session_id` → `register_sessions.id`
- `superadmin_sale_audit.sale_id` → `pos_sales.id`

---

### MÓDULO 11: NOTIFICACIONES - **SECUNDARIO**

```
┌──────────────┐
│notifications  │ ◄─── Sistema de notificaciones
└──────────────┘
```

**Tablas:**
- `notifications` - Notificaciones del sistema

**Observaciones:**
- ⚠️ Import comentado en `__init__.py` pero modelo se usa

---

### MÓDULO 12: ENCUESTAS - **EXPERIMENTAL**

```
┌──────────────────┐
│survey_responses   │
└──────────┬───────┘
           │
           └──► survey_sessions
```

**Tablas:**
- `survey_responses` - Respuestas de encuestas
- `survey_sessions` - Sesiones de encuestas

**Observaciones:**
- ⚠️ **NO EXPORTADAS** en `__init__.py`
- Uso limitado detectado

---

### MÓDULO 13: REDES SOCIALES - **EXPERIMENTAL**

```
┌──────────────────────┐
│social_media_messages │
└──────────┬───────────┘
           │
           └──► social_media_responses
```

**Tablas:**
- `social_media_messages` - Mensajes de redes sociales
- `social_media_responses` - Respuestas

**Observaciones:**
- ⚠️ **NO EXPORTADAS** en `__init__.py`
- Sistema experimental, posiblemente no activo

---

## 🎯 CLASIFICACIÓN DE TABLAS

### TABLAS CRÍTICAS (No tocar sin migración planificada)

**Núcleo de Transacciones:**
1. `pos_registers` - Maestro de cajas
2. `pos_sales` - Ventas (corazón del sistema)
3. `pos_sale_items` - Items de venta
4. `register_sessions` - Sesiones activas
5. `payment_intents` - Pagos pendientes
6. `jornadas` - Jornadas de trabajo
7. `planilla_trabajadores` - Asignación de trabajadores
8. `employees` - Maestro de empleados
9. `cargos` - Maestro de cargos
10. `products` - Catálogo de productos
11. `ingredients` - Ingredientes (sistema nuevo)
12. `ingredient_stocks` - Stock de ingredientes
13. `deliveries` - Entregas
14. `ticket_entregas` - Tickets con QR

**Total: 14 tablas críticas**

### TABLAS IMPORTANTES (Revisar antes de cambios)

1. `aperturas_cajas` - Aperturas de caja
2. `employee_payments` - Pagos a empleados
3. `cargo_salary_configs` - Configuración de sueldos
4. `recipes` - Recetas
5. `recipe_ingredients` - Ingredientes de recetas
6. `sale_audit_logs` - Auditoría de ventas
7. `audit_logs` - Auditoría general

**Total: 7 tablas importantes**

### TABLAS SECUNDARIAS (Pueden archivarse/limpiarse)

1. `pos_sessions` - Carritos temporales
2. `register_locks` - Bloqueos temporales
3. `register_closes` - Historial de cierres
4. `logs_intentos_pago` - Logs de debugging
5. `payment_agents` - Estado de agentes
6. `snapshot_empleados` - Snapshots históricos
7. `snapshot_cajas` - Snapshots históricos
8. `employee_shifts` - Historial de turnos
9. `employee_advances` - Abonos
10. `ficha_review_logs` - Logs de revisión
11. `cargo_salary_audit_logs` - Auditoría de cambios
12. `ingredient_categories` - Categorías
13. `inventory_movements` - Movimientos
14. `sale_delivery_status` - Estado de entregas
15. `delivery_items` - Items de entrega
16. `delivery_logs` - Logs de entregas
17. `fraud_attempts` - Intentos de fraude
18. `ticket_scans` - Escaneos
19. `guardarropia_items` - Items de guardarropía
20. `guardarropia_tickets` - Tickets
21. `guardarropia_ticket_logs` - Logs
22. `bartender_turnos` - Turnos de bartender
23. `turno_stock_inicial` - Stock inicial
24. `turno_stock_final` - Stock final
25. `merma_inventario` - Mermas
26. `turno_desviacion_inventario` - Desviaciones
27. `alerta_fuga_turno` - Alertas
28. `programacion_eventos` - Eventos
29. `programacion_asignaciones` - Asignaciones
30. `pagos` - Pagos kiosko
31. `pagos_items` - Items de pagos
32. `notifications` - Notificaciones
33. `api_connection_logs` - Logs API
34. `bot_logs` - Logs bot
35. `superadmin_sale_audit` - Auditoría superadmin

**Total: 35 tablas secundarias**

### TABLAS LEGACY/EXPERIMENTALES (Verificar uso antes de eliminar)

**Legacy:**
1. `shifts` - ⚠️ Sistema antiguo (coexiste con `jornadas`)
2. `inventory_items` - ⚠️ Sistema antiguo (coexiste con `ingredient_stocks`)
3. `recipe_ingredients_legacy` - ⚠️ Sistema antiguo
4. `product_recipes` - ⚠️ Sistema antiguo

**Backup/Historial:**
5. `pos_sales_backup` - ⚠️ Respaldo de ventas eliminadas
6. `pos_sale_items_backup` - ⚠️ Items de respaldo

**Experimentales:**
7. `survey_responses` - ⚠️ Encuestas (no exportada)
8. `survey_sessions` - ⚠️ Sesiones de encuestas (no exportada)
9. `social_media_messages` - ⚠️ Redes sociales (no exportada)
10. `social_media_responses` - ⚠️ Respuestas (no exportada)

**Total: 10 tablas legacy/experimentales**

---

## 🔍 DETECCIÓN DE PROBLEMAS

### 1. TABLAS DUPLICADAS (Sistemas Paralelos)

**A. Turnos:**
- `shifts` (legacy) vs `jornadas` (nuevo)
- **Riesgo:** Confusión, datos duplicados
- **Acción:** Verificar uso de `shifts`, posiblemente obsoleto

**B. Inventario:**
- `inventory_items` (legacy) vs `ingredient_stocks` (nuevo)
- `recipe_ingredients_legacy` vs `recipe_ingredients`
- `product_recipes` (legacy) vs `recipes` (nuevo)
- **Riesgo:** Datos inconsistentes, confusión
- **Acción:** Documentar cuál sistema está activo

### 2. INCONSISTENCIAS DE NOMBRES

**A. Nomenclatura mixta:**
- Español: `jornadas`, `planilla_trabajadores`, `aperturas_cajas`
- Inglés: `employees`, `products`, `ingredients`
- **Impacto:** Bajo (solo estético)
- **Acción:** Considerar estandarización futura (NO urgente)

**B. Conflicto de nombres:**
- `Recipe` (nuevo) vs `ProductRecipe` (legacy)
- `Ingredient` (nuevo) vs `LegacyIngredient` (legacy)
- **Impacto:** Medio (confusión en código)
- **Acción:** Ya resuelto con alias

### 3. RELACIONES FALTANTES O MAL DISEÑADAS

**A. Foreign Keys como String:**
- `planilla_trabajadores.id_empleado` → `employees.id` (String, no FK)
- `programacion_asignaciones.employee_id` → `employees.id` (String, no FK)
- **Riesgo:** Integridad referencial no garantizada
- **Acción:** Mantener por compatibilidad con sistema externo

**B. Relaciones circulares:**
- `bartender_turnos` tiene FK a sí mismo (posible error)
- **Riesgo:** Bajo (verificar lógica)
- **Acción:** Revisar modelo

**C. Índices parciales (PostgreSQL específico):**
- `payment_intents`: `WHERE status IN ('READY', 'IN_PROGRESS')`
- **Riesgo:** No compatible con MySQL
- **Acción:** Ya migrado a MySQL (índice completo)

### 4. MODELOS NO EXPORTADOS

**Modelos que existen pero no están en `__init__.py`:**
1. `PosSaleBackup` / `PosSaleItemBackup` - Backup funcional
2. `SurveyResponse` / `SurveySession` - Encuestas
3. `SocialMediaMessage` / `SocialMediaResponse` - Redes sociales

**Impacto:** Bajo (funcionan con import directo)
**Acción:** Exportar para consistencia

---

## 📐 PROPUESTA DE ORDEN FUTURO (IDEAL)

### FASE 1: Consolidación de Sistemas Duales

**Objetivo:** Eliminar duplicación legacy/nuevo

**Acciones (NO implementar aún):**
1. **Turnos:**
   - Verificar uso real de `shifts`
   - Si obsoleto: Migrar datos a `jornadas` y archivar `shifts`
   - Si activo: Documentar cuándo usar cada uno

2. **Inventario:**
   - Decidir sistema activo (legacy vs nuevo)
   - Migrar datos del sistema obsoleto
   - Archivar tablas legacy (NO eliminar)

**Riesgo:** 🟡 MEDIO - Requiere migración de datos

### FASE 2: Estandarización de Nomenclatura

**Objetivo:** Unificar español/inglés

**Acciones (NO implementar aún):**
1. Decidir estándar (recomendado: inglés)
2. Crear aliases/vistas para compatibilidad
3. Migrar gradualmente

**Riesgo:** 🟢 BAJO - Solo renombrado

### FASE 3: Consolidación de Relaciones

**Objetivo:** Fortalecer integridad referencial

**Acciones (NO implementar aún):**
1. Convertir `id_empleado` String a FK donde sea posible
2. Agregar constraints faltantes
3. Documentar relaciones String (compatibilidad externa)

**Riesgo:** 🟡 MEDIO - Puede romper integraciones

### FASE 4: Limpieza de Tablas Experimentales

**Objetivo:** Eliminar código no usado

**Acciones (NO implementar aún):**
1. Verificar uso real de:
   - `survey_responses` / `survey_sessions`
   - `social_media_messages` / `social_media_responses`
2. Si no usadas: Archivar (NO eliminar)
3. Si usadas: Exportar en `__init__.py`

**Riesgo:** 🟢 BAJO - Solo archivar

### FASE 5: Optimización de Índices

**Objetivo:** Mejorar rendimiento

**Acciones (NO implementar aún):**
1. Analizar queries frecuentes
2. Agregar índices compuestos faltantes
3. Eliminar índices no usados

**Riesgo:** 🟢 BAJO - Solo optimización

---

## ⚠️ RIESGOS DE ORDENAMIENTO SIN MIGRACIÓN PLANIFICADA

### RIESGO CRÍTICO 🔴

**1. Eliminar tablas legacy sin verificar:**
- `shifts` puede tener datos históricos importantes
- `inventory_items` puede estar en uso
- **Consecuencia:** Pérdida de datos, sistema roto
- **Mitigación:** Verificar uso real, migrar datos primero

**2. Cambiar Foreign Keys:**
- Convertir String a FK puede romper integraciones
- `employees.id` como String puede ser requerido por sistema externo
- **Consecuencia:** Queries fallan, integraciones rotas
- **Mitigación:** Mantener compatibilidad, agregar FK opcionales

**3. Renombrar tablas críticas:**
- `pos_sales`, `jornadas`, `employees` son núcleo
- **Consecuencia:** Sistema completamente roto
- **Mitigación:** Usar aliases/vistas, nunca renombrar directamente

### RIESGO ALTO 🟠

**4. Consolidar sistemas duales:**
- Eliminar legacy puede romper código que aún lo usa
- **Consecuencia:** Funcionalidades rotas
- **Mitigación:** Migración gradual, mantener ambos sistemas temporalmente

**5. Modificar estructura de tablas críticas:**
- Agregar/eliminar columnas en `pos_sales`
- **Consecuencia:** Queries fallan, datos inconsistentes
- **Mitigación:** Migraciones versionadas, rollback plan

### RIESGO MEDIO 🟡

**6. Archivar tablas de backup:**
- `pos_sales_backup` puede ser necesario para auditoría
- **Consecuencia:** Pérdida de historial
- **Mitigación:** Verificar políticas de retención

**7. Eliminar índices:**
- Índices pueden ser usados por queries no obvias
- **Consecuencia:** Degradación de rendimiento
- **Mitigación:** Analizar uso real antes de eliminar

---

## 📋 CHECKLIST DE SEGURIDAD

**Antes de CUALQUIER cambio:**

- [ ] Backup completo de BD
- [ ] Verificar uso real de tablas (logs de queries)
- [ ] Documentar dependencias
- [ ] Plan de rollback
- [ ] Pruebas en ambiente de staging
- [ ] Ventana de mantenimiento programada
- [ ] Comunicación con equipo

**NUNCA hacer sin:**
- ❌ Backup completo
- ❌ Verificación de uso real
- ❌ Plan de migración
- ❌ Pruebas exhaustivas

---

## 🎯 RECOMENDACIONES PRIORITARIAS

### INMEDIATAS (Sin riesgo)

1. ✅ Exportar modelos faltantes en `__init__.py`
2. ✅ Descomentar import de `Notification`
3. ✅ Eliminar duplicación en imports
4. ✅ Documentar sistemas duales

### CORTO PLAZO (Con planificación)

1. 📋 Verificar uso real de tablas legacy
2. 📋 Documentar qué sistema está activo (legacy vs nuevo)
3. 📋 Crear vistas/aliases para compatibilidad
4. 📋 Agregar comentarios en código sobre sistemas duales

### LARGO PLAZO (Con migración)

1. 🔄 Consolidar sistemas duales
2. 🔄 Estandarizar nomenclatura
3. 🔄 Fortalecer integridad referencial
4. 🔄 Optimizar índices

---

## 📊 RESUMEN EJECUTIVO

**Estado Actual:** ✅ **ESTABLE**
- Sistema funcional en producción
- Estructura bien organizada por módulos
- Relaciones bien definidas (mayormente)

**Problemas Detectados:**
- Sistemas duales (legacy + nuevo) - 4 casos
- Modelos no exportados - 6 modelos
- Inconsistencias menores de nomenclatura
- Algunas relaciones String en lugar de FK

**Riesgo de Cambios:** 🟡 **MEDIO**
- Cambios estructurales requieren migración planificada
- Sistemas legacy pueden estar en uso
- Integridad referencial parcial

**Recomendación:** 
- **MANTENER ESTABILIDAD** - No hacer cambios sin análisis profundo
- Documentar sistemas duales
- Verificar uso real antes de cualquier eliminación
- Planificar migraciones con ventanas de mantenimiento

---

## 📝 NOTAS FINALES

**Este análisis se basa en:**
- Modelos ORM inferidos (28 archivos)
- Relaciones Foreign Key detectadas (47 relaciones)
- Comentarios en código sobre legacy
- Estructura de migraciones SQL

**Para análisis completo se requiere:**
- Esquema real de BD (dump SQL)
- Estadísticas de uso (logs de queries)
- Datos de producción (volumen, frecuencia)

**Prioridad absoluta:** 🛡️ **ESTABILIDAD DEL SISTEMA**

