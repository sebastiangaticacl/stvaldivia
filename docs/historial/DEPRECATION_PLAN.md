# Plan de Deprecación de Endpoints No Utilizados

**Fecha:** 2025-12-20  
**Estado:** Plan de acción (sin implementar)  
**Objetivo:** Reducir superficie de ataque y simplificar código sin romper funcionalidad existente

---

## 📋 METODOLOGÍA

Este plan categoriza endpoints no utilizados en tres grupos según su propósito y riesgo:

- **Categoría A (dev/debug only):** Endpoints de desarrollo/debugging → **Eliminación directa**
- **Categoría B (admin/ops):** Endpoints administrativos/operacionales → **Ocultar en UI + Protección**
- **Categoría C (integrations/feature):** Endpoints de integraciones/features → **Ocultar + Protección + Documentar**

---

## 📂 CATEGORÍA A: DEV/DEBUG ONLY

Endpoints diseñados exclusivamente para desarrollo y debugging. **Riesgo bajo** de eliminación.

### Endpoints Identificados

#### 1. `/admin/debug/errors` (GET)
- **Archivo:** `app/routes/debug_routes.py`
- **Línea aproximada:** 81
- **Propósito:** Panel de visualización de errores del cliente
- **Uso actual:** 0 requests
- **Registro:** Blueprint `debug_bp` con `url_prefix='/admin/debug'`
- **Protección actual:** `is_debug_enabled()` check

**Plan de Eliminación:**

**Opción 1: Feature Flag con 410 Gone (Recomendado)**
```python
@debug_bp.route('/errors')
def errors_panel():
    """DEPRECATED: Panel simple para ver resumen de errores"""
    return jsonify({
        'error': 'This endpoint has been deprecated',
        'deprecated': True,
        'removed_date': '2025-12-20'
    }), 410
```

**Opción 2: Eliminación Completa**
- Eliminar función `errors_panel()` de `app/routes/debug_routes.py`
- Eliminar template relacionado si existe: `app/templates/admin/debug_errors.html`
- Verificar referencias en frontend (búsqueda: `debug/errors`)

---

#### 2. `/admin/debug/errors` (POST)
- **Archivo:** `app/routes/debug_routes.py`
- **Línea aproximada:** 40
- **Propósito:** Recibir reportes de errores del cliente
- **Uso actual:** 0 requests
- **Registro:** Blueprint `debug_bp`

**Plan de Eliminación:**

**Opción 1: Feature Flag con 410 Gone**
```python
@debug_bp.route('/errors', methods=['POST'])
def receive_errors():
    """DEPRECATED: Recibir reporte de errores del cliente"""
    return jsonify({
        'error': 'This endpoint has been deprecated',
        'deprecated': True,
        'removed_date': '2025-12-20'
    }), 410
```

**Opción 2: Eliminación Completa**
- Eliminar función `receive_errors()` de `app/routes/debug_routes.py`
- Verificar referencias en frontend JavaScript (búsqueda: `/debug/errors`, `POST`, `fetch`)

---

#### 3. `/admin/debug/errors/export`
- **Archivo:** `app/routes/debug_routes.py`
- **Línea aproximada:** 22
- **Propósito:** Exportar reporte de errores en formato descargable
- **Uso actual:** 0 requests
- **Registro:** Blueprint `debug_bp`

**Plan de Eliminación:**

**Opción 1: Feature Flag con 410 Gone**
```python
@debug_bp.route('/errors/export')
def export_errors():
    """DEPRECATED: Exportar reporte de errores capturados en el cliente"""
    return jsonify({
        'error': 'This endpoint has been deprecated',
        'deprecated': True,
        'removed_date': '2025-12-20'
    }), 410
```

**Opción 2: Eliminación Completa**
- Eliminar función `export_errors()` de `app/routes/debug_routes.py`
- Verificar referencias en frontend (búsqueda: `errors/export`)

---

### Resumen Categoría A

**Archivos a modificar:**
- `app/routes/debug_routes.py` (3 funciones)

**Pasos recomendados:**
1. ✅ **IMPLEMENTADO:** Opción 1 (410 Gone) con feature flag `ENABLE_DEBUG_ERRORS`
2. Monitorear logs por 2 semanas para confirmar que no hay uso
3. Si no hay requests, proceder con Opción 2 (eliminación completa)
4. Opcional: Eliminar blueprint completo si todas sus rutas se eliminan

---

### ✅ FASE 1 IMPLEMENTADA (2025-12-20)

**Variable de Entorno:**
- `ENABLE_DEBUG_ERRORS=false` (por defecto, deshabilitado)
- Para habilitar: `ENABLE_DEBUG_ERRORS=true`

**Comportamiento:**
- Si `ENABLE_DEBUG_ERRORS=false`: Los 3 endpoints retornan HTTP 410 Gone con header `X-Deprecated: true`
- Si `ENABLE_DEBUG_ERRORS=true`: Los endpoints funcionan normalmente (comportamiento original)
- La autenticación admin se mantiene intacta (no se debilita seguridad)

**Endpoints afectados:**
- `GET /admin/debug/errors` → 410 Gone (si flag=false)
- `POST /admin/debug/errors` → 410 Gone (si flag=false)
- `GET /admin/debug/errors/export` → 410 Gone (si flag=false)

**Logging:**
- Se registra cada acceso a endpoint deprecated con: `DEPRECATED endpoint accessed: {route} from IP: {client_ip}`

**Próximos pasos:**
1. Monitorear logs por 2 semanas
2. Si no hay requests, proceder con eliminación completa (Opción 2)
3. Fecha estimada de eliminación: 2026-01-03 (después del período de monitoreo)

---

## 📂 CATEGORÍA B: ADMIN/OPS

Endpoints administrativos y operacionales que pueden ser útiles pero no se usan actualmente. **Proteger y ocultar** en lugar de eliminar.

### Endpoints Identificados

#### 1. `/api/system/cache/stats`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 88
- **Propósito:** Estadísticas del sistema de cache
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Verificar autenticación admin: `if not session.get('admin_logged_in'): return 403`
- ✅ Agregar CSRF protection si aplica
- ❌ **NO** eliminar (útil para debugging operacional)
- ❌ **NO** ocultar en UI (no hay UI para esto actualmente)

---

#### 2. `/api/system/performance/stats`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 105
- **Propósito:** Estadísticas de rendimiento de funciones
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Verificar autenticación admin: `if not session.get('admin_logged_in'): return 403`
- ✅ Agregar CSRF protection si aplica
- ❌ **NO** eliminar (útil para optimización)

---

#### 3. `/api/system/csv/stats`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 125
- **Propósito:** Estadísticas de archivos CSV
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Verificar autenticación admin: `if not session.get('admin_logged_in'): return 403`
- ❌ **NO** eliminar (puede ser útil para debugging)

---

#### 4. `/api/system/circuit-breakers`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 194
- **Propósito:** Estado de los circuit breakers (admin only según código)
- **Uso actual:** 0 requests
- **Protección actual:** Ya tiene check de admin (revisar implementación)
- **Acción:** Verificar protección + Rate limit

**Plan de Protección:**
- ✅ Verificar que tiene `if not session.get('admin_logged_in'): return 403`
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Agregar CSRF protection si aplica
- ❌ **NO** eliminar (útil para debugging de circuit breakers)

---

#### 5. `/api/system/export/logs`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 175
- **Propósito:** Exportar logs en CSV
- **Uso actual:** 0 requests
- **Duplicado de:** `/admin/export/csv`
- **Acción:** Proteger + Considerar deprecación con redirect

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=5, per_seconds=60)`
- ✅ Verificar autenticación admin
- ✅ **RECOMENDACIÓN:** Agregar deprecation warning y sugerir usar `/admin/export/csv`
- Opcional: Redirect a `/admin/export/csv` con 301

---

#### 6. `/api/dashboard/stats`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 328
- **Propósito:** Estadísticas para dashboard
- **Uso actual:** 0 requests
- **Duplicado de:** `/admin/api/dashboard/metrics`
- **Acción:** Proteger + Deprecation warning + Redirect

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin
- ✅ **RECOMENDACIÓN:** Agregar deprecation warning en respuesta
- ✅ Opcional: Redirect interno a `/admin/api/dashboard/metrics` o retornar mismo formato

---

#### 7. `/api/services/status`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 216
- **Propósito:** Estado de servicios
- **Uso actual:** 0 requests
- **Duplicado de:** `/admin/api/services/status`
- **Acción:** Proteger + Deprecation warning

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin
- ✅ Agregar header `X-Deprecated: true` en respuesta
- ✅ Agregar campo `deprecated_endpoint: "/admin/api/services/status"` en JSON response
- ❌ **NO** eliminar inmediatamente (dar tiempo de migración)

---

#### 8. `/api/services/restart`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 242
- **Propósito:** Reiniciar servicio
- **Uso actual:** 0 requests
- **Duplicado de:** `/admin/service/restart`
- **Acción:** Proteger fuertemente + Deprecation warning

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=5, per_seconds=300)` (muy restrictivo)
- ✅ Verificar autenticación admin: `if not session.get('admin_logged_in'): return 403`
- ✅ Agregar CSRF protection (crítico para POST)
- ✅ Agregar confirmación adicional (PIN o token)
- ✅ Agregar header `X-Deprecated: true`
- ✅ Agregar campo `deprecated_endpoint: "/admin/service/restart"` en JSON response
- ❌ **NO** eliminar (operación crítica, mantener por compatibilidad)

---

#### 9. `/api/services/postfix/queue`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 288
- **Propósito:** Cola de correo Postfix
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Verificar autenticación admin
- ❌ **NO** eliminar (útil para debugging de email)

---

#### 10. `/api/monitoring/stats`
- **Archivo:** `app/routes/monitoring_routes.py`
- **Línea aproximada:** 12
- **Propósito:** Estadísticas de monitoreo
- **Uso actual:** 0 requests
- **Duplicado de:** `/admin/api/monitoreo/status`
- **Acción:** Proteger + Deprecation warning

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin
- ✅ Agregar header `X-Deprecated: true`
- ✅ Agregar campo `deprecated_endpoint: "/admin/api/monitoreo/status"` en JSON response

---

#### 11. `/admin/pos_stats`
- **Archivo:** `app/routes.py`
- **Línea aproximada:** 83
- **Propósito:** Redirigir a dashboard (módulo eliminado)
- **Uso actual:** 0 requests
- **Acción:** Mantener redirect o eliminar

**Plan de Protección:**
- ✅ Mantener redirect a `/admin/dashboard` (sin cambios necesarios)
- ⚠️ Alternativa: Retornar 410 Gone si se confirma que no se usa

---

#### 12. `/admin/api/register/toggle`
- **Archivo:** `app/routes.py`
- **Línea aproximada:** 92
- **Propósito:** API deshabilitada (módulo eliminado)
- **Uso actual:** 0 requests
- **Acción:** Retornar 410 Gone

**Plan de Protección:**
- ✅ Cambiar respuesta a `410 Gone` con mensaje claro
- ✅ Agregar header `X-Deprecated: true`
- ⚠️ No eliminar código inmediatamente (monitorear 2 semanas)

---

#### 13. `/admin/api/sync/start`
- **Archivo:** `app/routes.py`
- **Línea aproximada:** 2446
- **Propósito:** Iniciar sincronización de datos
- **Uso actual:** 0 requests
- **Acción:** Proteger fuertemente + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=5, per_seconds=300)`
- ✅ Verificar autenticación admin
- ✅ Agregar CSRF protection (POST)
- ✅ Agregar confirmación adicional (operación costosa)
- ❌ **NO** eliminar (puede ser útil para migraciones futuras)

---

#### 14. `/admin/api/sync/status`
- **Archivo:** `app/routes.py`
- **Línea aproximada:** 2481
- **Propósito:** Estado de sincronización
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin

---

#### 15. `/admin/api/sync/tables`
- **Archivo:** `app/routes.py`
- **Línea aproximada:** 2502
- **Propósito:** Lista de tablas disponibles para sincronizar
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Verificar autenticación admin

---

#### 16. `/admin/tpv/dashboard`
- **Archivo:** `app/routes/tpv_dashboard_routes.py`
- **Línea aproximada:** 17
- **Propósito:** Dashboard de monitoreo TPV
- **Uso actual:** 0 requests
- **Blueprint:** `tpv_dashboard_bp` con `url_prefix='/admin/tpv'`
- **Protección actual:** Ya tiene `if not session.get('admin_logged_in'): return redirect(...)`
- **Acción:** Proteger + Ocultar en UI

**Plan de Protección:**
- ✅ Verificar autenticación admin en la función
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)` si es API
- ✅ **Ocultar en UI:** Eliminar cualquier link/menú que apunte a `/tpv/dashboard`
- ❌ **NO** eliminar endpoint (puede ser útil para debugging)

---

#### 17. `/admin/tpv/api/status`
- **Archivo:** `app/routes/tpv_dashboard_routes.py`
- **Línea aproximada:** 72
- **Propósito:** Estado de todos los TPV
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin (agregar si no existe)
- ❌ **NO** eliminar (útil para debugging)

---

#### 18. `/admin/tpv/api/<tpv_id>/stats`
- **Archivo:** `app/routes/tpv_dashboard_routes.py`
- **Línea aproximada:** 129
- **Propósito:** Estadísticas detalladas de un TPV
- **Uso actual:** 0 requests
- **Acción:** Proteger + Ocultar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin (agregar si no existe)

---

### Resumen Categoría B

**Archivos a modificar:**
- `app/routes/api_routes.py` (9 endpoints)
- `app/routes.py` (4 endpoints)
- `app/routes/monitoring_routes.py` (1 endpoint)
- `app/routes/tpv_dashboard_routes.py` (3 endpoints)

**Acciones comunes:**
1. Agregar `@rate_limit` a todos los endpoints
2. Verificar/agregar autenticación admin
3. Agregar CSRF protection para POST/PUT/DELETE
4. Agregar headers `X-Deprecated: true` para duplicados
5. Agregar campos `deprecated_endpoint` en JSON responses cuando aplica
6. **NO** eliminar código (útil para operaciones)

---

## 📂 CATEGORÍA C: INTEGRATIONS/FEATURE

Endpoints de integraciones externas o features que pueden usarse por sistemas externos. **Proteger, documentar y monitorear**.

### Endpoints Identificados

#### 1. `/api/sale-details/<sale_id>`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 361
- **Propósito:** Detalles de una venta
- **Uso actual:** 0 requests
- **Acción:** Proteger + Documentar + Monitorear

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=60, per_seconds=60)`
- ✅ Verificar autenticación admin O token de API válido
- ✅ Agregar CSRF protection si es necesario
- ✅ Documentar en README o docs si es API pública
- ❌ **NO** eliminar (puede usarse por integraciones externas)

---

#### 2. `/api/v1/agent/public-info/today`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 430
- **Propósito:** Info pública del evento de hoy para agente/bot
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar

**Plan de Protección:**
- ✅ Ya tiene rate limiting (verificar implementación)
- ✅ Es endpoint público (no requiere autenticación)
- ✅ Documentar en README como API pública para bots
- ❌ **NO** eliminar (diseñado para integraciones externas)

---

#### 3. `/api/v1/agent/public-info/date`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 466
- **Propósito:** Info pública por fecha
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar

**Plan de Protección:**
- ✅ Ya tiene rate limiting (verificar)
- ✅ Endpoint público
- ✅ Documentar en README

---

#### 4. `/api/v1/agent/public-info/upcoming`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 521
- **Propósito:** Eventos próximos
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar

**Plan de Protección:**
- ✅ Ya tiene rate limiting (verificar)
- ✅ Endpoint público
- ✅ Documentar en README

---

#### 5. `/api/v1/agent/programacion/month/public`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 562
- **Propósito:** Programación mensual pública
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar

**Plan de Protección:**
- ✅ Ya tiene rate limiting (verificar)
- ✅ Endpoint público
- ✅ Documentar en README

---

#### 6. `/api/v1/agent/programacion/month/internal`
- **Archivo:** `app/routes/api_routes.py`
- **Línea aproximada:** 618
- **Propósito:** Programación mensual interna
- **Uso actual:** 0 requests
- **Acción:** Proteger + Documentar

**Plan de Protección:**
- ✅ Agregar autenticación (internal = requiere auth)
- ✅ Agregar decorador `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ Verificar autenticación admin o token API
- ✅ Documentar como API interna

---

#### 7. `/recipe/<product_name>`
- **Archivo:** `app/routes/recipe_routes.py`
- **Línea aproximada:** 10
- **Propósito:** Obtener receta de producto (para app móvil)
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar + Monitorear

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=60, per_seconds=60)`
- ⚠️ Decidir si es público o requiere autenticación
- ✅ Documentar en README como API para app móvil
- ❌ **NO** eliminar (diseñado para app móvil)

---

#### 8. `/recipe/all`
- **Archivo:** `app/routes/recipe_routes.py`
- **Línea aproximada:** 35
- **Propósito:** Obtener todas las recetas (sincronización)
- **Uso actual:** 0 requests
- **Acción:** Proteger + Documentar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=10, per_seconds=60)`
- ✅ Agregar autenticación (sincronización = requiere auth)
- ✅ Agregar CSRF protection
- ✅ Documentar como API de sincronización

---

#### 9. `/product/api/search`
- **Archivo:** `app/routes/product_routes.py`
- **Línea aproximada:** 264
- **Propósito:** Buscar productos (autocompletado)
- **Uso actual:** 0 requests
- **Acción:** Mantener + Documentar

**Plan de Protección:**
- ✅ Agregar decorador `@rate_limit(max_requests=60, per_seconds=60)`
- ⚠️ Decidir si es público o requiere autenticación
- ✅ Documentar en README

---

#### 10. Rutas de Instagram/Meta Webhooks
- **Archivo:** `app/routes_instagram.py`
- **Blueprint:** `instagram_bp` con `url_prefix='/webhook'` (registrado en `app/__init__.py` línea 520-521)
- **Rutas:**
  - `/webhook/instagram` (GET) - Verificación de webhook
  - `/webhook/instagram` (POST) - Recibir webhooks
  - `/webhook/instagram/test` (POST) - Test de webhook
- **Uso actual:** 0 requests
- **Acción:** Proteger + Documentar + Considerar eliminación futura

**Plan de Protección:**
- ✅ **GET `/webhook/instagram`:** Ya tiene verificación de token (Instagram requiere esto). Mantener como está.
- ✅ **POST `/webhook/instagram`:** Ya tiene verificación de firma HMAC. Agregar rate limiting: `@rate_limit(max_requests=30, per_seconds=60)`
- ✅ **POST `/webhook/instagram/test`:** Agregar autenticación admin + rate limiting estricto: `@rate_limit(max_requests=5, per_seconds=60)`
- ⚠️ **CONSIDERACIÓN:** Si Instagram no se usa, considerar:
  - Marcar como deprecated con 410 Gone en respuestas
  - Agregar header `X-Deprecated: true`
  - Documentar como "no mantenido" o "experimental"
- ✅ Documentar en README como webhook endpoint para Meta/Instagram

**NOTA:** Estos endpoints son públicos por diseño (webhooks de Meta requieren endpoints públicos), pero tienen verificación de firma/token incorporada.

---

### Resumen Categoría C

**Archivos a modificar:**
- `app/routes/api_routes.py` (6 endpoints)
- `app/routes/recipe_routes.py` (2 endpoints)
- `app/routes/product_routes.py` (1 endpoint)
- `app/routes_instagram.py` (todo el archivo)

**Acciones comunes:**
1. Agregar rate limiting apropiado
2. Decidir nivel de autenticación (público vs. autenticado)
3. Documentar en README o documentación de API
4. Agregar logging de acceso para monitoreo
5. ❌ **NO** eliminar (pueden usarse por integraciones externas)

---

## 🎯 PLAN DE IMPLEMENTACIÓN

### Fase 1: Categoría A (Dev/Debug) - 1-2 semanas

1. **Semana 1:**
   - Implementar Opción 1 (410 Gone) para los 3 endpoints de debug
   - Deploy a producción
   - Monitorear logs

2. **Semana 2:**
   - Si no hay requests a los endpoints deprecated
   - Proceder con Opción 2 (eliminación completa)
   - Verificar que no hay referencias en frontend

**Archivos:**
- `app/routes/debug_routes.py`

---

### Fase 2: Categoría B (Admin/Ops) - 2-3 semanas

1. **Semana 1:**
   - Agregar rate limiting a todos los endpoints
   - Agregar verificación de autenticación admin donde falta
   - Agregar CSRF protection para POST/PUT/DELETE

2. **Semana 2:**
   - Agregar headers `X-Deprecated: true` para duplicados
   - Agregar campos `deprecated_endpoint` en JSON responses
   - Ocultar endpoints duplicados en UI (si aplica)

3. **Semana 3:**
   - Monitorear uso
   - Documentar endpoints deprecated en README

**Archivos:**
- `app/routes/api_routes.py`
- `app/routes.py`
- `app/routes/monitoring_routes.py`
- `app/routes/tpv_dashboard_routes.py`

---

### Fase 3: Categoría C (Integrations) - 2-3 semanas

1. **Semana 1:**
   - Agregar rate limiting
   - Agregar autenticación donde corresponda
   - Documentar endpoints en README

2. **Semana 2:**
   - Agregar logging de acceso
   - Crear documentación de API (si no existe)

3. **Semana 3:**
   - Monitorear uso
   - Evaluar si algunos pueden marcarse como deprecated

**Archivos:**
- `app/routes/api_routes.py`
- `app/routes/recipe_routes.py`
- `app/routes/product_routes.py`
- `app/routes_instagram.py`

---

## 📊 MÉTRICAS DE ÉXITO

### Antes de Implementar
- Endpoints sin rate limiting: ~15
- Endpoints sin autenticación: ~10
- Endpoints debug activos: 3
- Superficie de ataque: Alta

### Después de Implementar
- Endpoints sin rate limiting: 0
- Endpoints sin autenticación: Solo públicos documentados
- Endpoints debug activos: 0
- Superficie de ataque: Reducida

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### Antes de Eliminar Cualquier Endpoint

1. **Búsqueda exhaustiva:**
   ```bash
   # Buscar referencias en código
   grep -r "endpoint_name" app/
   grep -r "endpoint_name" app/templates/
   grep -r "endpoint_name" app/static/
   
   # Buscar en logs históricos
   grep "endpoint_name" logs/access.log | tail -100
   ```

2. **Verificar integraciones externas:**
   - Revisar documentación de API
   - Consultar con equipo sobre integraciones conocidas
   - Verificar código de apps móviles o externas

3. **Monitoreo post-implementación:**
   - Monitorear logs por 2-4 semanas después de cambios
   - Alertar si hay aumento de 404s o errores

### Protecciones a Implementar

**Rate Limiting:**
- Endpoints públicos: 60-120 req/min
- Endpoints admin: 10-30 req/min
- Endpoints críticos (restart, sync): 5 req/5min

**Autenticación:**
- Endpoints admin: `session.get('admin_logged_in')`
- APIs internas: Token API o admin session
- Endpoints públicos: Rate limiting estricto

**CSRF Protection:**
- Todos los POST/PUT/DELETE que modifiquen estado
- Verificar que Flask-WTF CSRF está habilitado

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Para cada endpoint:

- [ ] Agregar `@rate_limit` apropiado
- [ ] Verificar/agregar autenticación
- [ ] Agregar CSRF protection (si aplica)
- [ ] Agregar logging de acceso
- [ ] Documentar en README/docs
- [ ] Buscar referencias en frontend
- [ ] Monitorear logs post-implementación
- [ ] Agregar headers de deprecation (si aplica)

---

**Estado:** Plan completado, listo para revisión  
**Próximo paso:** Revisar plan y aprobar implementación por fases

