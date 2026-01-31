# Análisis Arquitectónico - Compatibilidad con App Móvil y Wallet Digital

**Fecha:** 2025-01-15  
**Sistema:** stvaldivia.cl (producción)  
**Objetivo:** Evaluar compatibilidad para app móvil de clientes, wallet digital, QR único y pagos rápidos tipo Klap

---

## 1) ARQUITECTURA GENERAL

### Stack Tecnológico Real

**Backend:**
- **Framework:** Flask 2.3.3 (Python)
- **Base de datos:** PostgreSQL (producción) / SQLite (desarrollo)
- **ORM:** SQLAlchemy 2.0.44 con Flask-SQLAlchemy
- **WebSockets:** Flask-SocketIO 5.3.5 (eventlet)
- **Autenticación web:** Flask-WTF con CSRF protection
- **Servidor:** Gunicorn + eventlet (producción)
- **Deployment:** Google Cloud Run

**Frontend:**
- Templates Jinja2 (server-side rendering)
- JavaScript vanilla (sin framework)
- Socket.IO client para actualizaciones en tiempo real
- CSS responsive (mobile-first implementado)

**Integraciones Externas:**
- PHP Point of Sale API (legacy, sincronización)
- OpenAI API (bot de redes sociales)
- Getnet (pagos con tarjeta, agente local)
- Klap (cliente parcialmente implementado, no integrado)

### Estructura de Carpetas

```
app/
├── __init__.py              # Factory pattern (create_app)
├── config.py                # Configuración centralizada
├── models/                  # 68+ modelos SQLAlchemy
│   ├── pos_models.py        # Ventas, cajas, empleados, PaymentIntent
│   ├── ticket_entrega_models.py  # Sistema QR de tickets
│   ├── jornada_models.py     # Turnos/jornadas
│   └── ...
├── routes/                   # Blueprints de rutas web
│   ├── auth_routes.py       # Login admin
│   ├── api_routes.py         # APIs internas
│   └── ...
├── blueprints/              # Módulos funcionales
│   ├── pos/                 # Sistema POS completo
│   ├── api/                 # API V1, Operational
│   ├── kiosk/               # Kiosko de autoservicio
│   └── ...
├── helpers/                 # Utilidades (100+ archivos)
├── infrastructure/          # Repositorios, servicios externos
│   ├── external/           # Clientes API (Getnet, Klap, OpenAI)
│   └── repositories/       # Patrón Repository
└── application/             # Capa de servicios (DDD parcial)
    ├── services/           # Lógica de negocio
    └── dto/                # Data Transfer Objects
```

### Inicialización de la Aplicación

**Punto de entrada:** `app/__init__.py` → `create_app()`

**Flujo de inicialización:**
1. Carga variables de entorno (`.env` en desarrollo, env vars en producción)
2. Valida configuración crítica (SECRET_KEY, DATABASE_URL)
3. Crea instancia Flask
4. Configura CSRF (habilitado en producción, deshabilitado en desarrollo)
5. Configura base de datos (PostgreSQL en producción, SQLite en desarrollo)
6. Inicializa SQLAlchemy y crea tablas
7. Inicializa SocketIO con CORS abierto
8. Registra blueprints (home, auth, pos, api, kiosk, scanner, etc.)
9. Configura context processors (shift info, CSRF token)
10. Registra eventos SocketIO
11. Configura headers de seguridad

**Script de ejecución local:** `run_local.py` (puerto 5001 por defecto)

### Configuración y Entornos

**Variables de entorno críticas:**
- `FLASK_SECRET_KEY` - Obligatorio en producción
- `DATABASE_URL` - PostgreSQL connection string (obligatorio en producción)
- `FLASK_ENV` - 'production' o 'development'
- `API_KEY` / `BASE_API_URL` - PHP POS API (opcional, modo LOCAL_ONLY)
- `OPENAI_API_KEY` - Bot de IA (opcional)
- `AGENT_API_KEY` - Autenticación agente Getnet local
- `ENABLE_GETNET_SERIAL` - Habilitar integración serial Getnet

**Detección de entorno:**
- Producción: `K_SERVICE` o `GAE_ENV` o `CLOUD_RUN_SERVICE` presentes
- Desarrollo: archivos `.env` en múltiples ubicaciones

**Configuración por entorno:**
- Producción: PostgreSQL obligatorio, CSRF habilitado, sin archivos locales
- Desarrollo: SQLite permitido, CSRF deshabilitado, logs en archivos

---

## 2) AUTENTICACIÓN Y USUARIOS

### Sistema de Autenticación Actual

**Tipos de usuarios identificados:**

1. **Administradores** (`/login_admin`)
   - Autenticación: username + password
   - Sistema dual:
     - Archivo de usuarios (`app/helpers/admin_users.py`) - opcional
     - Fallback: contraseña única (`ADMIN_PASSWORD` o `ADMIN_PASSWORD_HASH`)
   - Sesión: `session['admin_logged_in'] = True`
   - Rate limiting: 5 intentos, bloqueo 15 minutos
   - Timeout: 8 horas de inactividad

2. **Empleados POS** (`/caja/login`)
   - Autenticación: selección de empleado + PIN
   - Modelo: `Employee` (tabla `employees`)
   - PIN: almacenado como hash (`pin_hash`) o texto plano (legacy)
   - Validación: `authenticate_employee()` verifica PIN
   - Sesión: `session['pos_logged_in'] = True`
   - Asociación: `pos_employee_id`, `pos_register_id`, `jornada_id`

3. **Bartenders/Barra** (`/scanner/bartender`)
   - Autenticación: selección de empleado (sin PIN en barra)
   - Sesión: `session['bartender_id']`, `session['barra']`
   - Propósito: escanear tickets y entregar productos

4. **Guardarropía** (`/guardarropia/login`)
   - Autenticación: empleado + PIN (similar a POS)
   - Sesión: `session['guardarropia_logged_in'] = True`

### Modelo de Usuario: Employee

**Tabla:** `employees`

**Campos relevantes:**
- `id` (String, PK) - ID único inmutable
- `name`, `first_name`, `last_name` - Información personal
- `pin` / `pin_hash` - Autenticación
- `cargo` - Rol ('Cajero', 'Bartender', etc.)
- `is_bartender`, `is_cashier` - Flags de rol
- `is_active` - Estado activo
- `email`, `rut`, `banco`, `numero_cuenta` - Datos bancarios (para pagos)

**Sincronización:**
- Sincroniza desde PHP POS API (`synced_from_phppos`)
- Cache local para performance

### Concepto de Cliente vs Admin

**NO existe modelo de Cliente/Usuario Final:**
- El sistema actual NO tiene concepto de "cliente" como entidad
- Las ventas (`PosSale`) NO tienen `customer_id`
- No hay registro de usuarios finales
- No hay sistema de cuentas de cliente

**Implicaciones:**
- Para app móvil de clientes, se requiere crear modelo `Customer` desde cero
- No hay autenticación de clientes existente
- No hay historial de compras por cliente
- No hay sistema de puntos o wallet de clientes

### Gestión de Sesiones

**Flask Session:**
- Sesiones basadas en cookies (server-side)
- Secret key para firmar cookies
- Timeout configurable (8 horas por defecto)
- Múltiples sesiones simultáneas (admin, pos, bartender, guardarropía)

**SocketIO Sessions:**
- Gestiona sesiones WebSocket independientes
- `manage_session=True` en configuración
- Usado para actualizaciones en tiempo real (notificaciones, métricas)

**Limitaciones para app móvil:**
- Sesiones web no son ideales para apps móviles
- No hay sistema de tokens JWT
- No hay OAuth2 o autenticación de terceros
- No hay refresh tokens

---

## 3) VENTAS, TICKETS Y BARRA

### Flujo de Ventas Actual

**1. Login POS** (`/caja/login`)
- Empleado selecciona su nombre
- Ingresa PIN
- Validación: `authenticate_employee()` + `puede_abrir_puesto()`
- Redirige a selección de caja

**2. Selección de Caja** (`/caja/register`)
- Lista de cajas disponibles (`PosRegister`)
- Validación: caja no bloqueada, jornada abierta
- Crea `RegisterSession` (estado OPEN)
- Guarda `pos_register_id` en sesión

**3. Pantalla de Ventas** (`/caja/ventas`)
- Carrito temporal (en memoria/sesión)
- Agregar productos: `POST /caja/api/cart/add`
- Validación de stock: `POST /caja/api/stock/validate`
- Calcular total

**4. Crear Venta** (`POST /caja/api/sale/create`)
- Validaciones críticas:
  - `RegisterSession` debe estar OPEN
  - Stock disponible
  - Jornada asociada válida
  - Idempotencia (evitar duplicados)
- Crea `PosSale` + `PosSaleItem`
- Genera `TicketEntrega` automáticamente (con QR)
- Procesa pago según tipo:
  - Efectivo: directo
  - Débito/Crédito: crea `PaymentIntent` → agente Getnet → polling
- Actualiza inventario (si aplica)
- Retorna `sale_id` + `ticket_code`

**5. Ticket QR Generado**
- Cada venta genera `TicketEntrega` con:
  - `display_code` (ej: "BMB 11725")
  - `qr_token` (UUID v4)
  - `hash_integridad` (validación)
- Items del ticket: `TicketEntregaItem` (qty, delivered_qty)

### Estados de Venta

**PosSale:**
- `is_cancelled` - Venta cancelada
- `is_courtesy` - Cortesía (monto 0)
- `is_test` - Prueba
- `no_revenue` - No cuenta como ingreso
- `inventory_applied` - Inventario descontado
- `synced_to_phppos` - Sincronizado con PHP POS

**TicketEntrega:**
- `status`: 'open', 'partial', 'delivered', 'void'
- Estados calculados automáticamente según `delivered_qty`

### Validación de Ventas

**Validaciones implementadas:**
- `RegisterSession` debe estar OPEN (P0-005)
- Stock disponible antes de crear venta
- Jornada asociada válida (P0-004)
- Idempotencia con `idempotency_key` (P0-007)
- Validación de fraude (tickets antiguos, múltiples intentos)
- Validación de cálculos (suma de pagos = total)

**Dónde se valida:**
- `app/helpers/sale_validator.py` - Validaciones de negocio
- `app/helpers/sale_security_validator.py` - Validaciones de seguridad
- `app/blueprints/pos/views/sales.py::api_create_sale()` - Endpoint principal

### Sistema de Tickets QR

**Modelo:** `TicketEntrega`

**Flujo actual:**
1. Venta creada → `TicketEntrega` generado automáticamente
2. QR contiene `qr_token` (UUID)
3. Cliente muestra QR en barra
4. Bartender escanea: `POST /api/tickets/scan` (qr_token)
5. Validación: ticket existe, no anulado, no entregado completamente
6. Entrega: `POST /api/tickets/<ticket_id>/deliver` (item_id, qty)
7. Actualización: `delivered_qty` incrementa, estado cambia a 'partial' o 'delivered'

**Endpoints QR existentes:**
- `POST /scanner/api/tickets/scan` - Escanear ticket
- `POST /scanner/api/tickets/<ticket_id>/deliver` - Entregar item
- `GET /scanner/api/tickets/<ticket_id>` - Consultar ticket

**Logs de auditoría:**
- `DeliveryLog` registra todos los escaneos y entregas
- Campos: `action`, `bartender_user_id`, `ip_address`, `user_agent`

### Qué Sirve para QR/Wallet

**Ya implementado:**
- ✅ Sistema de tickets QR funcional
- ✅ Generación automática de QR en ventas
- ✅ Escaneo y validación de tickets
- ✅ Estados de entrega (open, partial, delivered)
- ✅ Logs de auditoría completos
- ✅ Hash de integridad para validación

**Falta para QR único multi-propósito:**
- ❌ QR no se usa para entrada (solo para barra)
- ❌ QR no se usa para guardarropía (sistema separado)
- ❌ QR no se usa para puntos/recompensas
- ❌ No hay wallet digital de clientes

**Falta para wallet:**
- ❌ No hay modelo `Customer` o `Wallet`
- ❌ No hay sistema de saldo/crédito
- ❌ No hay historial de transacciones de wallet
- ❌ No hay recarga de wallet

---

## 4) BASE DE DATOS

### Tablas Existentes Relevantes

**Ventas y Transacciones:**
- `pos_sales` - Ventas principales
- `pos_sale_items` - Items de venta
- `payment_intents` - Intenciones de pago (GETNET/KLAP)
- `payment_agents` - Agentes de pago locales
- `log_intento_pago` - Logs de intentos de pago

**Tickets y Entregas:**
- `ticket_entregas` - Tickets QR de entrega
- `ticket_entrega_items` - Items de ticket
- `delivery_logs` - Logs de escaneo/entrega
- `deliveries` - Entregas registradas (legacy)
- `fraud_attempts` - Intentos de fraude

**Usuarios y Empleados:**
- `employees` - Empleados (cajeros, bartenders)
- `jornadas` - Turnos/jornadas
- `planilla_trabajador` - Planilla de trabajadores
- `employee_shifts` - Turnos de empleados
- `employee_payments` - Pagos a empleados

**Cajas y Sesiones:**
- `pos_registers` - Cajas/registros
- `register_sessions` - Sesiones de caja (apertura/cierre)
- `register_locks` - Bloqueos de caja
- `register_closes` - Cierres de caja

**Productos e Inventario:**
- `products` - Productos
- `inventory_items` - Items de inventario
- `inventory_stock` - Stock de ingredientes
- `recipes` - Recetas
- `recipe_ingredients` - Ingredientes de recetas

**Guardarropía:**
- `guardarropia_items` - Items guardados
- `guardarropia_tickets` - Tickets QR de guardarropía (similar a entrega)

**Auditoría:**
- `sale_audit_logs` - Logs de auditoría de ventas
- `audit_logs` - Logs generales
- `api_connection_logs` - Logs de conexión API

### Datos Reutilizables para App Móvil

**Productos:**
- `products` tiene: `id`, `name`, `price`, `category`, `is_active`
- Ya existe estructura de productos
- Puede servir para catálogo de app móvil

**Ventas:**
- `pos_sales` tiene: `total_amount`, `payment_type`, `created_at`
- **PERO:** No tiene `customer_id` - no se puede asociar a cliente
- Historial de ventas existe, pero no por cliente

**Tickets QR:**
- `ticket_entregas` tiene: `qr_token`, `sale_id`, `status`
- Sistema QR funcional, puede extenderse para múltiples usos

**Eventos/Jornadas:**
- `jornadas` tiene: `fecha_jornada`, `nombre_fiesta`, `djs`, `estado_apertura`
- Puede servir para mostrar eventos en app móvil

### Entidades que NO Existen

**Clientes:**
- ❌ No hay tabla `customers` o `users`
- ❌ No hay autenticación de clientes
- ❌ No hay perfil de cliente

**Wallet Digital:**
- ❌ No hay tabla `wallets` o `customer_wallets`
- ❌ No hay tabla `wallet_transactions`
- ❌ No hay sistema de saldo/crédito

**Puntos/Recompensas:**
- ❌ No hay tabla `points` o `rewards`
- ❌ No hay sistema de acumulación de puntos
- ❌ No hay catálogo de recompensas

**Entradas con QR:**
- ❌ No hay tabla `entradas` o `tickets_entrada`
- ❌ El sistema QR actual es solo para entregas de barra
- ❌ No hay validación de entrada por QR

**Pagos Rápidos (Klap):**
- ⚠️ `PaymentIntent` existe pero está diseñado para GETNET
- ⚠️ Cliente Klap existe (`app/infrastructure/external/klap_client.py`) pero no integrado
- ❌ No hay flujo de pago rápido tipo Klap para clientes

**Relaciones Cliente-Venta:**
- ❌ No hay `customer_id` en `pos_sales`
- ❌ No hay historial de compras por cliente
- ❌ No hay preferencias de cliente

---

## 5) RIESGOS Y OPORTUNIDADES

### Qué NO Conviene Tocar en Producción

**Sistema de Ventas Core:**
- ⚠️ **NO modificar** `api_create_sale()` sin pruebas exhaustivas
- ⚠️ **NO modificar** validaciones de `RegisterSession` (P0-005)
- ⚠️ **NO modificar** sistema de idempotencia (P0-007)
- ⚠️ **NO modificar** cálculo de inventario (`inventory_applied`)

**Modelos Críticos:**
- ⚠️ **NO modificar** estructura de `PosSale` sin migración cuidadosa
- ⚠️ **NO modificar** `Employee.id` (es inmutable por diseño)
- ⚠️ **NO modificar** `TicketEntrega` sin considerar impacto en barra

**Autenticación:**
- ⚠️ **NO modificar** sistema de autenticación de empleados sin afectar POS
- ⚠️ **NO modificar** sesiones de caja sin afectar ventas activas

**Integraciones Externas:**
- ⚠️ **NO modificar** integración con PHP POS sin validar sincronización
- ⚠️ **NO modificar** flujo de PaymentIntent sin afectar Getnet

### Qué Se Puede Extender Sin Romper

**Nuevas Tablas (Sin Modificar Existentes):**
- ✅ Crear `customers` - No afecta ventas existentes
- ✅ Crear `customer_wallets` - Sistema independiente
- ✅ Crear `wallet_transactions` - Trazabilidad separada
- ✅ Crear `customer_points` - Sistema de puntos nuevo
- ✅ Crear `entrada_tickets` - Sistema de entrada separado

**Nuevos Endpoints API:**
- ✅ Crear `/api/v1/customers/*` - APIs de clientes
- ✅ Crear `/api/v1/wallet/*` - APIs de wallet
- ✅ Crear `/api/v1/entradas/*` - APIs de entrada
- ✅ Extender `/api/tickets/scan` para múltiples propósitos

**Extensión de Modelos Existentes:**
- ✅ Agregar `customer_id` a `PosSale` (nullable, migración segura)
- ✅ Agregar `wallet_payment` a `payment_type` (extensión)
- ✅ Agregar campos opcionales a `TicketEntrega` (sin romper)

**Sistema QR:**
- ✅ Extender `TicketEntrega` para múltiples tipos (entrega, entrada, guardarropía)
- ✅ Agregar campo `ticket_type` ('delivery', 'entry', 'wardrobe')
- ✅ Reutilizar lógica de escaneo existente

### Puntos de Acoplamiento Ideales para la App

**1. API V1 Existente** (`/api/v1/*`)
- Ya tiene rate limiting
- Ya tiene estructura para endpoints públicos
- Endpoints existentes:
  - `/api/v1/public/evento/hoy` - Info de eventos
  - `/api/v1/public/eventos/proximos` - Lista de eventos
  - `/api/v1/bot/responder` - Bot de IA

**Recomendación:** Extender este blueprint para:
- `/api/v1/customers/register` - Registro de cliente
- `/api/v1/customers/login` - Login de cliente (JWT)
- `/api/v1/customers/profile` - Perfil de cliente
- `/api/v1/wallet/balance` - Saldo de wallet
- `/api/v1/wallet/recharge` - Recargar wallet
- `/api/v1/wallet/transactions` - Historial de transacciones
- `/api/v1/entradas/validate` - Validar entrada por QR
- `/api/v1/tickets/my-tickets` - Tickets del cliente

**2. Sistema de Tickets QR**
- `TicketEntrega` ya tiene estructura completa
- `TicketEntregaService` ya tiene lógica de escaneo
- Endpoints de escaneo ya existen

**Recomendación:** 
- Extender `TicketEntrega` con `ticket_type` y `customer_id`
- Reutilizar `TicketEntregaService.scan_ticket()` para múltiples propósitos
- Agregar validación de entrada en el mismo flujo

**3. PaymentIntent**
- Ya existe modelo `PaymentIntent` para pagos
- Estados: CREATED → READY → IN_PROGRESS → APPROVED/DECLINED
- Ya tiene integración con agente local (Getnet)

**Recomendación:**
- Extender para soportar wallet payments
- Agregar `payment_method = 'wallet'` en `PosSale`
- Crear `PaymentIntent` para pagos con wallet (sin agente externo)

**4. Sistema de Productos**
- `products` ya tiene estructura completa
- Ya existe catálogo de productos

**Recomendación:**
- Exponer `/api/v1/products` (público o autenticado)
- Filtrar por `is_active = True`
- Incluir categorías y precios

**5. Sistema de Eventos**
- `jornadas` ya tiene información de eventos
- Ya existe endpoint `/api/v1/public/evento/hoy`

**Recomendación:**
- Extender para incluir más detalles
- Agregar imágenes, descripciones
- Agregar venta de entradas desde app

### Arquitectura Recomendada para Integración

**Capa de API Nueva (Sin Tocar Existente):**
```
/api/v1/
├── customers/          # Registro, login, perfil
├── wallet/            # Saldo, recarga, transacciones
├── entradas/          # Compra y validación de entradas
├── tickets/           # Tickets del cliente (extender existente)
├── products/          # Catálogo (exponer existente)
└── payments/          # Pagos rápidos (extender PaymentIntent)
```

**Nuevas Tablas (Sin Modificar Existentes):**
```
customers              # Clientes de la app
customer_wallets       # Wallets de clientes
wallet_transactions    # Transacciones de wallet
customer_points        # Puntos de clientes
entrada_tickets        # Tickets de entrada (extender TicketEntrega)
customer_sales         # Relación cliente-venta (agregar customer_id a pos_sales)
```

**Autenticación para App:**
- Implementar JWT (nuevo, no tocar autenticación de empleados)
- Endpoint: `POST /api/v1/customers/login`
- Token en header: `Authorization: Bearer <token>`
- Refresh tokens para renovación

**Integración con Adalo:**
- Adalo puede consumir APIs REST existentes
- Usar `/api/v1/*` como base
- Autenticación JWT compatible
- Webhooks para notificaciones (nuevo endpoint)

---

## RESUMEN EJECUTIVO

### Compatibilidad Actual

**✅ Compatible:**
- Sistema QR funcional (puede extenderse)
- APIs REST existentes (estructura lista)
- Sistema de productos (catálogo disponible)
- Sistema de eventos (info disponible)
- PaymentIntent (puede extenderse para wallet)

**❌ No Compatible (Requiere Desarrollo):**
- Modelo de Cliente (no existe)
- Wallet Digital (no existe)
- Autenticación de Clientes (no existe)
- QR Multi-propósito (solo entrega actualmente)
- Pagos Rápidos Klap (cliente existe pero no integrado)
- Historial de Cliente (no hay relación cliente-venta)

### Riesgo de Implementación

**Bajo Riesgo:**
- Crear nuevas tablas (customers, wallets)
- Crear nuevos endpoints API
- Extender modelos existentes (agregar campos nullable)
- Implementar JWT para clientes

**Medio Riesgo:**
- Agregar `customer_id` a `pos_sales` (requiere migración)
- Extender `TicketEntrega` para múltiples tipos
- Integrar pagos con wallet en flujo de ventas

**Alto Riesgo:**
- Modificar flujo de ventas existente
- Modificar autenticación de empleados
- Modificar sistema de inventario
- Modificar integración PHP POS

### Recomendación Final

**Estrategia de Extensión Segura:**
1. Crear sistema de clientes completamente nuevo (tablas nuevas)
2. Extender APIs existentes sin modificar lógica core
3. Agregar `customer_id` a ventas de forma opcional (nullable)
4. Reutilizar sistema QR existente extendiéndolo
5. Implementar wallet como sistema independiente
6. Integrar con Adalo vía APIs REST estándar

**No tocar:**
- Lógica de ventas core
- Autenticación de empleados
- Sistema de cajas y sesiones
- Integración PHP POS


