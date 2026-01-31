# MVP1 - Sistema de Cajas BIMBA - Documentación Completa

**Fecha:** 2025-01-15  
**Estado:** ✅ Implementado  
**Alcance:** Operación básica de cajas (registro, apertura/cierre de sesión, reportes)

---

## 🏗️ ARQUITECTURA BIMBA (CRÍTICO)

### POS Propio (BIMBAVERSO) = Fuente de Verdad
- **Todas las ventas** se registran en nuestro POS propio (`pos_sales`)
- **Inventario** se descuenta automáticamente desde nuestro sistema
- **Catálogo** y productos están en nuestro sistema
- **GETNET/KLAP NO son sistemas POS**, solo procesadores de pago

### GETNET/KLAP = Procesadores de Pago
- **Solo procesan** la transacción de pago (captura y confirmación)
- **NO manejan** catálogo, inventario ni ventas "oficiales"
- Se registran en `pos_sales.payment_provider` para:
  - Conciliación con extractos bancarios
  - Reportes de uso por provider
  - Tracking de fallback

### Separación: Método vs Proveedor
- **payment_method** (`payment_type`): Forma de pago (cash, debit, credit, transfer, prepaid, qr)
- **payment_provider**: Procesador (GETNET, KLAP, NONE)
- Ejemplos:
  - Efectivo: `payment_type=cash`, `payment_provider=NONE`
  - Débito GETNET: `payment_type=debit`, `payment_provider=GETNET`
  - Débito fallback KLAP: `payment_type=debit`, `payment_provider=KLAP`

### Flujo Operativo Real
1. **Caja abre sesión** (`RegisterSession`)
2. **POS propio vende** (registra en `pos_sales`, descuenta inventario)
3. **En cada venta se selecciona:**
   - Método de pago (cash/debit/credit)
   - Proveedor (GETNET/KLAP/NONE)
4. **Cierre de sesión:**
   - Arqueo efectivo
   - Totales por método/proveedor desde nuestras ventas
   - Reporte de fallback_events (manual por ahora)

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### ✅ Modelos y Migración
- [x] Migración unificada creada: `migrations/2025_01_15_bimba_cajas_mvp1_paymentstack.sql` (idempotente)
- [x] Agregados campos nuevos a `PosRegister`:
  - `register_type` (TOTEM/HUMANA/OFICINA/VIRTUAL)
  - `devices` (JSON text)
  - `operation_mode` (JSON text)
  - `payment_methods` (JSON array)
  - `responsible_user_id`, `responsible_role`
  - `operational_status` (active/maintenance/offline/error)
  - `fallback_config` (JSON text)
  - `fast_lane_config` (JSON text)
- [x] Agregados campos nuevos a `RegisterSession`:
  - `cash_count` (JSON text)
  - `payment_totals` (JSON text)
  - `ticket_count` (int)
  - `cash_difference` (numeric)
  - `incidents` (JSON array)
  - `close_notes` (text)
- [x] Creado script de migración SQL: `migrations/add_cajas_mvp1_fields.sql`

### ✅ Formularios Admin
- [x] Actualizado `app/templates/admin/registers/form.html` con nuevos campos
- [x] Actualizado `app/routes/register_admin_routes.py` para procesar nuevos campos
- [x] Validación de JSON en formularios (devices, operation_mode, payment_methods)
- [x] Validación de `register_type` (TOTEM/HUMANA/OFICINA/VIRTUAL)

### ✅ Servicio de Sesiones
- [x] Mejorado `RegisterSessionService.close_session()`:
  - Calcula `payment_totals` desde ventas
  - Calcula `ticket_count` (número de ventas)
  - Calcula `cash_difference` (efectivo contado - esperado)
  - Guarda `cash_count`, `incidents`, `close_notes`

### ✅ Rutas y Templates
- [x] Creada ruta `/caja/session/open` (GET/POST)
- [x] Creada ruta `/caja/session/close` (GET/POST)
- [x] Creado template `app/templates/caja/session/open.html`
- [x] Creado template `app/templates/caja/session/close.html`
- [x] Creada ruta `/admin/cajas/reportes` (GET)
- [x] Creado template `app/templates/admin/cajas/reportes.html`

---

## 🗄️ MIGRACIÓN DE BASE DE DATOS

### Ejecutar Migración

**PostgreSQL:**
```bash
psql -U tu_usuario -d tu_base_de_datos -f migrations/add_cajas_mvp1_fields.sql
```

**O desde Python:**
```python
from app import create_app, db
from app.models import PosRegister, RegisterSession

app = create_app()
with app.app_context():
    # Ejecutar migración manualmente si es necesario
    # Las columnas se agregarán automáticamente si no existen
    pass
```

### Verificar Migración

```sql
-- Verificar columnas en pos_registers
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name IN ('register_type', 'devices', 'operation_mode', 'payment_methods', 
                     'responsible_user_id', 'responsible_role', 'operational_status', 
                     'fallback_config', 'fast_lane_config')
ORDER BY column_name;

-- Verificar columnas en register_sessions
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns
WHERE table_name = 'register_sessions'
AND column_name IN ('cash_count', 'payment_totals', 'ticket_count', 'cash_difference', 
                     'incidents', 'close_notes')
ORDER BY column_name;
```

---

## 🚀 ENDPOINTS Y PANTALLAS NUEVAS

### Admin - Gestión de Cajas

#### Crear/Editar Caja
- **URL:** `/admin/cajas/crear` y `/admin/cajas/<id>/editar`
- **Método:** GET, POST
- **Campos nuevos:**
  - Tipo de Caja (TOTEM/HUMANA/OFICINA/VIRTUAL) *
  - Estado Operativo (active/maintenance/offline/error)
  - Dispositivos (JSON)
  - Modo de Operación (JSON)
  - Métodos de Pago (checkboxes: cash, debit, credit, qr)
  - Usuario Responsable (ID y Rol)
  - Configuración de Fallback (JSON)
  - Configuración de Fast Lane (JSON)

#### Reportes de Cajas
- **URL:** `/admin/cajas/reportes`
- **Método:** GET
- **Muestra:**
  - Lista de todas las cajas
  - Última sesión por caja
  - Status de sesión (Abierta/Cerrada/Pendiente)
  - Total por método de pago (efectivo, débito, crédito)
  - Número de tickets
  - Diferencia de efectivo

### POS - Apertura/Cierre de Sesión

#### Abrir Sesión
- **URL:** `/caja/session/open`
- **Método:** GET, POST
- **Campos:**
  - Caja (select) *
  - Jornada (select, opcional - usa jornada abierta actual si no se especifica)
  - Fondo Inicial (number, opcional)

#### Cerrar Sesión
- **URL:** `/caja/session/close`
- **Método:** GET, POST
- **Campos:**
  - Conteo de Efectivo por Denominación ($1.000, $2.000, $5.000, $10.000, $20.000)
  - Notas del Cierre (textarea)
  - Incidentes (JSON array, opcional)
- **Calcula automáticamente:**
  - Total de efectivo contado
  - Totales por método de pago (desde ventas)
  - Número de tickets
  - Diferencia de efectivo (contado - esperado)

---

## 🧪 INSTRUCCIONES PARA PROBAR EN LOCAL

### 1. Preparación

```bash
# 1. Aplicar migración
psql -U postgres -d bimba_db -f migrations/add_cajas_mvp1_fields.sql

# 2. Verificar que el servidor esté corriendo
python app.py
# o
flask run
```

### 2. Probar Crear Caja

1. **Acceder a Admin:**
   - Ir a `http://localhost:5000/admin/cajas/crear`
   - Login como admin

2. **Crear Caja TOTEM:**
   - Nombre: "CAJA LUNA 1"
   - Código: "LUNA1"
   - Tipo de Caja: **TOTEM**
   - Estado Operativo: **active**
   - Dispositivos: `{"pos": "GETNET-123", "printer": "Epson-TM20", "drawer": false}`
   - Modo de Operación: `{"mode": "normal"}`
   - Métodos de Pago: ✅ Efectivo, ✅ Débito, ✅ Crédito
   - Guardar

3. **Crear Caja HUMANA:**
   - Nombre: "CAJA PUERTA"
   - Código: "PUERTA"
   - Tipo de Caja: **HUMANA**
   - Estado Operativo: **active**
   - Dispositivos: `{"pos": "GETNET-456", "printer": "Epson-TM20", "drawer": true}`
   - Métodos de Pago: ✅ Efectivo, ✅ Débito, ✅ Crédito
   - Guardar

### 3. Probar Apertura de Sesión

1. **Abrir Jornada:**
   - Ir a `/admin/open_shift` o usar el sistema existente
   - Abrir una jornada

2. **Abrir Sesión de Caja:**
   - Ir a `http://localhost:5000/caja/session/open`
   - Seleccionar "CAJA LUNA 1"
   - Fondo Inicial: `50000`
   - Click en "Abrir Sesión"
   - Debe redirigir a `/caja/sales`

3. **Verificar Sesión:**
   - Verificar que `session['pos_register_session_id']` está guardado
   - Verificar que la sesión aparece como OPEN en la BD

### 4. Probar Cierre de Sesión

1. **Realizar algunas ventas (opcional):**
   - Usar el sistema POS normal para crear ventas
   - O crear ventas directamente en la BD para pruebas

2. **Cerrar Sesión:**
   - Ir a `http://localhost:5000/caja/session/close`
   - Verificar que muestra el resumen de ventas
   - Ingresar conteo de efectivo:
     - $1.000: 10 billetes
     - $2.000: 5 billetes
     - $5.000: 2 billetes
     - Total debe calcularse automáticamente
   - Notas: "Cierre normal, sin incidentes"
   - Click en "Cerrar Sesión"

3. **Verificar Cierre:**
   - Verificar que la sesión está CLOSED en la BD
   - Verificar que `payment_totals` tiene los totales correctos
   - Verificar que `ticket_count` es correcto
   - Verificar que `cash_difference` se calculó correctamente

### 5. Probar Reportes

1. **Ver Reportes:**
   - Ir a `http://localhost:5000/admin/cajas/reportes`
   - Verificar que muestra todas las cajas
   - Verificar que muestra última sesión, totales, tickets, diferencias

---

## 🧪 INSTRUCCIONES PARA PROBAR EN VM/PRODUCCIÓN

### 1. Aplicar Migración en Producción

```bash
# SSH a la VM
ssh usuario@stvaldivia.cl

# Backup de BD antes de migrar
pg_dump -U postgres bimba_db > backup_antes_mvp1_$(date +%Y%m%d_%H%M%S).sql

# Aplicar migración
psql -U postgres -d bimba_db -f migrations/add_cajas_mvp1_fields.sql

# Verificar migración
psql -U postgres -d bimba_db -c "\d pos_registers"
psql -U postgres -d bimba_db -c "\d register_sessions"
```

### 2. Desplegar Código

```bash
# En la VM, hacer pull del código
cd /ruta/al/proyecto
git pull origin main

# Reiniciar aplicación (según tu setup)
sudo systemctl restart gunicorn
# o
sudo systemctl restart flask-app
```

### 3. Probar en Producción

1. **Crear cajas de prueba:**
   - Acceder a `https://stvaldivia.cl/admin/cajas/crear`
   - Crear cajas según tipos (TOTEM, HUMANA, OFICINA, VIRTUAL)

2. **Probar apertura/cierre:**
   - Abrir jornada
   - Abrir sesión de caja
   - Realizar ventas (o simular)
   - Cerrar sesión con arqueo

3. **Verificar reportes:**
   - Acceder a `https://stvaldivia.cl/admin/cajas/reportes`
   - Verificar que los datos se muestran correctamente

---

## 📊 ESTRUCTURA DE DATOS

### PosRegister - Campos Nuevos

```python
register_type = 'TOTEM'  # TOTEM, HUMANA, OFICINA, VIRTUAL
devices = '{"pos": "GETNET-123", "printer": "Epson-TM20", "drawer": false}'
operation_mode = '{"mode": "normal"}'  # normal, courtesy, prepurchase
payment_methods = '["cash", "debit", "credit", "qr"]'
responsible_user_id = 'user123'
responsible_role = 'cajero'
operational_status = 'active'  # active, maintenance, offline, error
fallback_config = '{"enabled": false}'  # MVP3
fast_lane_config = '{"enabled": false}'  # MVP3
```

### RegisterSession - Campos Nuevos

```python
cash_count = '{"1000": 10, "2000": 5, "5000": 2, "total": 25000}'
payment_totals = '{"cash": 100000, "debit": 50000, "credit": 30000}'
ticket_count = 25
cash_difference = 5000.0  # positivo = sobra, negativo = falta
incidents = '[{"type": "printer_down", "description": "Impresora falló a las 22:30"}]'
close_notes = 'Cierre normal, sin incidentes'
```

---

## ⚠️ NOTAS IMPORTANTES

1. **Compatibilidad:** Los campos nuevos son nullable por defecto, así que las cajas existentes seguirán funcionando.

2. **register_type vs tpv_type:** `register_type` es el nuevo campo según plan BIMBA. `tpv_type` es legacy y se mantiene para compatibilidad.

3. **Cálculo de cash_difference:**
   - `cash_difference = efectivo_contado - (initial_cash + ventas_efectivo)`
   - Positivo = sobra dinero
   - Negativo = falta dinero
   - Null = no se hizo conteo

4. **ticket_count:** Se calcula contando las ventas (`PosSale`) de la sesión, excluyendo canceladas y no_revenue.

5. **payment_totals:** Se calcula sumando `payment_cash`, `payment_debit`, `payment_credit` de todas las ventas de la sesión.

---

## 💳 ESTRATEGIA DE PAGOS (GETNET + KLAP)

### Decisión Estratégica
- **Provider Principal:** GETNET (Banco Santander)
- **Provider Backup:** KLAP (Tap On Phone)
- **Estrategia:** GETNET_PRIMARY_KLAP_BACKUP

### Configuración por Tipo de Caja

**TOTEM:**
- Principal: GETNET
- Backup: KLAP (operativo manual, no integrado aún)

**HUMANA/OFICINA:**
- Principal: GETNET
- Backup: KLAP (recomendado y operativo)

**VIRTUAL:**
- Principal: GETNET
- Backup: No aplica (integración real en fase posterior)

### Campos Agregados (Payment Stack)

**PosRegister:**
- `payment_provider_primary` (default: GETNET)
- `payment_provider_backup` (KLAP o null)
- `provider_config` (JSON: configuración por proveedor)
- `fallback_policy` (JSON: reglas de fallback)

**RegisterSession:**
- `payment_provider_used_primary_count` (contador GETNET)
- `payment_provider_used_backup_count` (contador KLAP)
- `fallback_events` (JSON array: eventos de fallback)

### Documentación Operativa
Ver `docs/PAGOS_BIMBA.md` para:
- Procedimientos de fallback
- Checklists de inicio/cierre
- Requisitos KLAP
- Contactos de soporte

---

## 📊 ASOCIACIÓN VENTAS-SESIONES

### Nota Importante: PosSale NO tiene register_session_id

**Asociación actual:**
- `PosSale` se asocia a `RegisterSession` por:
  - `register_id` (ID de la caja)
  - `shift_date` (fecha del turno)
  - Ventana temporal: `created_at >= opened_at` (ventas desde apertura de sesión)

**Cálculo en `close_session`:**
- `payment_totals`: Suma de `payment_cash`, `payment_debit`, `payment_credit` desde ventas
- `ticket_count`: Conteo de ventas (excluyendo canceladas y no_revenue)
- `cash_difference`: `cash_counted - (initial_cash + payment_totals['cash'])`

**Filtros aplicados:**
- `is_cancelled == False`
- `no_revenue == False`
- `created_at >= opened_at` (ventana temporal de la sesión)

**Decisión de diseño:**
Esta aproximación permite calcular totales por sesión sin requerir FK explícita, manteniendo compatibilidad con el modelo existente.

---

## 🔄 PRÓXIMOS PASOS (MVP2 y MVP3)

### MVP2 (No incluido en MVP1)
- Caja virtual con QR
- Validación rápida en pista/puerta
- Integración real con GETNET API

### MVP3 (No incluido en MVP1)
- Fast lane (cola rápida)
- Fallback automatizado cuando totem falla
- Offline light
- Métricas avanzadas
- Integración real con KLAP API

---

## 📝 COMMITS REALIZADOS

```
feat(cajas): add register fields + migration
feat(admin): cajas create/edit forms for new config
feat(sessions): open/close register session with cash count + totals
feat(reports): basic cajas reports view
docs: CAJAS_MVP1 setup + usage
```

---

## ✅ DEFINITION OF DONE

- [x] Modelos actualizados con campos nuevos
- [x] Migración SQL creada y probada
- [x] Formularios admin actualizados
- [x] Servicio de cierre mejorado
- [x] Rutas de apertura/cierre creadas
- [x] Templates creados y funcionales
- [x] Reportes básicos implementados
- [x] Documentación completa
- [x] Sin errores de linting críticos
- [x] Compatibilidad con código existente mantenida

---

**MVP1 Completado ✅**

