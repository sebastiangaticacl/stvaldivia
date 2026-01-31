# 💳 ESTRATEGIA DE PAGOS BIMBA - GETNET + KLAP

**Fecha:** 2025-01-15  
**Decisión:** GETNET Principal + KLAP Backup  
**Objetivo:** Minimizar fricción operativa y garantizar continuidad de servicio

---

## 🏗️ ARQUITECTURA BIMBA (CRÍTICO)

### POS Propio (BIMBAVERSO) = Fuente de Verdad
- **Todas las ventas** se registran en nuestro POS propio
- **Inventario** se descuenta desde nuestro sistema
- **Catálogo** y productos están en nuestro sistema
- **GETNET/KLAP NO manejan ventas**, solo procesan pagos

### GETNET/KLAP = Procesadores de Pago
- **Solo procesan** la transacción de pago (captura y confirmación)
- **NO manejan** catálogo, inventario ni ventas "oficiales"
- Se registran en la venta como `payment_provider` para:
  - Conciliación
  - Reportes
  - Fallback tracking

### Separación: Método vs Proveedor
- **payment_method**: Forma de pago (cash, debit, credit, transfer, prepaid, qr)
- **payment_provider**: Procesador (GETNET, KLAP, NONE)
- Ejemplos:
  - Efectivo: `method=cash`, `provider=NONE`
  - Débito GETNET: `method=debit`, `provider=GETNET`
  - Débito fallback KLAP: `method=debit`, `provider=KLAP`

---

## 📋 DECISIÓN ESTRATÉGICA

### Provider Principal: GETNET
- **Razón:** Estabilidad operativa probada (25.4% mercado Chile)
- **Infraestructura:** Banco Santander (alta disponibilidad)
- **Soporte:** 24/7 con técnicos locales
- **Ideal para:** Totem, Cajas Humanas, Caja Virtual

### Provider Backup: KLAP (Tap On Phone)
- **Razón:** Sin costo de hardware adicional (usa celulares existentes)
- **Activación rápida:** < 60 segundos cuando falla GETNET
- **Ideal para:** Fallback operativo, eventos especiales, cajas temporales

### Estrategia: GETNET_PRIMARY_KLAP_BACKUP
- **Objetivo:** Cambiar a KLAP en < 60 segundos cuando falla GETNET
- **Meta:** 0% pérdida de ventas por fallas técnicas

---

## 🗂️ QUÉ CAJAS USAN QUÉ

| Tipo de Caja | Provider Principal | Provider Backup | Notas |
|--------------|-------------------|-----------------|-------|
| **TOTEM** (LUNA 1, LUNA 2, TERRAZA) | GETNET | KLAP (manual) | Backup operativo manual, no integrado aún |
| **HUMANA** (PUERTA, PISTA) | GETNET | KLAP | Backup recomendado y operativo |
| **OFICINA** (Cortesías) | GETNET | KLAP | Backup recomendado |
| **VIRTUAL** (Precompra/QR) | GETNET | - | Integración real en fase posterior |

---

## 🚨 PROCEDIMIENTO: FALLA GETNET

### Objetivo
Cambiar a KLAP en **< 60 segundos** sin perder ventas.

### Pasos para Cajero (Bullets)

1. **Detectar falla:**
   - Terminal GETNET no responde
   - Error en pantalla del terminal
   - Cliente esperando en fila

2. **Registrar venta en POS propio (BIMBAVERSO):**
   - **IMPORTANTE:** Primero registrar la venta en nuestro POS
   - Seleccionar productos, confirmar venta
   - **Inventario se descuenta automáticamente**
   - Seleccionar método de pago: débito/crédito
   - **Seleccionar provider: KLAP** (en lugar de GETNET)

3. **Procesar pago con KLAP:**
   - Tomar celular con app KLAP instalada (debe estar cargado y con datos móviles)
   - Abrir app KLAP
   - Ingresar monto de la venta
   - Presentar celular al cliente para pago sin contacto
   - Cliente acerca tarjeta/celular al celular
   - Confirmar pago exitoso en app KLAP

4. **Confirmar venta en POS:**
   - Confirmar que el pago fue exitoso
   - La venta queda registrada con `payment_provider=KLAP`
   - Continuar con siguiente cliente

5. **Registrar fallback:**
   - Anotar hora y razón de falla
   - Continuar operando con KLAP hasta que GETNET se recupere
   - Todas las ventas durante fallback se registran con `provider=KLAP`

6. **Volver a GETNET cuando se recupere:**
   - Probar terminal GETNET con venta pequeña
   - Si funciona, volver a usar GETNET
   - Registrar fin del fallback
   - Nuevas ventas se registran con `provider=GETNET`

### Tiempo Objetivo: < 60 segundos

### ⚠️ CRÍTICO: Flujo Correcto
1. **Venta primero** en POS propio (inventario se descuenta)
2. **Pago después** con GETNET/KLAP
3. **Provider se registra** en la venta para conciliación

---

## 🌐 PROCEDIMIENTO: FALLA INTERNET

### Escenario 1: WiFi Falló, Datos Móviles Disponibles

**Acción:**
- Cambiar celular KLAP a datos móviles
- Continuar operando con KLAP
- GETNET puede funcionar con datos móviles si el terminal tiene SIM

**Checklist:**
- [ ] Verificar que celular tiene datos móviles activos
- [ ] Cambiar WiFi a datos móviles en app KLAP
- [ ] Probar una transacción pequeña
- [ ] Continuar operando normalmente

### Escenario 2: Sin Internet (WiFi + Datos Fallaron)

**Acción:**
- **GETNET:** Algunos terminales tienen modo offline limitado (verificar con GETNET)
- **KLAP:** No funciona sin internet
- **Fallback:** Aceptar solo efectivo temporalmente

**Checklist:**
- [ ] Informar a clientes que solo se acepta efectivo temporalmente
- [ ] Registrar incidente en sistema
- [ ] Contactar soporte técnico GETNET
- [ ] Verificar con proveedor de internet

---

## ✅ CHECKLIST DE INICIO DE TURNO

### Antes de Abrir Cajas

**GETNET:**
- [ ] Terminal encendido y conectado
- [ ] Probar transacción de prueba ($1.000)
- [ ] Verificar que terminal responde correctamente
- [ ] Confirmar conexión a red (WiFi o datos)

**KLAP (Backup):**
- [ ] Verificar que hay **mínimo 2 celulares** con app KLAP instalada
- [ ] Verificar que celulares tienen **batería > 50%**
- [ ] Verificar que celulares tienen **NFC habilitado**
- [ ] Verificar que celulares tienen **datos móviles activos** (o WiFi estable)
- [ ] Probar transacción de prueba con KLAP ($1.000)
- [ ] Confirmar que cargadores están disponibles

**Infraestructura:**
- [ ] WiFi funcionando (verificar con ping o navegación web)
- [ ] Datos móviles activos en celulares backup
- [ ] Cargadores disponibles cerca de cajas

### Si Algo Falla en Checklist

**NO ABRIR CAJAS** hasta resolver:
- Si GETNET no funciona → Usar solo KLAP (si está listo)
- Si KLAP no está listo → Esperar hasta tener mínimo 2 celulares listos
- Si no hay internet → Contactar soporte antes de abrir

---

## 🔒 CHECKLIST DE CIERRE DE TURNO

### Al Cerrar Sesión de Caja

**Registrar en Sistema:**
- [ ] Total de transacciones con GETNET (provider principal)
- [ ] Total de transacciones con KLAP (provider backup)
- [ ] Número de eventos de fallback (si aplica)
- [ ] Razones de fallback (pos_offline, pos_error, etc.)

**Revisar Fallback Events:**
- [ ] ¿Cuántas veces se cambió a KLAP?
- [ ] ¿Cuánto tiempo duró cada fallback?
- [ ] ¿Se perdió alguna venta por fallas técnicas?

**Reportar Incidentes:**
- [ ] Si hubo fallas frecuentes de GETNET → Reportar a soporte GETNET
- [ ] Si hubo problemas con KLAP → Revisar configuración de celulares
- [ ] Si hubo problemas de internet → Contactar proveedor de internet

---

## 📊 CONFIGURACIÓN POR CAJA

### TOTEM (Autoatención)

**Configuración:**
```json
{
  "payment_provider_primary": "GETNET",
  "payment_provider_backup": "KLAP",
  "fallback_policy": {
    "enabled": true,
    "trigger_events": ["pos_offline", "pos_error"],
    "max_switch_time_seconds": 60,
    "backup_devices_required": 2,
    "operational_mode": "manual"
  }
}
```

**Nota:** Backup operativo manual (no integrado aún). Si falla GETNET, operador debe activar KLAP manualmente.

### HUMANA (Cajero)

**Configuración:**
```json
{
  "payment_provider_primary": "GETNET",
  "payment_provider_backup": "KLAP",
  "fallback_policy": {
    "enabled": true,
    "trigger_events": ["pos_offline", "pos_error", "printer_error_optional"],
    "max_switch_time_seconds": 60,
    "backup_devices_required": 2
  }
}
```

**Recomendado:** Backup KLAP operativo. Cajero debe tener celular con app KLAP lista.

### OFICINA (Cortesías)

**Configuración:**
```json
{
  "payment_provider_primary": "GETNET",
  "payment_provider_backup": "KLAP",
  "fallback_policy": {
    "enabled": true,
    "trigger_events": ["pos_offline", "pos_error"],
    "max_switch_time_seconds": 60,
    "backup_devices_required": 1
  }
}
```

**Nota:** Menor flujo, 1 celular backup puede ser suficiente.

### VIRTUAL (Precompra/QR)

**Configuración:**
```json
{
  "payment_provider_primary": "GETNET",
  "payment_provider_backup": null,
  "fallback_policy": {
    "enabled": false
  }
}
```

**Nota:** Integración real con GETNET API en fase posterior. Por ahora solo configuración.

---

## 📱 REQUISITOS KLAP (Backup)

### Celulares Mínimos Requeridos

**Por Tipo de Caja:**
- **TOTEM:** 2 celulares (backup operativo manual)
- **HUMANA:** 2 celulares (backup operativo)
- **OFICINA:** 1 celular (menor flujo)
- **VIRTUAL:** No aplica

### Especificaciones Mínimas

- **Sistema Operativo:** Android 8+ o iOS 12+
- **NFC:** Habilitado y funcionando
- **Batería:** Mínimo 50% al inicio de turno
- **Datos Móviles:** Plan activo con datos disponibles
- **App KLAP:** Instalada y configurada con cuenta de comercio

### Checklist de Celular Backup

Antes de cada turno:
- [ ] App KLAP instalada y actualizada
- [ ] Cuenta de comercio configurada
- [ ] NFC habilitado en configuración
- [ ] Datos móviles activos (o WiFi estable)
- [ ] Batería > 50%
- [ ] Cargador disponible cerca

---

## 🔄 FLUJO DE FALLBACK (Operativo)

### 1. Detección de Falla

**Eventos que activan fallback:**
- `pos_offline`: Terminal GETNET no responde
- `pos_error`: Error en terminal GETNET
- `printer_error_optional`: Impresora falló (opcional, solo si es crítico)
- `network_error`: Problema de red (si GETNET requiere internet)

### 2. Activación de Backup

**Tiempo objetivo:** < 60 segundos

**Pasos:**
1. Cajero detecta falla
2. Toma celular con app KLAP
3. Abre app y procesa pago
4. Continúa operando con KLAP

### 3. Registro de Fallback

**En Sistema:**
```json
{
  "timestamp": "2025-01-15T22:30:00",
  "reason": "pos_offline",
  "from_provider": "GETNET",
  "to_provider": "KLAP",
  "handled_by_user_id": "cajero123"
}
```

### 4. Recuperación

**Cuando GETNET se recupera:**
1. Probar terminal GETNET con transacción pequeña
2. Si funciona, volver a usar GETNET
3. Registrar fin del fallback
4. Continuar operando normalmente

---

## 📞 CONTACTOS DE SOPORTE

### GETNET (Banco Santander)
- **Teléfono:** [Agregar número de soporte GETNET]
- **Horario:** 24/7
- **Email:** [Agregar email de soporte]
- **Para:** Fallas de terminal, problemas de conexión, errores de transacción

### KLAP
- **Teléfono:** [Agregar número de soporte KLAP]
- **Horario:** [Agregar horario]
- **Email:** [Agregar email de soporte]
- **Para:** Problemas con app, configuración de cuenta, errores de pago

### Internet/Red
- **Proveedor WiFi:** [Agregar proveedor y contacto]
- **Proveedor Datos Móviles:** [Agregar proveedor y contacto]

---

## 📈 MÉTRICAS Y MONITOREO

### Métricas a Monitorear

**Por Sesión de Caja:**
- `payment_provider_used_primary_count`: Transacciones con GETNET
- `payment_provider_used_backup_count`: Transacciones con KLAP
- `fallback_events`: Número de veces que se activó fallback

**Objetivos:**
- **Tasa de fallback:** < 5% de transacciones en backup
- **Tiempo de cambio:** < 60 segundos promedio
- **Pérdida de ventas:** 0% por fallas técnicas

### Reportes

**Diario:**
- Total de transacciones por provider
- Número de fallbacks
- Razones de fallback más comunes

**Semanal:**
- Tendencias de fallas
- Efectividad del backup
- Tiempo promedio de cambio

---

## ⚠️ NOTAS IMPORTANTES

1. **No implementación real aún:** Esta documentación describe la estrategia operativa. La integración real con GETNET/KLAP APIs será en fase posterior.

2. **Backup manual por ahora:** El cambio a KLAP es manual. La automatización vendrá con la integración real.

3. **Trazabilidad:** Todos los fallbacks se registran en `RegisterSession.fallback_events` para auditoría.

4. **Capacitación:** Todos los cajeros deben estar capacitados en uso de KLAP antes de operar.

5. **Pruebas regulares:** Probar fallback al menos una vez por semana para mantener habilidades.

---

## 🔄 ACTUALIZACIONES

**Versión 1.0** (2025-01-15)
- Estrategia inicial GETNET + KLAP
- Procedimientos operativos básicos
- Checklists de inicio/cierre

**Próximas actualizaciones:**
- Integración real con APIs
- Automatización de fallback
- Métricas avanzadas

---

**Documento operativo BIMBA - Pagos Low Friction**

