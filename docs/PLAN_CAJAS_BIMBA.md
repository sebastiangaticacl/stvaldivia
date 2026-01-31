# 🏪 PLAN SISTEMA DE CAJAS BIMBA - Low-Friction UX

**Fecha:** 2025-01-15  
**Objetivo:** Sistema de cajas con MENOR FRICCIÓN posible para comprar, manteniendo control y trazabilidad

---

## A) OBJETIVO Y MÉTRICAS

### Objetivos Principales:
1. **Reducir tiempo de transacción:** Menos pasos = menos filas
2. **Minimizar abandono:** Fallbacks cuando algo falla
3. **Mantener trazabilidad:** Cada venta asociada a caja/usuario/turno/ticket

### Métricas Clave:

| Métrica | Objetivo | Actual (estimado) | Mejora esperada |
|---------|----------|-------------------|-----------------|
| **Tiempo promedio por venta (Totem)** | < 30 segundos | ~60s | -50% |
| **Tiempo promedio por venta (Humana)** | < 45 segundos | ~90s | -50% |
| **Tiempo promedio (Fast Lane)** | < 15 segundos | N/A | Nuevo |
| **Tasa de fallas técnicas** | < 2% | ~5-10% | -60% |
| **Tasa de abandono** | < 1% | ~3-5% | -70% |
| **Tiempo de recuperación (fallback)** | < 60 segundos | ~5 min | -80% |

### Definición de Éxito:
- ✅ Cliente completa compra en < 1 minuto (Totem) o < 2 minutos (Humana)
- ✅ Si falla Totem, puede usar código QR para pasar a caja humana en < 1 minuto
- ✅ 0 ventas perdidas por fallas técnicas (siempre hay fallback)
- ✅ 100% trazabilidad (caja/usuario/turno/ticket)

---

## B) FLUJOS POR TIPO DE CAJA

### B.1) CAJA TOTEM (LUNA 1, LUNA 2, TERRAZA)

**Dispositivos:** Tótem + POS + Impresora POS  
**Modo:** Auto-servicio completo

#### Flujo Ideal (MVP 1):
1. **Selección de productos** (10-15s)
   - Cliente navega categorías en pantalla táctil
   - Agrega productos al carrito
   - Ve total en tiempo real

2. **Pago** (10-15s)
   - Selecciona método de pago (Efectivo/Débito/Crédito)
   - Si efectivo: ingresa monto recibido → calcula vuelto automático
   - Si tarjeta: inserta/contactless → espera confirmación POS
   - **Tiempo objetivo:** 10-15s

3. **Comprobante** (5s)
   - Impresora genera ticket automáticamente
   - Cliente retira ticket
   - **Tiempo objetivo:** 5s (impresión automática)

4. **Entrega/Ingreso** (5s)
   - Cliente retira productos (si aplica) o ingresa al local
   - **Tiempo objetivo:** 5s

**Tiempo total objetivo:** < 30 segundos

#### Puntos de Fricción y Soluciones:

| Fricción | Solución |
|----------|----------|
| Impresora sin papel | Detección automática → mostrar QR para validación manual |
| POS sin internet | Modo offline → guardar venta local → sincronizar después |
| Cliente confundido | UI simple con iconos grandes + instrucciones visuales |
| Múltiples productos | Carrito visible siempre + botón "Pagar" destacado |
| Tiempo de espera POS | Mostrar "Procesando pago..." con spinner |

#### Fallback (Totem falla):
1. Totem muestra código QR único de la transacción
2. Cliente escanea QR con su celular (o toma foto)
3. Va a caja humana más cercana
4. Cajero escanea QR → carga carrito → procesa pago
5. **Tiempo objetivo:** < 60 segundos desde falla hasta pago

---

### B.2) CAJA HUMANA (PUERTA, PISTA)

**Dispositivos:** Cajero + POS + Impresora + Gaveta  
**Modo:** Atención personalizada

#### Flujo Ideal (MVP 1):
1. **Selección de productos** (15-20s)
   - Cajero busca productos en POS
   - O cliente indica productos verbalmente
   - Cajero agrega al carrito

2. **Pago** (15-20s)
   - Cajero indica total
   - Cliente paga (efectivo/tarjeta)
   - Si efectivo: cajero cuenta → abre gaveta → entrega vuelto
   - Si tarjeta: procesa en POS → espera confirmación

3. **Comprobante** (5s)
   - Impresora genera ticket automáticamente
   - Cajero entrega ticket al cliente

4. **Entrega** (5s)
   - Cliente retira productos o ingresa al local

**Tiempo total objetivo:** < 45 segundos

#### Fast Lane (MVP 3):
Para compras de 1 item (entrada, recarga, producto simple):
- Botón "Fast Lane" en POS
- Seleccionar producto predefinido → cantidad → pago
- **Tiempo objetivo:** < 15 segundos

#### Puntos de Fricción y Soluciones:

| Fricción | Solución |
|----------|----------|
| Búsqueda de productos lenta | Búsqueda rápida por código/nombre + favoritos |
| Conteo de efectivo lento | Calculadora integrada + sugerencia de vuelto |
| Impresora lenta | Impresión en background + mostrar "Imprimiendo..." |
| Cliente indeciso | Mostrar productos más vendidos + sugerencias |

---

### B.3) CAJA OFICINA (CORTESÍAS)

**Dispositivos:** Cajero + POS + Impresora (sin gaveta)  
**Modo:** Solo cortesías (monto $0)

#### Flujo Ideal (MVP 1):
1. **Selección de productos** (10s)
   - Cajero busca productos
   - Agrega al carrito

2. **Aplicar cortesía** (5s)
   - Selecciona "Modo Cortesía"
   - Confirma → total = $0
   - Requiere autorización (PIN superadmin o usuario autorizado)

3. **Comprobante** (5s)
   - Impresora genera ticket con marca "CORTESÍA"
   - Cajero entrega ticket

**Tiempo total objetivo:** < 20 segundos

#### Restricciones:
- ✅ Solo usuarios con permiso "cortesías" pueden usar esta caja
- ✅ Requiere autorización para cada cortesía (PIN o usuario supervisor)
- ✅ Ticket debe mostrar claramente "CORTESÍA" y motivo
- ✅ No requiere gaveta (no hay efectivo)

---

### B.4) CAJA VIRTUAL (COMPRAS ANTICIPADAS)

**Dispositivos:** Sistema web/app + QR  
**Modo:** Compra anticipada + validación rápida en pista/puerta

#### Flujo Ideal (MVP 2):

**Fase 1: Compra Anticipada (cliente en casa/app)**
1. Cliente navega productos en app/web
2. Agrega productos al carrito
3. Selecciona método de pago:
   - **Opción A:** Transferencia bancaria (Chile: Banco Estado, Santander, etc.)
   - **Opción B:** Saldo prepago (recarga cuenta)
   - **Opción C:** Pago en local (reserva con código)
4. Recibe código QR único de compra
5. **Tiempo objetivo:** < 2 minutos (compra completa)

**Fase 2: Validación en Local (pista/puerta)**
1. Cliente llega al local
2. Muestra QR en pantalla del celular
3. Cajero/validador escanea QR con lector o app
4. Sistema valida:
   - ✅ Compra pagada → entrega productos/ingreso
   - ⏳ Compra reservada → procesa pago en caja → entrega
   - ❌ QR inválido/expirado → muestra error
5. **Tiempo objetivo:** < 15 segundos (validación)

#### Puntos de Fricción y Soluciones:

| Fricción | Solución |
|----------|----------|
| QR no se lee | Mostrar código numérico alternativo |
| QR expirado | Renovar QR automáticamente si compra válida |
| Pago pendiente | Redirigir a caja física más cercana |
| Sin internet en local | Modo offline: validar QR contra lista local |

---

## C) CONFIGURACIÓN DE DATOS

### C.1) Modelo: Caja (PosRegister)

**Campos existentes (mantener):**
- `id` (Integer, PK)
- `name` (String) - Ej: "CAJA LUNA 1"
- `code` (String, unique) - Ej: "LUNA1"
- `is_active` (Boolean)
- `location` (String) - Ej: "LUNA1", "LUNA2", "TERRAZA", "PUERTA", "PISTA", "OFICINA"
- `tpv_type` (String) - Ej: "totem", "humana", "oficina", "virtual"
- `printer_config` (JSON) - Configuración de impresora
- `allowed_categories` (JSON array) - Categorías permitidas

**Campos nuevos (agregar):**

```python
# Tipo de caja (enum)
register_type = db.Column(db.String(50), nullable=False, index=True)
# Valores: 'TOTEM', 'HUMANA', 'OFICINA', 'VIRTUAL'

# Dispositivos asociados (JSON)
devices = db.Column(Text, nullable=True)
# Ejemplo: {
#   "pos": {"model": "Ingenico", "serial": "12345"},
#   "printer": {"model": "Epson", "ip": "192.168.1.100"},
#   "drawer": {"enabled": true, "gpio_pin": 18},  # Solo HUMANA
#   "totem": {"screen_size": "15inch", "touch": true}  # Solo TOTEM
# }

# Modo de operación (JSON)
operation_mode = db.Column(Text, nullable=True)
# Ejemplo: {
#   "default_mode": "normal",  # normal, cortesia, precompra
#   "allow_courtesy": false,  # Solo OFICINA = true
#   "allow_prepurchase": false,  # Solo VIRTUAL = true
#   "fast_lane_enabled": true  # Solo HUMANA
# }

# Métodos de pago habilitados (JSON array)
payment_methods = db.Column(Text, nullable=True)
# Ejemplo: ["cash", "debit", "credit", "transfer", "prepaid"]
# Valores: 'cash', 'debit', 'credit', 'transfer', 'prepaid', 'qr'

# Usuario/rol responsable (opcional)
responsible_user_id = db.Column(db.String(50), nullable=True)
responsible_role = db.Column(db.String(50), nullable=True)
# Ejemplo: role = "cajero_puerta" o "supervisor"

# Estado operativo
operational_status = db.Column(db.String(50), default='active', nullable=False)
# Valores: 'active', 'maintenance', 'offline', 'error'
# 'maintenance' = en mantenimiento programado
# 'offline' = sin conexión pero funcional (modo offline)
# 'error' = error crítico, requiere intervención

# Configuración de fallback
fallback_config = db.Column(Text, nullable=True)
# Ejemplo: {
#   "qr_fallback_enabled": true,  # Totem → QR cuando falla
#   "fallback_register_id": 5,  # ID de caja humana para fallback
#   "offline_mode_enabled": true,  # Permitir ventas sin internet
#   "offline_sync_interval": 300  # Sincronizar cada 5 min cuando vuelve internet
# }

# Configuración de fast lane (solo HUMANA)
fast_lane_config = db.Column(Text, nullable=True)
# Ejemplo: {
#   "enabled": true,
#   "max_items": 1,
#   "allowed_categories": ["entradas", "recargas"],
#   "skip_confirmation": false
# }
```

### C.2) Modelo: Sesión de Caja (RegisterSession)

**Campos existentes (mantener):**
- `id` (Integer, PK)
- `register_id` (String)
- `opened_by_employee_id` (String)
- `opened_by_employee_name` (String)
- `opened_at` (DateTime)
- `status` (String) - 'OPEN', 'PENDING_CLOSE', 'CLOSED'
- `shift_date` (String)
- `jornada_id` (Integer, FK)
- `initial_cash` (Numeric)

**Campos nuevos (agregar):**

```python
# Arqueo de cierre (JSON)
cash_count = db.Column(Text, nullable=True)
# Ejemplo: {
#   "cash_total": 150000,
#   "bills": {"1000": 50, "2000": 30, "5000": 10, "10000": 5},
#   "coins": {"100": 20, "500": 15},
#   "counted_by": "employee_id",
#   "counted_at": "2025-01-15T20:00:00"
# }

# Totales por método de pago (calculados, pero guardar snapshot)
payment_totals = db.Column(Text, nullable=True)
# Ejemplo: {
#   "cash": 120000,
#   "debit": 45000,
#   "credit": 30000,
#   "transfer": 15000,
#   "prepaid": 5000,
#   "courtesy": 0
# }

# Contador de tickets
ticket_count = db.Column(db.Integer, default=0, nullable=False)
# Total de ventas realizadas en esta sesión

# Diferencias (si hay)
cash_difference = db.Column(Numeric(10, 2), nullable=True)
# Diferencia entre efectivo esperado y contado
# Positivo = sobrante, Negativo = faltante

# Incidentes durante la sesión (JSON array)
incidents = db.Column(Text, nullable=True)
# Ejemplo: [
#   {
#     "type": "printer_error",
#     "timestamp": "2025-01-15T18:30:00",
#     "description": "Impresora sin papel",
#     "resolved": true,
#     "resolved_at": "2025-01-15T18:32:00"
#   },
#   {
#     "type": "pos_offline",
#     "timestamp": "2025-01-15T19:00:00",
#     "duration_minutes": 5,
#     "sales_affected": 3,
#     "resolved": true
#   }
# ]

# Notas de cierre
close_notes = db.Column(Text, nullable=True)
# Notas del cajero al cerrar (observaciones, problemas, etc.)
```

---

## D) REGLAS DE OPERACIÓN

### D.1) Qué se vende dónde

| Caja | Productos Permitidos | Restricciones |
|------|---------------------|---------------|
| **LUNA 1, LUNA 2, TERRAZA** (Totem) | Todos los productos activos | Sin restricciones (auto-servicio completo) |
| **PUERTA** (Humana) | Entradas + productos físicos | Prioridad: entradas y productos para llevar |
| **PISTA** (Humana) | Tragos + comida + productos | Prioridad: consumo en local |
| **OFICINA** (Cortesías) | Todos (pero monto = $0) | Solo modo cortesía, requiere autorización |
| **VIRTUAL** | Todos (compra anticipada) | Validación en PUERTA o PISTA |

### D.2) Enrutamiento de Clientes

**Señalética física:**
- Totem: "AUTO-SERVICIO - Pague aquí"
- Puerta: "ENTRADAS Y PRODUCTOS"
- Pista: "TRAGOS Y COMIDA"
- Fast Lane: "COMPRA RÁPIDA - 1 producto"

**UI en Totem:**
- Pantalla inicial muestra opciones grandes:
  - "Comprar productos" → navegación completa
  - "Solo entrada" → fast lane (MVP 3)
  - "Recargar saldo" → fast lane (MVP 3)

**UI en Caja Humana:**
- Botón destacado "Fast Lane" para:
  - Entrada simple
  - Recarga de saldo
  - 1 producto específico

### D.3) Fast Lane (MVP 3)

**Criterios:**
- ✅ Máximo 1 producto
- ✅ Categorías permitidas: "entradas", "recargas", productos predefinidos
- ✅ Sin confirmación adicional (pago directo)
- ✅ Tiempo objetivo: < 15 segundos

**Implementación:**
- Botón "Fast Lane" en POS (caja humana)
- Lista de productos fast lane (configurable por caja)
- Flujo: Seleccionar producto → Cantidad → Pago → Ticket

### D.4) Fallback cuando Totem falla

**Escenario:** Totem se congela / sin internet / impresora sin papel

**Proceso:**
1. Totem detecta error crítico
2. Genera código QR único de la transacción (si hay carrito)
3. Muestra pantalla: "Problema técnico. Escanea este código y ve a caja humana"
4. Cliente escanea QR (o toma foto)
5. Va a caja humana más cercana
6. Cajero escanea QR en POS
7. POS carga carrito automáticamente
8. Cajero procesa pago normalmente
9. **Tiempo objetivo:** < 60 segundos desde falla hasta pago

**Implementación técnica:**
- QR contiene: `{transaction_id, cart_items, timestamp, register_id}`
- Endpoint: `POST /caja/fallback/load-from-qr`
- Valida QR → carga carrito en sesión → continúa flujo normal

---

## E) MVP POR FASES

### MVP 1 (1 semana): Operación Básica

**Alcance:**
- ✅ Registrar cajas con tipo (TOTEM/HUMANA/OFICINA/VIRTUAL)
- ✅ Abrir/cerrar sesión de caja
- ✅ Asociar sesión a turno/jornada
- ✅ Realizar ventas desde caja
- ✅ Imprimir ticket básico
- ✅ Reportes básicos (ventas por caja, totales por método de pago)

**No incluye:**
- ❌ Fast lane
- ❌ Fallback QR
- ❌ Caja virtual (compra anticipada)
- ❌ Modo offline avanzado

**Entregables:**
- Formulario `/admin/cajas/crear` con todos los campos nuevos
- Formulario `/admin/cajas/<id>/editar` para modificar configuración
- Vista `/caja/register` mejorada con selección de caja por tipo
- Vista `/caja/session/open` para abrir sesión
- Vista `/caja/session/close` para cerrar con arqueo
- Endpoint `/api/caja/session/close` con validación de arqueo
- Reporte `/admin/cajas/reportes` con ventas por caja

**Tiempo estimado:** 5-7 días

---

### MVP 2 (2 semanas): Caja Virtual + Validación

**Alcance:**
- ✅ Compra anticipada desde app/web
- ✅ Generación de QR único por compra
- ✅ Validación de QR en caja física (PUERTA/PISTA)
- ✅ Pago diferido (reserva con código, pago en local)
- ✅ Integración con métodos de pago Chile (transferencia bancaria)

**Flujos:**
1. Cliente compra en app/web → recibe QR
2. Llega al local → muestra QR
3. Cajero escanea QR → valida → entrega/ingreso

**Entregables:**
- Vista `/caja/virtual/comprar` (público, sin login)
- Endpoint `/api/caja/virtual/create-order` para crear compra
- Endpoint `/api/caja/virtual/payment` para procesar pago
- Vista `/caja/validate-qr` para validar QR en caja física
- Endpoint `/api/caja/validate-qr` para validar QR
- Integración con APIs bancarias (transferencia) o saldo prepago

**Tiempo estimado:** 10-14 días

---

### MVP 3 (2 semanas): Optimizaciones

**Alcance:**
- ✅ Fast lane en caja humana
- ✅ Fallback QR cuando totem falla
- ✅ Modo offline light (guardar ventas localmente, sincronizar después)
- ✅ Métricas en tiempo real (tiempo promedio por venta, tasa de fallas)
- ✅ Reintentos automáticos (impresora, POS)

**Entregables:**
- Botón "Fast Lane" en POS (caja humana)
- Configuración de productos fast lane por caja
- Generación de QR de fallback en totem
- Endpoint `/api/caja/fallback/load-from-qr`
- Modo offline: guardar ventas en localStorage → sincronizar cuando vuelve internet
- Dashboard `/admin/cajas/metricas` con tiempos y tasas de falla

**Tiempo estimado:** 10-14 días

---

## F) CHECKLIST OPERATIVO

### F.1) Checklist de Apertura (por tipo de caja)

#### Totem (LUNA 1, LUNA 2, TERRAZA):
- [ ] **Pantalla táctil:** Encendida y responsive
- [ ] **POS:** Conectado y funcionando (probar transacción de prueba)
- [ ] **Impresora:** Encendida, con papel, conexión OK (probar impresión de prueba)
- [ ] **Red:** Internet funcionando (verificar ping a servidor)
- [ ] **Software:** Sistema cargado y sin errores en consola
- [ ] **Productos:** Catálogo actualizado y visible
- [ ] **Métodos de pago:** Efectivo/Débito/Crédito habilitados
- [ ] **Señalética:** Visible y clara para clientes

**Tiempo objetivo:** < 5 minutos

#### Humana (PUERTA, PISTA):
- [ ] **POS:** Conectado y funcionando
- [ ] **Impresora:** Encendida, con papel, conexión OK
- [ ] **Gaveta:** Funcionando (probar apertura)
- [ ] **Red:** Internet funcionando
- [ ] **Software:** Sistema cargado, cajero logueado
- [ ] **Fondo inicial:** Contado y registrado en sistema
- [ ] **Calculadora:** Disponible (o integrada en POS)
- [ ] **Productos:** Catálogo actualizado
- [ ] **Métodos de pago:** Todos habilitados

**Tiempo objetivo:** < 5 minutos

#### Oficina (CORTESÍAS):
- [ ] **POS:** Conectado y funcionando
- [ ] **Impresora:** Encendida, con papel
- [ ] **Software:** Sistema cargado, usuario con permiso "cortesías" logueado
- [ ] **Autorización:** PIN superadmin o usuario supervisor disponible
- [ ] **Productos:** Catálogo actualizado

**Tiempo objetivo:** < 3 minutos

---

### F.2) Checklist de Cierre

#### Todas las cajas:
- [ ] **Cerrar sesión en sistema:** Botón "Cerrar Sesión" en POS
- [ ] **Arqueo de efectivo** (si aplica):
  - [ ] Contar efectivo físico
  - [ ] Comparar con total esperado del sistema
  - [ ] Registrar diferencia (si hay)
  - [ ] Registrar quien contó y cuando
- [ ] **Totales por método de pago:**
  - [ ] Efectivo: $X
  - [ ] Débito: $X
  - [ ] Crédito: $X
  - [ ] Otros: $X
- [ ] **Contador de tickets:** Verificar número de ventas
- [ ] **Incidentes:** Registrar cualquier problema durante el turno
- [ ] **Notas:** Agregar observaciones si es necesario
- [ ] **Confirmar cierre:** Sistema genera reporte de cierre

**Tiempo objetivo:** < 10 minutos

---

### F.3) Responsabilidades y Fallas

#### Si Totem falla:
1. **Responsable inmediato:** Supervisor de turno
2. **Acción:** Activar fallback QR → redirigir clientes a caja humana
3. **Solución técnica:** 
   - Reiniciar totem (si es software)
   - Verificar conexión de red
   - Verificar impresora (papel/conexión)
   - Si no se resuelve en 5 min → marcar como "maintenance"

#### Si Impresora falla:
1. **Responsable:** Cajero (humana) o Supervisor (totem)
2. **Acción inmediata:** 
   - Totem → Activar fallback QR
   - Humana → Continuar ventas, imprimir tickets después cuando se repare
3. **Solución técnica:**
   - Verificar papel
   - Verificar conexión (USB/Red)
   - Reiniciar impresora
   - Si no funciona → usar impresora de respaldo o marcar incidente

#### Si POS sin internet:
1. **Responsable:** Cajero/Supervisor
2. **Acción:** Activar modo offline
3. **Solución técnica:**
   - Verificar router/conexión
   - Reiniciar router si es necesario
   - Modo offline guarda ventas localmente
   - Cuando vuelve internet → sincronizar automáticamente

#### Si Gaveta no abre (solo HUMANA):
1. **Responsable:** Cajero
2. **Acción:** Usar gaveta manual o marcar incidente
3. **Solución técnica:**
   - Verificar conexión GPIO/USB
   - Probar apertura manual
   - Si no funciona → usar gaveta de respaldo

---

## IMPLEMENTACIÓN TÉCNICA

### Archivos a modificar/crear:

1. **Modelos:**
   - `app/models/pos_models.py` - Agregar campos nuevos a PosRegister y RegisterSession

2. **Rutas Admin:**
   - `app/routes/register_admin_routes.py` - Mejorar formularios de creación/edición
   - Nueva ruta: `/admin/cajas/reportes` - Reportes de ventas por caja

3. **Rutas POS:**
   - `app/blueprints/pos/views/register.py` - Mejorar selección de caja
   - Nueva ruta: `/caja/session/open` - Apertura de sesión
   - Nueva ruta: `/caja/session/close` - Cierre con arqueo
   - Nueva ruta: `/caja/fallback/load-from-qr` - Cargar carrito desde QR

4. **Templates:**
   - `app/templates/admin/cajas/crear.html` - Formulario completo
   - `app/templates/admin/cajas/editar.html` - Formulario completo
   - `app/templates/caja/session/open.html` - Apertura de sesión
   - `app/templates/caja/session/close.html` - Cierre con arqueo
   - `app/templates/caja/fallback/qr.html` - Pantalla de fallback en totem

5. **Servicios:**
   - `app/services/register_session_service.py` - Lógica de apertura/cierre
   - `app/services/qr_service.py` - Generación y validación de QR

---

## PRÓXIMOS PASOS INMEDIATOS

1. **Revisar modelo PosRegister actual** y agregar campos nuevos
2. **Crear migración de base de datos** para nuevos campos
3. **Actualizar formularios admin** (`/admin/cajas/crear` y `/editar`)
4. **Implementar apertura/cierre de sesión** con arqueo
5. **Probar flujo completo** en desarrollo local

---

**Plan listo para implementación. Priorizar MVP 1 (operación básica) antes de avanzar a MVP 2 y MVP 3.**


