# Análisis de Rendimiento y APIs No Utilizadas

**Fecha:** 2025-12-20  
**Servidor:** stvaldivia.cl (34.176.144.166)

---

## 📊 RENDIMIENTO DEL SERVIDOR

### Recursos del Sistema

**CPU:**
- Uso actual: 0-2% (idle: 98.99%)
- Load average: 0.33, 0.23, 0.13 (muy bajo)
- Estado: ✅ Excelente

**Memoria:**
- Total: 7.8 GB
- Usada: 878 MB (11%)
- Libre: 4.9 GB (63%)
- Buffer/Cache: 2.0 GB
- Disponible: 6.6 GB
- Estado: ✅ Excelente

**Disco:**
- Uso: 11 GB / 29 GB (38%)
- I/O: Mínimo (0.00% util)
- Estado: ✅ Excelente

**Gunicorn:**
- Workers: 4 (eventlet)
- Memoria por worker: ~109 MB
- Total memoria Gunicorn: ~450 MB
- Timeout: 30 segundos
- Estado: ✅ Adecuado

### Análisis de Logs (Últimas 2000 requests)

**Códigos HTTP:**
- 200 (OK): 548 (55%)
- 404 (Not Found): 286 (29%) ⚠️ **ALTO**
- 400 (Bad Request): 105 (11%) ⚠️
- 304 (Not Modified): 45 (5%)
- 429 (Rate Limited): 16 (2%) ✅ Mejoró después del fix

**Problemas Identificados:**
1. **Alto porcentaje de 404s (29%)**: Muchas requests a endpoints inexistentes
2. **Alto porcentaje de 400s (11%)**: Requests mal formadas o con datos inválidos
3. **Polling excesivo**: 724 requests a `/caja/api/payment/agent/pending` (36% del tráfico)

---

## 🔍 ENDPOINTS MÁS UTILIZADOS

### Top 10 Endpoints (Últimas 2000 requests)

1. **724 requests** - `/caja/api/payment/agent/pending?register_id=1`
   - **Uso:** Polling del agente Getnet Java
   - **Estado:** ✅ Necesario (pero muy frecuente)
   - **Optimización:** Ya aumentado rate limit a 120/min

2. **13 requests** - `/static/vendor/socket.io.min.js`
   - **Uso:** WebSockets para actualizaciones en tiempo real
   - **Estado:** ✅ Necesario

3. **13 requests** - `/static/vendor/chart.umd.min.js`
   - **Uso:** Gráficos en dashboard
   - **Estado:** ✅ Necesario

4. **10 requests** - `/admin/api/dashboard/metrics`
   - **Uso:** Métricas del dashboard administrativo
   - **Estado:** ✅ Necesario

5. **8 requests** - `/admin/api/notifications`
   - **Uso:** Notificaciones del sistema
   - **Estado:** ✅ Necesario

6. **5 requests** - `/login_admin`
   - **Uso:** Login de administrador
   - **Estado:** ✅ Necesario

7. **5 requests** - `/admin/dashboard`
   - **Uso:** Dashboard principal
   - **Estado:** ✅ Necesario

8. **5 requests** - `/`
   - **Uso:** Página principal
   - **Estado:** ✅ Necesario

9. **4 requests** - `/bartender`
   - **Uso:** Sistema de barra
   - **Estado:** ✅ Necesario

10. **3 requests** - `/caja/login`
    - **Uso:** Login de caja
    - **Estado:** ✅ Necesario

---

## 🗑️ ENDPOINTS NO UTILIZADOS O POCO UTILIZADOS

### APIs de Sistema (Probablemente no usadas)

#### `/api/health` y variantes
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Health check básico
- **Recomendación:** ⚠️ Mantener (útil para monitoreo)

#### `/api/system/health`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Health check completo
- **Recomendación:** ⚠️ Mantener (útil para monitoreo)

#### `/api/system/cache/stats`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas de cache
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/api/system/performance/stats`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas de rendimiento
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/api/system/csv/stats`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas de CSV
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/api/system/info`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Información del sistema (admin only)
- **Recomendación:** ⚠️ Mantener (útil para debugging)

#### `/api/system/export/logs`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Exportar logs en CSV
- **Recomendación:** ❌ **ELIMINAR** (no se usa, hay `/admin/export/csv`)

#### `/api/system/circuit-breakers`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estado de circuit breakers
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/api/health/detailed`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Health check detallado
- **Recomendación:** ⚠️ Mantener (útil para monitoreo avanzado)

#### `/api/dashboard/stats`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas para dashboard
- **Recomendación:** ❌ **ELIMINAR** (duplicado de `/admin/api/dashboard/metrics`)

#### `/api/sale-details/<sale_id>`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Detalles de venta
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

### APIs de Agente (Probablemente no usadas)

#### `/api/v1/agent/public-info/today`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Info pública del evento de hoy para agente
- **Recomendación:** ⚠️ Mantener (puede usarse por bot externo)

#### `/api/v1/agent/public-info/date`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Info pública por fecha
- **Recomendación:** ⚠️ Mantener (puede usarse por bot externo)

#### `/api/v1/agent/public-info/upcoming`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Eventos próximos
- **Recomendación:** ⚠️ Mantener (puede usarse por bot externo)

#### `/api/v1/agent/programacion/month/public`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Programación mensual pública
- **Recomendación:** ⚠️ Mantener (puede usarse por bot externo)

#### `/api/v1/agent/programacion/month/internal`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Programación mensual interna
- **Recomendación:** ⚠️ Mantener (puede usarse por bot externo)

### APIs de Servicios (Probablemente no usadas)

#### `/api/services/status`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estado de servicios
- **Recomendación:** ❌ **ELIMINAR** (duplicado de `/admin/api/services/status`)

#### `/api/services/restart`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Reiniciar servicio
- **Recomendación:** ❌ **ELIMINAR** (duplicado de `/admin/service/restart`)

#### `/api/services/postfix/queue`
- **Definido en:** `app/routes/api_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Cola de correo Postfix
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

### APIs de Debug (No usadas en producción)

#### `/debug/errors`
- **Definido en:** `app/routes/debug_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Panel de errores
- **Recomendación:** ❌ **ELIMINAR** (solo para desarrollo)

#### `/debug/errors/export`
- **Definido en:** `app/routes/debug_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Exportar errores
- **Recomendación:** ❌ **ELIMINAR** (solo para desarrollo)

#### `/debug/errors` (POST)
- **Definido en:** `app/routes/debug_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Recibir errores del cliente
- **Recomendación:** ❌ **ELIMINAR** (solo para desarrollo)

### APIs de Recetas (Probablemente no usadas)

#### `/recipe/<product_name>`
- **Definido en:** `app/routes/recipe_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Obtener receta de producto
- **Recomendación:** ⚠️ Mantener (puede usarse por app móvil)

#### `/recipe/all`
- **Definido en:** `app/routes/recipe_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Obtener todas las recetas
- **Recomendación:** ⚠️ Mantener (puede usarse para sincronización)

### APIs de Productos (Probablemente no usadas directamente)

#### `/product/api/search`
- **Definido en:** `app/routes/product_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Buscar productos (autocompletado)
- **Recomendación:** ⚠️ Mantener (puede usarse por frontend)

### APIs de TPV Dashboard (Probablemente no usadas)

#### `/tpv/dashboard`
- **Definido en:** `app/routes/tpv_dashboard_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Dashboard de monitoreo TPV
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/tpv/api/status`
- **Definido en:** `app/routes/tpv_dashboard_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estado de TPVs
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

#### `/tpv/api/<tpv_id>/stats`
- **Definido en:** `app/routes/tpv_dashboard_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas de TPV
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

### APIs de Monitoreo (Probablemente no usadas)

#### `/api/monitoring/stats`
- **Definido en:** `app/routes/monitoring_routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Estadísticas de monitoreo
- **Recomendación:** ❌ **ELIMINAR** (duplicado de `/admin/api/monitoreo/status`)

### APIs de Instagram (Probablemente no usadas)

#### Todas las rutas en `app/routes_instagram.py`
- **Uso en logs:** 0 requests
- **Propósito:** Integración con Instagram
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

### APIs de Admin (Algunas no usadas)

#### `/admin/pos_stats`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Redirigir a dashboard (módulo eliminado)
- **Recomendación:** ❌ **ELIMINAR** (solo redirección innecesaria)

#### `/admin/api/register/toggle`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** API deshabilitada (módulo eliminado)
- **Recomendación:** ❌ **ELIMINAR** (ya está deshabilitada)

#### `/admin/scanner`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Redirigir al scanner
- **Recomendación:** ⚠️ Mantener (redirección útil)

#### `/admin/export/csv`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Exportar logs en CSV
- **Recomendación:** ⚠️ Mantener (útil para admin)

#### `/admin/area`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Propósito:** Alias de admin_logs
- **Recomendación:** ⚠️ Mantener (compatibilidad)

#### `/admin/api/sync/*`
- **Definido en:** `app/routes.py`
- **Uso en logs:** 0 requests
- **Endpoints:**
  - `/admin/api/sync/start`
  - `/admin/api/sync/status`
  - `/admin/api/sync/tables`
- **Recomendación:** ❌ **ELIMINAR** (no se usa)

---

## 📋 RESUMEN DE RECOMENDACIONES

### Endpoints a Eliminar (Alta Confianza)

1. **APIs de Sistema no usadas:**
   - `/api/system/cache/stats`
   - `/api/system/performance/stats`
   - `/api/system/csv/stats`
   - `/api/system/circuit-breakers`
   - `/api/dashboard/stats`
   - `/api/sale-details/<sale_id>`

2. **APIs de Servicios duplicadas:**
   - `/api/services/status` (usar `/admin/api/services/status`)
   - `/api/services/restart` (usar `/admin/service/restart`)
   - `/api/services/postfix/queue`

3. **APIs de Debug:**
   - `/debug/errors` (GET y POST)
   - `/debug/errors/export`

4. **APIs de TPV Dashboard:**
   - `/tpv/dashboard`
   - `/tpv/api/status`
   - `/tpv/api/<tpv_id>/stats`

5. **APIs de Monitoreo duplicadas:**
   - `/api/monitoring/stats` (usar `/admin/api/monitoreo/status`)

6. **APIs de Instagram:**
   - Todas las rutas en `app/routes_instagram.py`

7. **APIs de Admin no usadas:**
   - `/admin/pos_stats`
   - `/admin/api/register/toggle`
   - `/admin/api/sync/*` (3 endpoints)

### Endpoints a Mantener (Útiles o Potencialmente Usados)

1. **Health Checks:**
   - `/api/health`
   - `/api/system/health`
   - `/api/health/detailed`
   - `/api/system/info`

2. **APIs de Agente/Bot:**
   - `/api/v1/agent/*` (pueden usarse por bot externo)
   - `/api/v1/public/evento/*` (públicas)

3. **APIs de Recetas:**
   - `/recipe/*` (pueden usarse por app móvil)

4. **APIs de Productos:**
   - `/product/api/search` (puede usarse por frontend)

---

## 🚀 OPTIMIZACIONES RECOMENDADAS

### 1. Eliminar Endpoints No Utilizados
- **Impacto:** Reducir superficie de ataque, simplificar código
- **Endpoints a eliminar:** ~20 endpoints
- **Ahorro estimado:** ~5-10% de código de rutas

### 2. Optimizar Polling del Agente
- **Problema actual:** 724 requests en 2000 (36% del tráfico)
- **Solución:** Implementar WebSockets o Server-Sent Events
- **Impacto:** Reducir tráfico en ~70%

### 3. Reducir 404s
- **Problema:** 286 requests 404 (29% del tráfico)
- **Causas probables:**
  - Bots buscando archivos comunes (wp-config.php, .env, etc.)
  - Requests mal formadas
- **Solución:** Mejorar manejo de errores y logging

### 4. Optimizar Gunicorn
- **Actual:** 4 workers con eventlet
- **Recomendación:** Considerar aumentar a 6-8 workers si hay más tráfico
- **Nota:** Actualmente no es necesario (CPU idle 98%)

### 5. Implementar Caching
- **Endpoints candidatos:**
  - `/admin/api/dashboard/metrics`
  - `/admin/api/notifications`
  - `/admin/equipo/api/cargos`
- **Impacto:** Reducir carga en base de datos

---

## 📊 MÉTRICAS ACTUALES

**Rendimiento del Servidor:**
- ✅ CPU: 0-2% uso (excelente)
- ✅ Memoria: 11% uso (excelente)
- ✅ Disco: 38% uso (adecuado)
- ✅ I/O: Mínimo (excelente)

**Tráfico HTTP:**
- ⚠️ 404s: 29% (alto, pero muchos son bots)
- ⚠️ 400s: 11% (moderado)
- ✅ 200s: 55% (normal)
- ✅ Rate limiting: 2% (mejoró después del fix)

**Endpoints:**
- Total definidos: ~150+
- Activamente usados: ~30-40
- No utilizados: ~20-30 (candidatos a eliminar)

---

## ✅ ACCIONES INMEDIATAS

1. **Eliminar endpoints no utilizados** (lista arriba)
2. **Monitorear logs** para confirmar que no se usan
3. **Implementar mejor manejo de 404s** (evitar logging excesivo)
4. **Considerar WebSockets** para el agente Getnet (reducir polling)

---

**Nota:** Antes de eliminar endpoints, verificar:
- Si son usados por aplicaciones móviles o externas
- Si son parte de integraciones futuras planificadas
- Si tienen documentación que indique uso previsto










