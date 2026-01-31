# 🏪 ESTRATEGIA DE MANEJO DE TPV (PUNTOS DE VENTA)

**Fecha:** 2025-12-17  
**Concepto:** TPV = Terminal Punto de Venta = Caja Registradora

---

## 📋 DEFINICIÓN Y CONCEPTOS

### ¿Qué es un TPV en BIMBA?

Un **TPV (Terminal Punto de Venta)** es lo mismo que una **Caja Registradora** (`PosRegister`). Representa un punto físico o lógico donde se realizan ventas.

**Ejemplos de TPV:**
- 🍺 **Barra Principal** - Para ventas de bebidas en la barra
- 🍕 **Puerta** - Para ventas de entradas (solo categoría ENTRADAS)
- 🏖️ **Terraza** - Para ventas en área exterior
- 💎 **VIP** - Para área exclusiva
- 📱 **Kiosko** - Terminal autoservicio (si se implementa)

---

## 🏗️ ARQUITECTURA ACTUAL

### Modelo de Datos

```python
class PosRegister(db.Model):
    """Caja/Register del POS = TPV"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # "Barra Principal"
    code = db.Column(db.String(50), unique=True)  # "BARRA_1"
    is_active = db.Column(db.Boolean, default=True)
    superadmin_only = db.Column(db.Boolean, default=False)
    allowed_categories = db.Column(Text, nullable=True)  # JSON: ["ENTRADAS"]
```

### Componentes Relacionados

1. **PosRegister** - Definición del TPV
2. **RegisterSession** - Sesión activa de un TPV (apertura/cierre)
3. **RegisterLock** - Bloqueo temporal de TPV por usuario
4. **PosSale** - Ventas asociadas a un TPV (`register_id`)

---

## 🔄 FLUJO DE TRABAJO DE UN TPV

### 1. Configuración Inicial (Admin)

```
Admin → Panel Control → Administración de Cajas
  ├─ Crear nuevo TPV
  ├─ Configurar nombre y código
  ├─ Definir categorías permitidas (opcional)
  └─ Activar/Desactivar TPV
```

### 2. Apertura de Sesión (Cajero)

```
Cajero → Seleccionar TPV → Abrir Sesión
  ├─ Validar jornada activa
  ├─ Crear RegisterSession (status: OPEN)
  ├─ Registrar monto inicial (opcional)
  └─ Bloquear TPV para otros usuarios
```

### 3. Operación Normal

```
Cajero → Realizar Ventas
  ├─ Validar sesión abierta
  ├─ Validar categorías permitidas
  ├─ Crear PosSale con register_id
  └─ Aplicar inventario
```

### 4. Cierre de Sesión

```
Cajero → Cerrar Sesión
  ├─ Calcular totales esperados
  ├─ Registrar totales reales
  ├─ Calcular diferencias
  ├─ Cambiar status a CLOSED
  └─ Liberar bloqueo
```

---

## 🎯 FUNCIONALIDADES ACTUALES

### ✅ Implementado

1. **Gestión de TPV**
   - ✅ Crear, editar, eliminar TPV
   - ✅ Activar/Desactivar TPV
   - ✅ Código único por TPV

2. **Restricciones por Categoría**
   - ✅ Filtrar productos por categoría permitida
   - ✅ Ejemplo: "Puerta" solo vende "ENTRADAS"

3. **Sesiones de TPV**
   - ✅ Apertura con validación de jornada
   - ✅ Cierre con cálculo de diferencias
   - ✅ Estados: OPEN, PENDING_CLOSE, CLOSED

4. **Seguridad**
   - ✅ Bloqueo de TPV por usuario
   - ✅ Validación de sesión antes de vender
   - ✅ Restricción superadmin (opcional)

---

## 🚀 PROPUESTA DE MEJORAS

### 1. Nomenclatura Consistente

**Problema:** Se usa "Caja", "Register", "TPV" indistintamente.

**Solución:** Unificar terminología:
- **En código:** `PosRegister` (mantener)
- **En UI:** "Punto de Venta" o "TPV"
- **En documentación:** "TPV" o "Punto de Venta"

### 2. Campos Adicionales para TPV

**Propuesta de nuevos campos:**

```python
class PosRegister(db.Model):
    # ... campos existentes ...
    
    # Nuevos campos propuestos:
    location = db.Column(db.String(200), nullable=True)  # "Barra Principal", "Terraza"
    tpv_type = db.Column(db.String(50), nullable=True)  # "barra", "puerta", "kiosko", "movil"
    printer_config = db.Column(Text, nullable=True)  # JSON: configuración de impresora
    default_location = db.Column(db.String(100), nullable=True)  # Ubicación para inventario
    max_concurrent_sessions = db.Column(db.Integer, default=1)  # Sesiones simultáneas
    requires_cash_count = db.Column(db.Boolean, default=True)  # Requiere conteo de efectivo
```

### 3. Dashboard de TPV

**Propuesta:** Crear dashboard específico para monitoreo de TPV:

```
/admin/tpv/dashboard
  ├─ TPV activos (sesiones abiertas)
  ├─ Ventas por TPV (hoy)
  ├─ TPV inactivos
  └─ Estadísticas por TPV
```

### 4. Tipos de TPV

**Propuesta:** Clasificar TPV por tipo:

- **BARRA** - Para ventas de bebidas/cocteles
- **PUERTA** - Para ventas de entradas
- **TERRAZA** - Para área exterior
- **KIOSKO** - Terminal autoservicio
- **MOVIL** - Tablet/dispositivo móvil
- **VIP** - Área exclusiva

### 5. Configuración de Impresoras por TPV

**Propuesta:** Cada TPV puede tener su impresora configurada:

```python
printer_config = {
    "printer_name": "Impresora Barra",
    "printer_type": "thermal",
    "paper_width": 80,
    "auto_print": True,
    "print_items": True,
    "print_total": True
}
```

---

## 📊 ESTRUCTURA PROPUESTA

### Módulo de Administración de TPV

```
/admin/tpv/
  ├─ /                    # Lista de TPV
  ├─ /crear               # Crear nuevo TPV
  ├─ /<id>/editar         # Editar TPV
  ├─ /<id>/eliminar       # Eliminar TPV
  ├─ /<id>/toggle         # Activar/Desactivar
  ├─ /dashboard           # Dashboard de monitoreo
  └─ /<id>/sesiones       # Historial de sesiones
```

### API de TPV

```
/api/tpv/
  ├─ GET /                # Listar TPV activos
  ├─ GET /<id>            # Detalles de TPV
  ├─ GET /<id>/sesion     # Sesión actual
  ├─ POST /<id>/abrir     # Abrir sesión
  ├─ POST /<id>/cerrar    # Cerrar sesión
  └─ GET /<id>/ventas     # Ventas del TPV
```

---

## 🔍 CASOS DE USO

### Caso 1: TPV "Puerta" (Solo Entradas)

```
1. Admin crea TPV "Puerta" con categoría "ENTRADAS"
2. Cajero abre sesión en "Puerta"
3. Sistema filtra productos: solo muestra ENTRADAS
4. Cajero realiza ventas de entradas
5. Al cerrar, se calculan totales
```

### Caso 2: TPV "Barra Principal" (Todas las Categorías)

```
1. Admin crea TPV "Barra Principal" sin restricciones
2. Cajero abre sesión
3. Sistema muestra TODOS los productos
4. Cajero vende bebidas, cocteles, etc.
5. Inventario se descuenta de ubicación "barra_principal"
```

### Caso 3: Múltiples Sesiones Simultáneas

```
1. TPV "Terraza" permite 2 sesiones simultáneas
2. Cajero A abre sesión 1
3. Cajero B abre sesión 2
4. Ambos pueden vender simultáneamente
5. Al cerrar, se consolidan ventas
```

---

## 🛠️ IMPLEMENTACIÓN RECOMENDADA

### Fase 1: Mejoras Inmediatas (Sin cambios de BD)

1. ✅ Unificar terminología en UI ("Punto de Venta" en lugar de "Caja")
2. ✅ Mejorar dashboard de administración
3. ✅ Agregar estadísticas por TPV

### Fase 2: Campos Adicionales (Con migración)

1. Agregar campo `location` a `PosRegister`
2. Agregar campo `tpv_type` a `PosRegister`
3. Agregar campo `default_location` para inventario

### Fase 3: Funcionalidades Avanzadas

1. Configuración de impresoras por TPV
2. Múltiples sesiones simultáneas
3. Dashboard de monitoreo en tiempo real

---

## 📝 DECISIONES DE DISEÑO

### 1. ¿TPV vs Caja vs Register?

**Decisión:** Mantener `PosRegister` en código, usar "Punto de Venta" o "TPV" en UI.

### 2. ¿Restricciones por Categoría?

**Decisión:** Mantener `allowed_categories` como JSON array. `null` = todas las categorías.

### 3. ¿Sesiones Simultáneas?

**Decisión:** Por defecto 1 sesión por TPV. Permitir múltiples si `max_concurrent_sessions > 1`.

### 4. ¿Inventario por Ubicación?

**Decisión:** Cada TPV puede tener `default_location` para descontar inventario automáticamente.

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [x] Modelo `PosRegister` existente
- [x] Administración básica de TPV
- [x] Restricciones por categoría
- [x] Sesiones de apertura/cierre
- [ ] Dashboard de monitoreo
- [ ] Campos adicionales (location, tpv_type)
- [ ] Configuración de impresoras
- [ ] Múltiples sesiones simultáneas
- [ ] Estadísticas avanzadas

---

## 📚 REFERENCIAS

- **Modelo:** `app/models/pos_models.py::PosRegister`
- **Rutas Admin:** `app/routes/register_admin_routes.py`
- **Sesiones:** `app/models/pos_models.py::RegisterSession`
- **Servicio:** `app/helpers/register_session_service.py`

---

**Última actualización:** 2025-12-17

