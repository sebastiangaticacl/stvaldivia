# 🖨️ ESTRATEGIA DE MANEJO DE IMPRESORAS POR TPV

**Fecha:** 2025-12-17  
**Objetivo:** Sistema de configuración de impresoras por TPV (Terminal Punto de Venta)

---

## 📋 SITUACIÓN ACTUAL

### Sistema de Impresión Existente

- ✅ `TicketPrinterService` - Servicio de impresión funcional
- ✅ Soporte para Windows, macOS y Linux
- ✅ Impresión de tickets con código de barras/QR
- ✅ Apertura de cajón de dinero
- ⚠️ Configuración global única (`TICKET_PRINTER_NAME`)

### Limitaciones Actuales

- ❌ No se puede configurar impresora diferente por TPV
- ❌ Todos los TPV usan la misma impresora
- ❌ No hay gestión de múltiples impresoras

---

## 🎯 PROPUESTA DE SOLUCIÓN

### Arquitectura Propuesta

```
TPV (PosRegister)
  └─ printer_config (JSON)
      ├─ printer_name: "Impresora Barra Principal"
      ├─ printer_type: "thermal" | "inkjet" | "laser"
      ├─ auto_print: true/false
      ├─ print_items: true/false
      ├─ print_total: true/false
      ├─ paper_width: 80 (mm)
      └─ open_drawer: true/false
```

### Flujo de Impresión Mejorado

```
Venta creada → Obtener TPV → Leer printer_config → 
  → Si auto_print: true → Imprimir con impresora del TPV
  → Si auto_print: false → No imprimir automáticamente
```

---

## 🏗️ IMPLEMENTACIÓN

### 1. Modelo de Configuración

**Campo existente:** `PosRegister.printer_config` (JSON)

**Estructura JSON:**
```json
{
  "printer_name": "Impresora Barra Principal",
  "printer_type": "thermal",
  "auto_print": true,
  "print_items": true,
  "print_total": true,
  "print_barcode": true,
  "paper_width": 80,
  "open_drawer": true,
  "cut_paper": true
}
```

### 2. Servicio de Impresión Mejorado

**Modificar:** `TicketPrinterService`

- ✅ Aceptar configuración de impresora desde TPV
- ✅ Usar `printer_name` del TPV si está configurado
- ✅ Fallback a impresora por defecto si no hay configuración

### 3. Interfaz de Administración

**Crear:** Panel de configuración de impresoras

- ✅ Listar impresoras disponibles del sistema
- ✅ Configurar impresora por TPV
- ✅ Probar impresión desde el panel
- ✅ Ver estado de impresoras

### 4. Integración con Ventas

**Modificar:** `api_create_sale` en `sales.py`

- ✅ Obtener configuración de impresora del TPV
- ✅ Usar configuración para imprimir ticket
- ✅ Respetar `auto_print: false` si está desactivado

---

## 📊 ESTRUCTURA DE DATOS

### Configuración de Impresora (JSON)

```typescript
interface PrinterConfig {
  printer_name: string | null;      // Nombre de la impresora del sistema
  printer_type: 'thermal' | 'inkjet' | 'laser' | 'default';
  auto_print: boolean;               // Imprimir automáticamente al crear venta
  print_items: boolean;              // Imprimir lista de items
  print_total: boolean;              // Imprimir total
  print_barcode: boolean;            // Imprimir código de barras
  paper_width: number;               // Ancho de papel en mm (80, 58, etc.)
  open_drawer: boolean;              // Abrir cajón de dinero
  cut_paper: boolean;                // Cortar papel después de imprimir
}
```

### Valores por Defecto

```json
{
  "printer_name": null,
  "printer_type": "thermal",
  "auto_print": true,
  "print_items": true,
  "print_total": true,
  "print_barcode": true,
  "paper_width": 80,
  "open_drawer": true,
  "cut_paper": true
}
```

---

## 🔄 FLUJO DE TRABAJO

### 1. Configuración Inicial

```
Admin → Panel Control → Administración de TPV → Editar TPV
  ├─ Sección: Configuración de Impresora
  ├─ Listar impresoras disponibles del sistema
  ├─ Seleccionar impresora
  ├─ Configurar opciones (auto_print, paper_width, etc.)
  └─ Guardar configuración
```

### 2. Impresión Automática

```
Cajero → Crear Venta → Sistema verifica TPV
  ├─ Lee printer_config del TPV
  ├─ Si auto_print: true → Imprime automáticamente
  ├─ Si auto_print: false → No imprime (cajero puede imprimir manualmente)
  └─ Usa printer_name del TPV o impresora por defecto
```

### 3. Impresión Manual

```
Cajero → Ver Venta → Botón "Imprimir Ticket"
  ├─ Obtiene configuración del TPV
  ├─ Imprime con impresora configurada
  └─ Respeta todas las opciones de configuración
```

---

## 🛠️ COMPONENTES A CREAR/MODIFICAR

### Nuevos Archivos

1. **`app/helpers/printer_helper.py`**
   - Función para listar impresoras disponibles
   - Función para obtener configuración de impresora del TPV
   - Validación de configuración

2. **`app/templates/admin/registers/printer_config.html`**
   - Formulario de configuración de impresora
   - Lista de impresoras disponibles
   - Opciones de impresión

### Archivos a Modificar

1. **`app/infrastructure/services/ticket_printer_service.py`**
   - Aceptar configuración de impresora
   - Usar `printer_name` del TPV
   - Respetar opciones de configuración

2. **`app/blueprints/pos/views/sales.py`**
   - Obtener configuración del TPV al crear venta
   - Pasar configuración al servicio de impresión

3. **`app/routes/register_admin_routes.py`**
   - Agregar ruta para configurar impresora
   - Endpoint para listar impresoras disponibles

4. **`app/templates/admin/registers/form.html`**
   - Sección de configuración de impresora

---

## 📝 CASOS DE USO

### Caso 1: TPV "Barra Principal" - Impresora Térmica

```
Configuración:
  - printer_name: "TM-T20"
  - printer_type: "thermal"
  - auto_print: true
  - paper_width: 80
  - open_drawer: true
```

### Caso 2: TPV "Puerta" - Sin Impresión Automática

```
Configuración:
  - printer_name: null (usa impresora por defecto)
  - auto_print: false
  - print_items: true
  - print_total: true
```

### Caso 3: TPV "Kiosko" - Impresora de Recibos

```
Configuración:
  - printer_name: "HP LaserJet"
  - printer_type: "laser"
  - auto_print: true
  - paper_width: 210 (A4)
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear helper para gestión de impresoras
- [ ] Modificar TicketPrinterService para aceptar configuración
- [ ] Agregar sección de impresora en formulario de TPV
- [ ] Crear endpoint para listar impresoras disponibles
- [ ] Modificar api_create_sale para usar configuración del TPV
- [ ] Crear interfaz de prueba de impresión
- [ ] Documentar configuración

---

## 🔍 DETALLES TÉCNICOS

### Listar Impresoras Disponibles

**Windows:**
```python
wmic printer get name
```

**macOS:**
```python
lpstat -p
```

**Linux:**
```python
lpstat -p -d
```

### Validación de Configuración

- Verificar que `printer_name` existe en el sistema
- Validar `paper_width` (valores comunes: 58, 80, 110 mm)
- Validar `printer_type` (valores permitidos)

---

**Última actualización:** 2025-12-17

