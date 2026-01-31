# 🖥️ GETNET POS Integrado - Windows Serial (COM)

**Fecha:** 2025-01-15  
**Plataforma:** Windows 11  
**Puerto:** COM4 (USB Serial Device)

---

## 📋 CONFIGURACIÓN

### Habilitar GETNET Serial

**Variable de entorno:**
```bash
ENABLE_GETNET_SERIAL=1
```

**O en `.env`:**
```
ENABLE_GETNET_SERIAL=1
```

### Configuración en Admin - Cajas

**URL:** `/admin/cajas/<id>/editar`

**Sección:** "💳 Procesadores de Pago (GETNET + KLAP)"

**Campo:** "Configuración de Providers (JSON)"

**Ejemplo para GETNET Serial:**
```json
{
  "GETNET": {
    "mode": "serial",
    "port": "COM4",
    "baudrate": 9600,
    "timeout_ms": 30000
  },
  "KLAP": {
    "merchant_id": "KLAP-789",
    "api_key": "..."
  }
}
```

**Campos GETNET Serial:**
- `mode`: `"serial"` (obligatorio para comunicación serial)
- `port`: `"COM4"` (obligatorio, puerto COM en Windows)
- `baudrate`: `9600` (opcional, default: 9600)
- `timeout_ms`: `30000` (opcional, default: 30000ms = 30s)

**Validación:**
- Si `mode=serial` y `payment_provider_primary=GETNET` → `port` es obligatorio
- El sistema valida esto al guardar la configuración

---

## 🔍 VERIFICAR PUERTO COM EN WINDOWS

### Device Manager

1. Abrir **Device Manager** (Administrador de dispositivos)
2. Expandir **Ports (COM & LPT)**
3. Buscar **"USB Serial Device"** o **"GETNET"**
4. Verificar que aparece como **COM4** (o el puerto correcto)

### PowerShell

```powershell
# Listar puertos COM disponibles
Get-WmiObject Win32_SerialPort | Select-Object Name, DeviceID, Description
```

### Python (pyserial)

```python
import serial.tools.list_ports

for port in serial.tools.list_ports.comports():
    print(f"{port.device} - {port.description}")
```

---

## 🧪 SMOKE TEST

### Instalación de Dependencias

```bash
pip install pyserial
```

### Ejecutar Smoke Test

**Uso básico (puerto por defecto COM4):**
```bash
python tools/smoke_getnet_serial.py
```

**Con puerto específico:**
```bash
python tools/smoke_getnet_serial.py --port COM4
```

**Con configuración completa:**
```bash
python tools/smoke_getnet_serial.py --port COM4 --baudrate 9600 --timeout 30000
```

### Salida Esperada (PASS)

```
============================================================
GETNET Serial Smoke Test
============================================================

🔍 Testing GETNET Serial Connection
   Port: COM4
   Baudrate: 9600
   Timeout: 30000ms (30.0s)

📋 Listing available COM ports...
   ✅ Found: COM4 - USB Serial Device

🔌 Opening port COM4...
   ✅ Port COM4 opened successfully
   Port settings: {'baudrate': 9600, 'bytesize': 8, 'parity': 'N', 'stopbits': 1, 'xonxoff': False, 'rtscts': False, 'dsrdtr': False}

✅ Port COM4 is open and ready

📡 Testing port readiness...
   (No protocol defined yet - only checking port availability)
   ✅ Buffers cleared
   ✅ Port accepts operations

🔒 Closing port...
   ✅ Port COM4 closed successfully

============================================================
RESULTADO
============================================================

✅ PASS
   SUCCESS: Port COM4 is accessible and ready for GETNET communication
```

### Salida Esperada (FAIL)

```
============================================================
RESULTADO
============================================================

❌ FAIL
   ERROR: Cannot open port COM4. Port might be in use by another application or requires administrator privileges.

TROUBLESHOOTING:
   1. Verificar que el puerto COM existe en Device Manager
   2. Verificar que no hay otra aplicación usando el puerto
   3. En Windows, puede requerir ejecutar como Administrador
   4. Verificar que pyserial está instalado: pip install pyserial
```

---

## 🐛 TROUBLESHOOTING

### Error: "Cannot open port COM4"

**Causas posibles:**
1. Puerto en uso por otra aplicación
2. Permisos insuficientes (requiere ejecutar como Administrador)
3. Puerto no existe o está desconectado

**Soluciones:**
- Cerrar otras aplicaciones que usen el puerto
- Ejecutar como Administrador
- Verificar en Device Manager que el puerto existe

### Error: "Port COM4 not found"

**Causas posibles:**
1. Dispositivo no conectado
2. Driver no instalado
3. Puerto asignado a otro número

**Soluciones:**
- Verificar conexión USB
- Instalar drivers del dispositivo GETNET
- Verificar en Device Manager el puerto correcto

### Error: "pyserial no está instalado"

**Solución:**
```bash
pip install pyserial
```

---

## 📝 NOTAS IMPORTANTES

1. **Flag ENABLE_GETNET_SERIAL:**
   - Toda la funcionalidad GETNET Serial está detrás de este flag
   - Si no está habilitado, la validación de serial no se ejecuta
   - Por defecto está deshabilitado (`ENABLE_GETNET_SERIAL=0`)

2. **Protocolo:**
   - Por ahora el smoke test solo verifica que el puerto es accesible
   - No se implementa protocolo GETNET aún (fase posterior)
   - El smoke test se limita a open/close y readiness del puerto

3. **Windows:**
   - Los puertos COM son específicos de Windows
   - En Linux/Mac se usarían `/dev/ttyUSB0` o `/dev/ttyACM0`
   - El código actual está preparado para Windows COM

4. **Validación en Admin:**
   - Si `mode=serial` y `provider=GETNET` → `port` es obligatorio
   - La validación se ejecuta al guardar la configuración de caja
   - Solo se valida si `ENABLE_GETNET_SERIAL=1`

---

## 🔄 PRÓXIMOS PASOS

1. **Implementar protocolo GETNET:**
   - Comandos de poll/healthcheck
   - Comandos de transacción
   - Manejo de respuestas

2. **Integración con ventas:**
   - Llamar a GETNET Serial al procesar pago
   - Manejar respuestas y errores
   - Registrar resultado en venta

3. **Manejo de errores:**
   - Timeouts
   - Errores de comunicación
   - Fallback a KLAP si GETNET falla

---

**Documentación GETNET Windows Serial** ✅


