# 🔒 Content Security Policy (CSP) - Documentación

**Fecha:** 2025-01-15 (actualizado)  
**Ubicación:** `app/helpers/security_headers.py`

---

## ⚠️ CAMBIO IMPORTANTE: SELF-HOSTING DE LIBRERÍAS

**Desde 2025-01-15:** Todas las librerías JavaScript están self-hosted en `/app/static/vendor/`:
- ✅ Socket.IO 4.5.4 → `app/static/vendor/socket.io.min.js`
- ✅ Chart.js 4.4.0 → `app/static/vendor/chart.umd.min.js`
- ✅ QRCode.js 1.0.0 → `app/static/vendor/qrcode.min.js`

**Razón:** Eliminar dependencias de CDNs externos y fortalecer la CSP (solo `'self'`).

---

## CSP ACTUAL APLICADA

### PRODUCCIÓN (is_production = True)

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; connect-src 'self' ws: wss: https://stvaldivia.cl wss://stvaldivia.cl; frame-ancestors 'self';
```

### DESARROLLO (is_production = False)

```http
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com data:; connect-src 'self' ws: wss: http://localhost:* ws://localhost:* wss://localhost:* https://stvaldivia.cl wss://stvaldivia.cl; frame-ancestors 'self';
```

---

## DESGLOSE POR DIRECTIVA

### `default-src 'self'`
- **Motivo:** Política por defecto restrictiva, solo permite recursos del mismo origen
- **Permite:** Recursos desde el mismo dominio (stvaldivia.cl)

### `script-src`
**Valores permitidos:**
- `'self'` - Scripts del mismo origen
- `'unsafe-inline'` - Scripts inline (necesario para templates Jinja2)
- `https://cdn.jsdelivr.net` - CDN para Chart.js y otras librerías
- `https://cdnjs.cloudflare.com` - CDN alternativo para Socket.IO y otras librerías
- `https://cdn.socket.io` - CDN oficial de Socket.IO

**Motivo de cada origen:**
- **cdn.jsdelivr.net:** Chart.js y otras librerías JavaScript
- **cdnjs.cloudflare.com:** Socket.IO 4.5.0 usado en `base.html`
- **cdn.socket.io:** Socket.IO 4.5.4 usado en varios templates admin

**⚠️ Nota:** `'unsafe-inline'` es necesario porque los templates Jinja2 generan scripts inline. Si se elimina, se romperían funcionalidades críticas.

### `style-src`
**Valores permitidos:**
- `'self'` - Estilos del mismo origen (incluye `/static/css/`)
- `'unsafe-inline'` - Estilos inline (necesario para estilos dinámicos)

**Motivo:** Permite estilos inline generados dinámicamente. Todos los estilos están en `/static/css/`.

### `img-src`
**Valores permitidos:**
- `'self'` - Imágenes del mismo origen (incluye `/static/img/`)
- `data:` - Imágenes en base64 (usado para logos y avatares)

**Motivo:** Permite imágenes del mismo origen y datos inline. **Cambio:** Eliminado `https:` para mayor seguridad (solo imágenes propias).

### `font-src`
**Valores permitidos:**
- `'self'` - Fuentes del mismo origen
- `https://cdn.jsdelivr.net` - Fuentes desde CDN
- `https://cdnjs.cloudflare.com` - Fuentes desde CDN alternativo
- `data:` - Fuentes en base64

**Motivo:** Permite cargar fuentes desde CDNs y datos inline.

### `connect-src` (CRÍTICO PARA SOCKET.IO)

#### PRODUCCIÓN:
```
'self' ws: wss: https://stvaldivia.cl wss://stvaldivia.cl
```

**Valores permitidos:**
- `'self'` - Conexiones al mismo origen (Socket.IO usa el mismo dominio)
- `ws:` - Protocolo WebSocket (cualquier origen con ws://)
- `wss:` - Protocolo WebSocket seguro (cualquier origen con wss://)
- `https://stvaldivia.cl` - Conexiones HTTPS al dominio de producción
- `wss://stvaldivia.cl` - Conexiones WebSocket seguras al dominio de producción

**Motivo:**
- Socket.IO automáticamente usa `wss://` cuando la página está en HTTPS
- `ws:` y `wss:` como esquemas permiten conexiones WebSocket desde cualquier origen (necesario para Socket.IO)
- `https://stvaldivia.cl` permite conexiones HTTP/HTTPS al dominio

#### DESARROLLO:
```
'self' ws: wss: http://localhost:* ws://localhost:* wss://localhost:* https://stvaldivia.cl wss://stvaldivia.cl
```

**Valores adicionales en desarrollo:**
- `http://localhost:*` - Conexiones HTTP a localhost (cualquier puerto)
- `ws://localhost:*` - Conexiones WebSocket a localhost (cualquier puerto)
- `wss://localhost:*` - Conexiones WebSocket seguras a localhost (cualquier puerto)

**Motivo:** Permite desarrollo local con Socket.IO en diferentes puertos (5000, 5001, etc.).

### `frame-ancestors 'self'`
- **Motivo:** Previene clickjacking, solo permite que la página sea embebida en el mismo origen

---

## DIFERENCIAS DEV vs PROD

### Cómo se detecta el entorno:

```python
is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
```

### Diferencias:

| Directiva | Desarrollo | Producción |
|-----------|-------------|------------|
| `connect-src` | Incluye `localhost:*` (ws/http) | Solo dominio real + ws/wss |
| Razón | Desarrollo local necesita localhost | Seguridad: no permitir conexiones a localhost en producción |

---

## SOCKET.IO Y CSP

### Cómo funciona Socket.IO:

1. **Cliente se conecta:** `io('/admin_stats', { transports: ['websocket', 'polling'] })`
2. **Socket.IO detecta HTTPS:** Automáticamente usa `wss://` si la página está en HTTPS
3. **Conexión:** Se conecta al mismo origen (`'self'`) usando WebSocket seguro

### Verificación:

- ✅ Socket.IO usa `wss://stvaldivia.cl` en producción (automático)
- ✅ Socket.IO usa `ws://localhost:*` en desarrollo (automático)
- ✅ CSP permite ambos esquemas (`ws:` y `wss:`)
- ✅ CSP permite conexiones al mismo origen (`'self'`)

---

## CÓMO MODIFICAR LA CSP EN EL FUTURO

### Ubicación:
`app/helpers/security_headers.py` - Función `setup_security_headers()`

### Pasos:

1. **Identificar el recurso bloqueado:**
   - Abrir DevTools (F12)
   - Ir a pestaña "Console"
   - Buscar errores de CSP (rojos)
   - Leer el mensaje: `Refused to connect to '...' because it violates the following Content Security Policy directive: ...`

2. **Determinar la directiva correcta:**
   - `script-src` - Para scripts JavaScript
   - `style-src` - Para estilos CSS
   - `connect-src` - Para conexiones (AJAX, WebSocket, fetch)
   - `img-src` - Para imágenes
   - `font-src` - Para fuentes
   - `media-src` - Para audio/video
   - `object-src` - Para plugins (Flash, etc.)

3. **Agregar el origen necesario:**
   ```python
   # Ejemplo: agregar nuevo CDN a script-src
   script_src = "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://cdn.socket.io https://nuevo-cdn.com"
   ```

4. **Probar:**
   - Limpiar caché del navegador (`Ctrl+Shift+R`)
   - Verificar que el error desaparece
   - Confirmar que la funcionalidad funciona

5. **Documentar:**
   - Actualizar este archivo (`SECURITY_CSP.md`)
   - Agregar motivo del nuevo origen
   - Especificar si aplica solo a DEV o PROD

---

## ORÍGENES PERMITIDOS - RESUMEN

### Scripts (script-src):
- ✅ `'self'` - Scripts del mismo origen
- ✅ `https://cdn.jsdelivr.net` - Chart.js y librerías
- ✅ `https://cdnjs.cloudflare.com` - Socket.IO y librerías alternativas
- ✅ `https://cdn.socket.io` - Socket.IO oficial

### Estilos (style-src):
- ✅ `'self'` - Estilos del mismo origen
- ✅ `https://cdn.jsdelivr.net` - Estilos de librerías
- ✅ `https://cdnjs.cloudflare.com` - Estilos alternativos

### Conexiones (connect-src):
- ✅ `'self'` - Socket.IO al mismo origen
- ✅ `ws:` / `wss:` - WebSocket (cualquier origen)
- ✅ `https://stvaldivia.cl` - HTTPS al dominio
- ✅ `wss://stvaldivia.cl` - WebSocket seguro al dominio
- ✅ `localhost:*` (solo DEV) - Desarrollo local

### Imágenes (img-src):
- ✅ `'self'` - Imágenes del mismo origen
- ✅ `data:` - Imágenes base64
- ✅ `https:` - Cualquier imagen HTTPS

### Fuentes (font-src):
- ✅ `'self'` - Fuentes del mismo origen
- ✅ `https://cdn.jsdelivr.net` - Fuentes desde CDN
- ✅ `https://cdnjs.cloudflare.com` - Fuentes alternativas
- ✅ `data:` - Fuentes base64

---

## SEGURIDAD

### ✅ Buenas prácticas aplicadas:

1. **Política restrictiva por defecto:** `default-src 'self'`
2. **Orígenes específicos:** No se usa `*` (wildcard) excepto en esquemas (`ws:`, `wss:`)
3. **Diferenciación DEV/PROD:** Desarrollo permite localhost, producción no
4. **Frame protection:** `frame-ancestors 'self'` previene clickjacking
5. **MIME type protection:** `X-Content-Type-Options: nosniff`
6. **XSS protection:** `X-XSS-Protection: 1; mode=block`

### ⚠️ Compromisos de seguridad:

1. **`'unsafe-inline'` en scripts:**
   - **Razón:** Templates Jinja2 generan scripts inline
   - **Riesgo:** Permite ejecución de scripts inline (XSS potencial)
   - **Mitigación:** Validación de entrada en backend, sanitización de datos

2. **`'unsafe-inline'` en estilos:**
   - **Razón:** Estilos dinámicos generados por JavaScript
   - **Riesgo:** Permite estilos inline (menor riesgo que scripts)
   - **Mitigación:** Validación de datos antes de aplicar estilos

3. **`https:` en img-src:**
   - **Razón:** Necesario para avatares y logos externos
   - **Riesgo:** Permite imágenes desde cualquier origen HTTPS
   - **Mitigación:** Validación de URLs en backend antes de mostrar

---

## TROUBLESHOOTING

### Error: "Refused to connect to 'wss://stvaldivia.cl'"

**Causa:** CSP no permite conexiones WebSocket al dominio.

**Solución:** Verificar que `connect-src` incluya:
- `wss://stvaldivia.cl` (específico)
- `wss:` (esquema general)

### Error: "Refused to load script from 'https://cdn.socket.io'"

**Causa:** CSP no permite scripts desde ese CDN.

**Solución:** Agregar `https://cdn.socket.io` a `script-src`.

### Error: "Refused to execute inline script"

**Causa:** CSP no permite scripts inline.

**Solución:** Verificar que `script-src` incluya `'unsafe-inline'` (ya está incluido).

### Socket.IO no se conecta en producción

**Causa:** CSP bloquea conexiones WebSocket.

**Solución:** Verificar que `connect-src` incluya:
- `'self'` (mismo origen)
- `wss:` (WebSocket seguro)
- `wss://stvaldivia.cl` (dominio específico)

---

## REFERENCIAS

- [MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Socket.IO: Client Configuration](https://socket.io/docs/v4/client-options/)
- [OWASP: Content Security Policy](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)

---

## HISTORIAL DE CAMBIOS

### 2025-01-15
- ✅ Actualizada CSP para permitir Socket.IO y CDNs necesarios
- ✅ Diferenciación DEV vs PROD en `connect-src`
- ✅ Agregado `ws:` y `wss:` como esquemas permitidos
- ✅ Documentación completa creada

