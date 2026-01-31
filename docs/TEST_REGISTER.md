# 🧪 Caja de Prueba (TEST Register)

**Fecha:** 2025-01-15  
**Código:** TEST001  
**Propósito:** Caja aislada para probar flujo POS + PaymentIntent (GETNET manual confirmado) sin afectar operación real

---

## 📋 CONFIGURACIÓN

### Características de la Caja TEST

- **Nombre:** CAJA TEST BIMBA
- **Código:** TEST001
- **Ubicación:** TEST
- **Tipo:** HUMANA
- **Estado:** ACTIVA
- **Flag:** `is_test=true`

### Métodos de Pago

- ✅ Efectivo (cash)
- ✅ Débito (debit)
- ✅ Crédito (credit)

### Payment Providers

- **Principal:** GETNET
- **Backup:** KLAP
- **Modo:** Manual confirmado (sin agente local)

### Configuración

```json
{
  "fallback_policy": {
    "enabled": true,
    "max_switch_time_seconds": 60,
    "backup_devices_required": 1,
    "trigger_events": ["pos_error", "pos_offline"]
  },
  "provider_config": {
    "note": "TEST REGISTER - no usar en operación real",
    "GETNET": {
      "mode": "manual",
      "note": "Pago manual confirmado"
    },
    "KLAP": {
      "merchant_id": "TEST-KLAP",
      "note": "Backup para pruebas"
    }
  }
}
```

---

## 🚀 CREAR CAJA DE PRUEBA

### Opción 1: Botón en Admin UI

1. Ir a `/admin/cajas/`
2. Click en botón **"🧪 Crear/Actualizar Caja TEST"**
3. La caja se crea/actualiza automáticamente (idempotente)

### Opción 2: Endpoint Admin

```bash
# Requiere login admin
curl -X POST https://stvaldivia.cl/admin/cajas/seed-test \
  -H "Cookie: session=..." \
  -b cookies.txt
```

### Opción 3: Función Python

```python
from app.helpers.seed_test_register import seed_test_register

success, message, register = seed_test_register()
if success:
    print(f"✅ {message}")
else:
    print(f"❌ {message}")
```

---

## 👁️ VISIBILIDAD EN POS

La caja TEST solo aparece en `/caja/register` si se cumple **AL MENOS UNA** de estas condiciones:

1. **Modo DEBUG:** `FLASK_DEBUG=true`
2. **Flag habilitado:** `ENABLE_TEST_REGISTERS=true`
3. **Usuario Superadmin:** Sesión de admin con username='sebagatica'
4. **Usuario Admin:** Sesión de admin activa

### Configurar Visibilidad

**En `.env`:**
```bash
# Mostrar cajas de prueba en selección POS
ENABLE_TEST_REGISTERS=1
```

**En producción (ocultar):**
```bash
ENABLE_TEST_REGISTERS=0
FLASK_DEBUG=false
```

---

## 🎯 USO

### 1. Seleccionar Caja TEST

1. Ir a `/caja/login`
2. Iniciar sesión
3. En `/caja/register`, seleccionar **"CAJA TEST BIMBA"**
4. La caja aparece con badge **"🧪 TEST"**

### 2. Probar Flujo GETNET Manual

1. Agregar productos al carrito
2. Click en botón **"🏦 GETNET"**
3. Modal aparece: "Pase tarjeta en terminal GETNET"
4. Ingresar código de autorización/voucher
5. Click **"APROBADO"** o **"RECHAZADO"**
6. Si aprobado: venta creada + inventario aplicado

### 3. Verificar en Admin

- `/admin/cajas/` → Caja TEST aparece con badge **"TEST"**
- `/admin/cajas/<id>/editar` → Checkbox **"Es caja de prueba"** marcado

---

## 🔒 SEGURIDAD

### Filtrado Automático

- En producción, con `ENABLE_TEST_REGISTERS=0`, la caja TEST **NO aparece** para cajeros regulares
- Solo aparece para admins/superadmins o en modo DEBUG

### Badge Visual

- En lista admin: badge **"TEST"** verde
- En selección POS: badge **"🧪 TEST (Caja de Prueba)"**

### Campo `is_test`

- Índice creado para filtrado rápido
- Fácil de filtrar en queries: `WHERE is_test = false`

---

## 📊 MIGRACIÓN

**Archivo:** `migrations/2025_01_15_add_is_test_to_pos_registers.sql`

```sql
ALTER TABLE pos_registers 
ADD COLUMN IF NOT EXISTS is_test BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_pos_registers_is_test ON pos_registers(is_test);
```

**Ejecutar:**
```bash
psql -U postgres -d bimba_db -f migrations/2025_01_15_add_is_test_to_pos_registers.sql
```

---

## 🧹 LIMPIEZA

### Ocultar en Producción

```sql
-- Ocultar caja TEST (desactivar)
UPDATE pos_registers 
SET is_active = false 
WHERE code = 'TEST001';

-- O eliminar (si es necesario)
DELETE FROM pos_registers WHERE code = 'TEST001';
```

### Filtrar en Queries

```python
# Excluir cajas de prueba
registers = PosRegister.query.filter_by(
    is_active=True,
    is_test=False
).all()
```

---

## 📝 NOTAS

1. **Idempotencia:** El seed puede ejecutarse múltiples veces sin duplicar
2. **Actualización:** Si la caja existe, se actualiza con configuración correcta
3. **Aislamiento:** La caja TEST está claramente marcada para evitar uso en producción
4. **Flexibilidad:** Fácil habilitar/deshabilitar con `ENABLE_TEST_REGISTERS`

---

**Documentación Caja de Prueba** ✅


