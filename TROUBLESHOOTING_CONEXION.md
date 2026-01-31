# Solución de Problemas de Conexión - stvaldivia.cl

## Problema: ERR_CONNECTION_REFUSED

Si estás viendo "ERR_CONNECTION_REFUSED" en el navegador, sigue estos pasos:

### 1. Verificar que estás usando HTTP (no HTTPS)

**IMPORTANTE:** El sitio actualmente solo funciona con HTTP, NO HTTPS.

**URL correcta:**
- ✅ `http://www.stvaldivia.cl` 
- ✅ `http://stvaldivia.cl`
- ❌ `https://www.stvaldivia.cl` (NO funciona todavía)

### 2. Limpiar caché del navegador

1. Presiona `Cmd + Shift + Delete` (Mac) o `Ctrl + Shift + Delete` (Windows/Linux)
2. Selecciona "Imágenes y archivos en caché"
3. Limpia la caché

### 3. Probar en modo incógnito

- Chrome/Edge: `Cmd + Shift + N` (Mac) o `Ctrl + Shift + N` (Windows)
- Firefox: `Cmd + Shift + P` (Mac) o `Ctrl + Shift + P` (Windows)
- Safari: `Cmd + Shift + N`

### 4. Verificar DNS

Abre una terminal y ejecuta:
```bash
nslookup www.stvaldivia.cl
```

Deberías ver: `34.176.144.166`

### 5. Probar directamente con la IP

Intenta acceder directamente: `http://34.176.144.166`

### 6. Verificar desde terminal

```bash
curl -I http://www.stvaldivia.cl
```

Deberías ver: `HTTP/1.1 200 OK`

### 7. Deshabilitar extensiones del navegador

Algunas extensiones (como ad blockers o VPNs) pueden bloquear conexiones.

### 8. Verificar firewall local

Asegúrate de que tu firewall local no esté bloqueando conexiones salientes al puerto 80.

---

## Estado del Servidor

- **IP:** 34.176.144.166
- **HTTP (Puerto 80):** ✅ Funcionando
- **HTTPS (Puerto 443):** ❌ No configurado todavía
- **Estado:** ✅ Operativo

## Contacto

Si el problema persiste después de seguir estos pasos, verifica:
1. La consola del navegador (F12 → Console) para ver errores
2. La pestaña Network (F12 → Network) para ver qué está pasando

