# ✅ SERVIDOR LOCAL INICIADO

**Fecha:** 2025-12-12  
**Estado:** ✅ **SERVIDOR CORRIENDO**

---

## 🚀 INFORMACIÓN DEL SERVIDOR

### URL Local
- **URL:** http://127.0.0.1:5001
- **Puerto:** 5001
- **Entorno:** development
- **Debug:** Habilitado

---

## 📍 ENDPOINTS DISPONIBLES

### APIs Públicas
- ✅ `GET http://127.0.0.1:5001/api/v1/public/evento/hoy`
- ✅ `GET http://127.0.0.1:5001/api/v1/public/eventos/proximos`

### Bot API
- ✅ `POST http://127.0.0.1:5001/api/v1/bot/responder`

### APIs Operacionales (requieren API key)
- ✅ `GET http://127.0.0.1:5001/api/v1/operational/summary`
- ✅ `GET http://127.0.0.1:5001/api/v1/operational/sales/summary`

### Panel de Control
- ✅ `http://127.0.0.1:5001/admin/panel_control`
- ✅ `http://127.0.0.1:5001/admin/bot/logs`

---

## 🔧 CONFIGURACIÓN

### Archivo de Ejecución
- **Script:** `run_local.py`
- **Puerto:** 5001 (configurable vía `PORT`)
- **Host:** 127.0.0.1 (configurable vía `HOST`)

### Variables de Entorno
- Archivo `.env` detectado y cargado
- `FLASK_ENV=development`
- `FLASK_DEBUG=True`

---

## 🛑 DETENER EL SERVIDOR

Para detener el servidor:
1. Presiona `Ctrl+C` en la terminal donde está corriendo
2. O ejecuta: `pkill -f "python.*run_local"`

---

## 📝 NOTAS

- El servidor está corriendo en modo desarrollo con debug habilitado
- SocketIO está activo para WebSockets
- Los cambios en el código se reflejarán automáticamente (auto-reload)

---

**Estado:** ✅ **SERVIDOR LOCAL OPERATIVO**

