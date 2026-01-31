# 🔍 ERROR AUDIT - Documentación Completa

**Fecha:** 2025-01-15  
**Objetivo:** Sistema de captura y auditoría de errores end-to-end

---

## SISTEMA DE CAPTURA DE ERRORES

### Componentes

1. **`app/static/js/error_capture.js`**
   - Captura errores JavaScript (`window.onerror`)
   - Captura promesas rechazadas (`unhandledrejection`)
   - Intercepta `fetch` y `XMLHttpRequest`
   - Captura violaciones CSP (si están disponibles)
   - Almacena errores en memoria con contexto completo

2. **`app/routes/debug_routes.py`**
   - `/admin/debug/errors` - Panel visual de errores
   - `/admin/debug/errors/export` - Instrucciones para exportar
   - `/admin/debug/errors` (POST) - Recibir reporte del cliente

3. **`tools/smoke_test_admin.py`**
   - Script Python para probar rutas admin
   - Detecta errores 4xx/5xx
   - Exporta resultados a JSON

---

## ACTIVACIÓN

### Desarrollo Local:
El sistema se activa automáticamente si:
- `FLASK_ENV != 'production'` Y `hostname == 'localhost'` o `'127.0.0.1'`

### Producción:
Activar con variable de entorno:
```bash
export DEBUG_ERRORS=1
```

O verificar que el usuario admin esté logueado (para panel visual).

---

## USO

### En el navegador:

1. **Ver reporte actual:**
   ```javascript
   window.getErrorReport()
   ```

2. **Limpiar reporte:**
   ```javascript
   window.clearErrorReport()
   ```

3. **Exportar JSON:**
   ```javascript
   JSON.stringify(window.getErrorReport(), null, 2)
   ```

4. **Panel visual:**
   Navegar a `/admin/debug/errors` (requiere login admin)

### Smoke Test:

```bash
# Configurar variables de entorno (opcional)
export SMOKE_TEST_URL=http://localhost:5001
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=admin

# Ejecutar smoke test
python3 tools/smoke_test_admin.py

# Resultados se guardan en smoke_test_results_*.json
```

---

## AGRUPACIÓN POR CAUSA RAÍZ

### Familia A: CSP/CDN/Socket
**Síntomas:**
- Errores de CSP en consola
- Conexiones bloqueadas a CDNs
- Socket.IO no conecta

**Fix aplicado:**
- ✅ Self-hosting de librerías (Socket.IO, Chart.js, QRCode.js)
- ✅ CSP sin CDNs (solo `'self'`)
- ✅ `connect-src` permite `ws:` y `wss:`

**Estado:** ✅ Resuelto

---

### Familia B: 500 Backend
**Síntomas:**
- Errores 500 en Network tab
- Tracebacks en HTML
- Endpoints que fallan consistentemente

**Fix estándar:**
```python
try:
    # Lógica del endpoint
    result = some_operation()
    return jsonify({'success': True, 'data': result})
except Exception as e:
    current_app.logger.exception(f"Error en endpoint: {e}")
    return jsonify({'success': False, 'error': 'Error interno'}), 500
```

**Pendiente:** Identificar endpoints específicos con smoke test

---

### Familia C: 404 Assets/Static
**Síntomas:**
- Recursos estáticos no encontrados
- Imágenes rotas
- CSS/JS no carga

**Fix estándar:**
- Verificar rutas `url_for('static', ...)`
- Cache-busting con `CSS_VERSION`
- Verificar que archivos existan en `app/static/`

**Pendiente:** Identificar assets específicos con smoke test

---

### Familia D: JSON Serialization
**Síntomas:**
- Errores "Object of type datetime is not JSON serializable"
- Errores con Decimal
- Errores con objetos ORM

**Fix estándar:**
```python
def to_dict(obj):
    """Helper para serializar objetos a dict"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif hasattr(obj, '__dict__'):
        return {k: to_dict(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    return obj
```

**Pendiente:** Identificar endpoints específicos

---

### Familia E: Auth/Permiso (401/403)
**Síntomas:**
- Errores 401/403 en endpoints admin
- Redirecciones inesperadas
- Sesiones expiradas

**Fix estándar:**
- Verificar `session.get('admin_logged_in')` antes de endpoints
- Retornar JSON consistente: `{'error': 'Unauthorized'}, 401`
- Redirecciones claras a `/login_admin`

**Pendiente:** Identificar endpoints específicos

---

### Familia F: Frontend null/undefined
**Síntomas:**
- "Cannot read property X of null"
- Selectores que no encuentran elementos
- Variables undefined

**Fix estándar:**
```javascript
// Guards antes de usar elementos
const element = document.getElementById('my-id');
if (!element) {
    console.warn('Element #my-id not found');
    return;
}
// Usar element...
```

**Pendiente:** Identificar errores específicos con error_capture.js

---

## RUTAS VERIFICADAS

### Rutas Admin Principales:

1. `/admin` → `/admin/dashboard` ✅
2. `/admin/dashboard` ✅
3. `/admin/logs` ✅
4. `/admin/turnos` ✅
5. `/admin/panel_control` ✅
6. `/admin/scanner` ✅
7. `/admin/equipo/listar` ✅
8. `/admin/inventario` ✅
9. `/admin/guardarropia` ✅
10. `/encuesta/admin` ✅
11. `/admin/programacion` ✅

**Nota:** Ejecutar `tools/smoke_test_admin.py` para verificar estado actual.

---

## CÓMO CORRER EL SMOKE TEST

### Requisitos:
```bash
pip install requests
```

### Ejecución:
```bash
# Con valores por defecto (localhost:5001)
python3 tools/smoke_test_admin.py

# Con configuración personalizada
SMOKE_TEST_URL=http://localhost:5001 \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin \
python3 tools/smoke_test_admin.py
```

### Salida:
- Resultados en consola (✅/❌ por ruta)
- JSON exportado: `smoke_test_results_*.json`
- Código de salida: 0 si no hay errores, 1 si hay errores

---

## DEFINITION OF DONE

### ✅ Criterios de éxito:

1. **Navegación sin 500:**
   - Todas las rutas admin cargan sin errores 500
   - Verificado con smoke test

2. **Network limpio:**
   - 0 requests 500 en flujo normal
   - 404 solo para recursos realmente inexistentes (documentados)

3. **Consola limpia:**
   - Sin errores rojos (JS errors)
   - Warnings aceptables solo si están documentados
   - Sin violaciones CSP

4. **Reporte exportable:**
   - `window.getErrorReport()` funciona
   - Panel `/admin/debug/errors` muestra datos
   - Smoke test genera JSON válido

---

## PRÓXIMOS PASOS

1. **Ejecutar smoke test:**
   ```bash
   python3 tools/smoke_test_admin.py
   ```

2. **Navegar manualmente:**
   - Abrir `/admin/debug/errors`
   - Navegar rutas admin principales
   - Revisar consola y Network tab

3. **Agrupar errores:**
   - Analizar JSON del smoke test
   - Analizar reporte de error_capture.js
   - Agrupar por familia (A-F)

4. **Aplicar fixes:**
   - Por familia, aplicar solución estándar
   - Verificar que fixes resuelven errores
   - Documentar cambios

---

## REFERENCIAS

- `app/static/js/error_capture.js` - Sistema de captura
- `app/routes/debug_routes.py` - Endpoints de debug
- `tools/smoke_test_admin.py` - Script de smoke test
- `SECURITY_CSP.md` - Documentación CSP


