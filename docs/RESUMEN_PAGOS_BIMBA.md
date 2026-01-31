# 📋 RESUMEN: Payment Stack BIMBA - GETNET + KLAP

**Fecha:** 2025-01-15  
**Implementación:** Configuración y operación (sin integración real aún)

---

## ✅ ARCHIVOS TOCADOS

### Modelos
- `app/models/pos_models.py`
  - Agregados campos a `PosRegister`: `payment_provider_primary`, `payment_provider_backup`, `provider_config`, `fallback_policy`
  - Agregados campos a `RegisterSession`: `payment_provider_used_primary_count`, `payment_provider_used_backup_count`, `fallback_events`
  - Agregadas constantes: `PROVIDER_GETNET`, `PROVIDER_KLAP`, `STRATEGY_GETNET_PRIMARY_KLAP_BACKUP`

### Migración
- `migrations/add_payment_provider_fields.sql`
  - Agrega columnas de payment providers a `pos_registers`
  - Agrega columnas de tracking a `register_sessions`

### Rutas Admin
- `app/routes/register_admin_routes.py`
  - Procesamiento de campos `payment_provider_primary`, `payment_provider_backup`, `provider_config`, `fallback_policy`
  - Construcción de `fallback_policy` JSON desde campos del formulario
  - Validación de providers (GETNET, KLAP, SUMUP)

### Templates Admin
- `app/templates/admin/registers/form.html`
  - Nueva sección "💳 Pagos (Low Friction) - GETNET + KLAP"
  - Selector provider principal (default GETNET)
  - Selector provider backup (KLAP recomendado)
  - Toggle fallback habilitado
  - Checklist requisitos fallback (NFC, cargadores, datos móviles)
  - Campos: tiempo máximo de cambio, cantidad mínima de celulares backup
  - Campos JSON: provider_config, fallback_policy
  - Validaciones por tipo de caja (TOTEM/HUMANA/OFICINA/VIRTUAL)

### Documentación
- `docs/PAGOS_BIMBA.md` (NUEVO)
  - Decisión estratégica GETNET + KLAP
  - Tabla de qué cajas usan qué
  - Procedimiento FALLA GETNET (<60s)
  - Procedimiento FALLA INTERNET
  - Checklists inicio/cierre de turno
  - Requisitos KLAP
  - Contactos de soporte
- `docs/CAJAS_MVP1.md` (ACTUALIZADO)
  - Sección de estrategia de pagos agregada
  - Configuración por tipo de caja
  - Referencia a PAGOS_BIMBA.md

---

## 📊 CAMPOS AGREGADOS

### PosRegister

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `payment_provider_primary` | String(50) | 'GETNET' | Provider principal de pagos |
| `payment_provider_backup` | String(50) | NULL | Provider backup (KLAP recomendado) |
| `provider_config` | Text (JSON) | NULL | Configuración por proveedor (terminal_id, merchant_id, etc) |
| `fallback_policy` | Text (JSON) | NULL | Reglas de cuándo usar backup |

**Ejemplo `fallback_policy`:**
```json
{
  "enabled": true,
  "trigger_events": ["pos_offline", "pos_error", "printer_error_optional"],
  "max_switch_time_seconds": 60,
  "backup_devices_required": 2
}
```

### RegisterSession

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `payment_provider_used_primary_count` | Integer | 0 | Transacciones con provider principal |
| `payment_provider_used_backup_count` | Integer | 0 | Transacciones con provider backup |
| `fallback_events` | Text (JSON array) | NULL | Eventos de fallback registrados |

**Ejemplo `fallback_events`:**
```json
[
  {
    "timestamp": "2025-01-15T22:30:00",
    "reason": "pos_offline",
    "from_provider": "GETNET",
    "to_provider": "KLAP",
    "handled_by_user_id": "cajero123"
  }
]
```

---

## 🖥️ NUEVA SECCIÓN EN /admin/cajas/

### Ubicación
En el formulario de crear/editar caja, después de "Métodos de Pago Habilitados" y antes de "Responsabilidad".

### Campos Visibles

1. **Provider Principal** (select, requerido)
   - Opciones: GETNET (default), KLAP, SUMUP
   - Default: GETNET

2. **Provider Backup** (select, opcional)
   - Opciones: -- Sin backup --, KLAP (recomendado), GETNET
   - Default: -- Sin backup --

3. **Fallback Habilitado** (checkbox)
   - Permite cambiar automáticamente al backup cuando falla principal
   - Default: checked

4. **Requisitos Fallback** (checklist visual, informativo)
   - ✅ Celulares con NFC habilitado
   - ✅ Cargadores disponibles
   - ✅ Datos móviles activos (WiFi backup)
   - Nota: Requisitos obligatorios para operar con KLAP

5. **Tiempo Máximo de Cambio** (number, segundos)
   - Rango: 30-300 segundos
   - Default: 60 segundos

6. **Cantidad Mínima de Celulares Backup** (number)
   - Rango: 1-10
   - Default: 2

7. **Configuración de Providers** (textarea JSON)
   - Placeholder con ejemplo de estructura
   - Para terminal_id, merchant_id, api_key, etc.

8. **Política de Fallback** (textarea JSON)
   - Placeholder con ejemplo completo
   - trigger_events, max_switch_time_seconds, backup_devices_required

### Validaciones por Tipo de Caja

**TOTEM:**
- Backup permitido pero operativo manual (no integrado aún)
- Mensaje de advertencia visible

**HUMANA/OFICINA:**
- Backup KLAP recomendado
- Sin restricciones

**VIRTUAL:**
- Provider principal GETNET
- Nota: Integración real en fase posterior

---

## ✅ CHECKLIST OPERATIVO FINAL (RESUMEN)

### Inicio de Turno

**GETNET:**
- [ ] Terminal encendido y conectado
- [ ] Probar transacción de prueba ($1.000)
- [ ] Verificar conexión a red

**KLAP (Backup):**
- [ ] Mínimo 2 celulares con app KLAP instalada
- [ ] Celulares con batería > 50%
- [ ] NFC habilitado en celulares
- [ ] Datos móviles activos (o WiFi estable)
- [ ] Probar transacción de prueba ($1.000)
- [ ] Cargadores disponibles

**Infraestructura:**
- [ ] WiFi funcionando
- [ ] Datos móviles activos en celulares backup

### Durante Operación

**Si falla GETNET:**
1. Detectar falla (< 5 segundos)
2. Tomar celular con app KLAP
3. Abrir app y procesar pago
4. **Objetivo: < 60 segundos** desde detección hasta pago procesado
5. Registrar fallback en sistema
6. Continuar con KLAP hasta recuperación

**Si falla Internet:**
- WiFi falló → Cambiar a datos móviles
- Datos también fallaron → Solo efectivo temporalmente

### Cierre de Turno

**Registrar:**
- [ ] Total transacciones GETNET
- [ ] Total transacciones KLAP
- [ ] Número de fallbacks
- [ ] Razones de fallback
- [ ] Tiempo promedio de cambio

**Reportar:**
- [ ] Fallas frecuentes de GETNET → Soporte GETNET
- [ ] Problemas con KLAP → Revisar configuración
- [ ] Problemas de internet → Proveedor de internet

---

## 📝 PRÓXIMOS PASOS

1. **Aplicar migración:**
   ```bash
   psql -U postgres -d bimba_db -f migrations/add_payment_provider_fields.sql
   ```

2. **Configurar cajas existentes:**
   - Ir a `/admin/cajas/<id>/editar`
   - Configurar payment providers según tipo de caja
   - Guardar configuración

3. **Capacitar cajeros:**
   - Entrenar en uso de app KLAP
   - Practicar procedimiento de fallback
   - Probar fallback al menos una vez por semana

4. **Integración real (fase posterior):**
   - Integrar con GETNET API
   - Integrar con KLAP API
   - Automatizar detección de fallas
   - Automatizar cambio a backup

---

## 🎯 OBJETIVOS CUMPLIDOS

✅ **Configuración por caja:** Campos y UI para definir providers y fallback  
✅ **Playbooks operativos:** Documentación completa de procedimientos  
✅ **Documentación:** PAGOS_BIMBA.md con checklists y procedimientos  
✅ **Trazabilidad:** Campos para registrar uso de providers y fallbacks  
✅ **Sin integración real:** Solo configuración y operación manual por ahora  

---

**Payment Stack BIMBA implementado ✅**


