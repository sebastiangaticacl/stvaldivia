# 🖥️ GUÍA DE ACCESO: Punto de Venta (POS) BIMBA

**Fecha:** 2025-01-15  
**Sistema:** BIMBAVERSO (POS Propio)

---

## 🌐 URL BASE DEL SERVICIO

### Producción (stvaldivia.cl)
```
https://stvaldivia.cl/caja
```

**Nota:** `/caja` redirige automáticamente a `/caja/login`

### Desarrollo Local
```
http://localhost:5001/caja
```

---

## 🔐 FLUJO DE ACCESO DESDE UN PUNTO DE VENTA

### Paso 1: Login del Cajero

**URL:** `https://stvaldivia.cl/caja/login`  
**Alternativa:** `https://stvaldivia.cl/caja` (redirige automáticamente a login)

**Método:** GET (pantalla) o POST (autenticación)

**Proceso:**
1. Abrir navegador en el dispositivo POS
2. Ir a `https://stvaldivia.cl/caja/login`
3. Ingresar PIN del empleado (o usuario admin)
4. Seleccionar caja disponible

**Autenticación:**
- **PIN de empleado:** Se valida contra PHP POS API (si está configurada)
- **Admin:** Si tienes sesión admin activa, puedes acceder directamente

**Resultado:**
- Sesión creada (`pos_logged_in = True`)
- Variables de sesión:
  - `pos_employee_id`
  - `pos_employee_name`
  - `pos_register_id`
  - `pos_register_name`
  - `pos_register_session_id` (si hay sesión activa)

---

### Paso 2: Seleccionar Caja (si no se seleccionó en login)

**URL:** `https://stvaldivia.cl/caja/register`

**Método:** GET (pantalla) o POST (selección)

**Proceso:**
1. Ver lista de cajas disponibles
2. Seleccionar caja (ej: CAJA-01, CAJA-02)
3. Verificar que la caja no esté bloqueada por otro cajero
4. Si hay sesión activa, se asocia automáticamente

**Resultado:**
- `pos_register_id` guardado en sesión
- Redirección a `/caja/ventas`

---

### Paso 3: Abrir Sesión de Caja (Opcional pero Recomendado)

**URL:** `https://stvaldivia.cl/caja/session/open`

**Método:** GET (formulario) o POST (abrir)

**Proceso:**
1. Seleccionar caja
2. Ingresar fondo inicial (opcional)
3. Seleccionar jornada/turno (si aplica)
4. Confirmar apertura

**Resultado:**
- `RegisterSession` creada con estado `OPEN`
- `pos_register_session_id` guardado en sesión
- Trazabilidad: todas las ventas se asocian a esta sesión

---

### Paso 4: Pantalla Principal de Ventas

**URL:** `https://stvaldivia.cl/caja/ventas`

**Método:** GET

**Requisitos:**
- `pos_logged_in = True`
- `pos_register_id` definido
- Caja no bloqueada por otro cajero

**Funcionalidades:**
- Agregar productos al carrito
- Ver carrito actual
- Calcular total
- Procesar venta
- Imprimir ticket

---

## 📡 APIs DISPONIBLES PARA EL POS

### Base URL
```
https://stvaldivia.cl/caja/api
```

### Endpoints Principales

#### 1. Carrito

**Agregar producto:**
```
POST /caja/api/cart/add
Content-Type: application/json

{
  "item_id": "123",
  "quantity": 2,
  "price": 5000
}
```

**Remover producto:**
```
POST /caja/api/cart/remove
Content-Type: application/json

{
  "item_id": "123",
  "quantity": 1
}
```

**Limpiar carrito:**
```
POST /caja/api/cart/clear
```

**Obtener carrito:**
```
GET /caja/api/cart
```

#### 2. Validación de Stock

**Validar stock antes de venta:**
```
POST /caja/api/stock/validate
Content-Type: application/json

{
  "cart": [
    {"item_id": "123", "quantity": 2}
  ],
  "register_id": "CAJA-01"
}
```

#### 3. Crear Venta

**Crear venta (CRÍTICO):**
```
POST /caja/api/sale/create
Content-Type: application/json

{
  "cart": [
    {
      "item_id": "123",
      "quantity": 2,
      "price": 5000,
      "name": "Producto"
    }
  ],
  "payment_type": "debit",
  "payment_provider": "GETNET",
  "register_id": "CAJA-01",
  "total": 10000
}
```

**Campos importantes:**
- `payment_type`: `cash`, `debit`, `credit`, `transfer`, `prepaid`, `qr`
- `payment_provider`: `GETNET`, `KLAP`, `NONE` (para efectivo)
- `register_id`: ID de la caja
- `register_session_id`: (opcional) ID de sesión de caja si existe

**Respuesta exitosa:**
```json
{
  "success": true,
  "sale_id": 12345,
  "message": "Venta creada exitosamente",
  "inventory_applied": true
}
```

#### 4. Cancelar Venta

```
POST /caja/api/sale/<sale_id>/cancel
Content-Type: application/json

{
  "reason": "Cliente canceló",
  "cancelled_by": "Cajero123"
}
```

#### 5. Productos

**Obtener productos disponibles:**
```
GET /caja/api/products
```

**Parámetros:**
- `category`: Filtrar por categoría
- `search`: Búsqueda por nombre

---

## 🔄 FLUJO COMPLETO DE UNA VENTA

### 1. Login y Selección de Caja
```
GET /caja/login → POST /caja/login → GET /caja/register → POST /caja/register
```

### 2. Abrir Sesión (Recomendado)
```
GET /caja/session/open → POST /caja/session/open
```

### 3. Agregar Productos al Carrito
```
POST /caja/api/cart/add (múltiples veces)
```

### 4. Validar Stock (Opcional)
```
POST /caja/api/stock/validate
```

### 5. Procesar Pago y Crear Venta
```
POST /caja/api/sale/create
{
  "cart": [...],
  "payment_type": "debit",
  "payment_provider": "GETNET",
  "total": 15000
}
```

**IMPORTANTE:**
- La venta se registra en `pos_sales` (nuestro sistema)
- El inventario se descuenta automáticamente
- `payment_provider` se guarda para conciliación
- Si hay `register_session_id`, se asocia a la sesión

### 6. Procesar Pago con GETNET/KLAP
- **Fuera del sistema:** Procesar pago físico con terminal GETNET o app KLAP
- **Dentro del sistema:** Solo registrar `payment_provider` en la venta

### 7. Imprimir Ticket (Opcional)
```
GET /caja/ticket/<ticket_id>/print
```

---

## 🚪 CERRAR SESIÓN DE CAJA

**URL:** `https://stvaldivia.cl/caja/session/close`

**Método:** GET (formulario) o POST (cerrar)

**Proceso:**
1. Ingresar conteo de efectivo (arqueo)
2. Revisar totales calculados automáticamente:
   - Totales por método (cash/debit/credit)
   - Totales por provider (GETNET/KLAP/NONE)
   - Ticket count
   - Cash difference
3. Ingresar notas de cierre (opcional)
4. Registrar incidentes (opcional)
5. Confirmar cierre

**Resultado:**
- `RegisterSession` cambia a estado `CLOSED`
- Totales guardados en `payment_totals` (JSON)
- Contadores de providers guardados
- Sesión POS limpiada

---

## 🔒 AUTENTICACIÓN Y SEGURIDAD

### Variables de Sesión Requeridas

Para acceder a rutas del POS, se requiere:

```python
session.get('pos_logged_in') == True
session.get('pos_register_id')  # ID de caja seleccionada
session.get('pos_employee_id')  # ID del empleado
```

### Protección de Rutas

Todas las rutas del POS verifican:
- `pos_logged_in` activo
- `pos_register_id` definido
- Caja no bloqueada por otro cajero
- Sesión no expirada (timeout configurable)

### Rate Limiting

Algunas APIs tienen rate limiting:
- `/api/sale/create`: 30 ventas por minuto
- `/api/stock/validate`: 60 requests por minuto

---

## 📱 DISPOSITIVOS SOPORTADOS

### Navegadores Recomendados
- Chrome/Chromium (recomendado)
- Firefox
- Safari (iOS)
- Edge

### Dispositivos
- Tablets Android/iOS
- Computadoras de escritorio
- Pantallas táctiles
- Kioscos

### Requisitos
- JavaScript habilitado
- Cookies habilitadas
- Conexión a internet estable
- Resolución mínima: 1024x768 (recomendado: 1920x1080)

---

## 🔧 CONFIGURACIÓN PARA ACCESO DESDE DISPOSITIVO POS

### 1. Configurar URL Base

En el dispositivo POS, configurar URL base:
```
https://stvaldivia.cl/caja
```

### 2. Crear Acceso Directo

**Chrome/Chromium (Android/iOS):**
1. Abrir `https://stvaldivia.cl/caja/login`
2. Menú → "Agregar a pantalla de inicio"
3. Nombre: "POS BIMBA"

**Windows:**
1. Crear acceso directo en escritorio
2. URL: `https://stvaldivia.cl/caja/login`
3. Nombre: "POS BIMBA"

### 3. Modo Kiosco (Opcional)

Para tablets en modo kiosco:
- Usar Chrome en modo kiosco: `chrome --kiosk https://stvaldivia.cl/caja/login`
- O usar aplicación de kiosco que abra la URL

---

## 🐛 TROUBLESHOOTING

### Error: "Por favor, inicia sesión primero"
**Causa:** Sesión expirada o no iniciada  
**Solución:** Ir a `/caja/login` y autenticarse nuevamente

### Error: "Por favor, selecciona una caja primero"
**Causa:** No hay caja seleccionada en sesión  
**Solución:** Ir a `/caja/register` y seleccionar caja

### Error: "Caja bloqueada por otro cajero"
**Causa:** Otro cajero tiene la caja bloqueada  
**Solución:** 
- Esperar a que se desbloquee
- O usar función de desbloqueo (si tienes permisos)

### Error: "No se pudo crear venta"
**Causa:** Validación fallida, stock insuficiente, o error de sistema  
**Solución:** 
- Verificar stock disponible
- Revisar logs del servidor
- Intentar nuevamente

### Error: CORS o conexión rechazada
**Causa:** Problema de red o configuración del servidor  
**Solución:** 
- Verificar que el servidor esté corriendo
- Verificar firewall/red
- Verificar URL base correcta

---

## 📊 EJEMPLO DE INTEGRACIÓN DESDE DISPOSITIVO POS

### JavaScript (Frontend)

```javascript
// Base URL
const BASE_URL = 'https://stvaldivia.cl/caja/api';

// Agregar producto al carrito
async function addToCart(itemId, quantity, price) {
  const response = await fetch(`${BASE_URL}/cart/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // Incluir cookies de sesión
    body: JSON.stringify({
      item_id: itemId,
      quantity: quantity,
      price: price
    })
  });
  return await response.json();
}

// Crear venta
async function createSale(cart, paymentType, paymentProvider) {
  const response = await fetch(`${BASE_URL}/sale/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      cart: cart,
      payment_type: paymentType,
      payment_provider: paymentProvider,
      register_id: sessionStorage.getItem('register_id'),
      register_session_id: sessionStorage.getItem('register_session_id'),
      total: calculateTotal(cart)
    })
  });
  return await response.json();
}
```

---

## ✅ CHECKLIST DE ACCESO DESDE POS

- [ ] Dispositivo conectado a internet
- [ ] Navegador actualizado
- [ ] JavaScript y cookies habilitados
- [ ] URL base configurada: `https://stvaldivia.cl/caja`
- [ ] Login exitoso (`/caja/login`)
- [ ] Caja seleccionada (`/caja/register`)
- [ ] Sesión de caja abierta (opcional pero recomendado)
- [ ] Pantalla de ventas carga (`/caja/ventas`)
- [ ] APIs responden correctamente
- [ ] Ventas se crean exitosamente
- [ ] Inventario se descuenta
- [ ] `payment_provider` se registra correctamente

---

## 📝 NOTAS IMPORTANTES

1. **Sesiones:** Las sesiones del POS son independientes de las sesiones admin
2. **Trazabilidad:** Todas las ventas quedan registradas con `register_id` y `register_session_id`
3. **Inventario:** Se descuenta automáticamente al crear venta
4. **Providers:** GETNET/KLAP solo procesan pagos, no crean ventas
5. **Offline:** El sistema requiere conexión a internet (no hay modo offline aún)

---

**Guía de acceso POS BIMBA** ✅

