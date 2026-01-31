# 🌐 CONFIGURAR DNS EN NIC.CL PARA STVALDIVIA.CL

**Proveedor:** NIC.CL (Registro de dominios .cl)  
**IP de la VM:** `34.176.68.46`  
**Dominio:** stvaldivia.cl

---

## ⚠️ IMPORTANTE: RESTRICCIONES DE NIC.CL

NIC.CL solo permite **registros A (dirección IP)** directamente. No se pueden usar:
- ❌ CNAME para el dominio raíz (@)
- ❌ CNAME para www (debe ser registro A)
- ❌ Otros tipos de registros complejos

**Solución:** Usar registros A para ambos: `@` y `www`

## 🚫 NO CAMBIAR SERVIDORES NS

**IMPORTANTE:** Tu dominio ya tiene servidores DNS de NIC.CL configurados:
- A.NIC.CL
- B.NIC.CL
- C.NIC.CL

**NO necesitas cambiar los servidores de nombres (NS).** Si intentas cambiarlos y ves el error:
```
Nombre de host NS inválido
```

**Solución:** Ignora la sección de servidores NS y ve directamente a crear **registros A** en la zona DNS.

---

## 📋 PASO A PASO EN NIC.CL

### PASO 1: Acceder a NIC.CL
1. Ve a: **https://www.nic.cl**
2. Inicia sesión con tus credenciales
3. Accede al panel de administración de dominios
4. Busca el dominio **stvaldivia.cl**

### PASO 2: Ir a Configuración DNS
1. Busca la sección **"DNS"** o **"Zona DNS"** o **"Registros DNS"**
2. Puede estar en: **"Administración"** → **"DNS"** o **"Zona DNS"**
3. **⚠️ NO toques la sección "Servidores de Nombres" o "NS"** - Déjalos como están
4. Ve directamente a la sección de **"Registros"** o **"Registros A"**

### PASO 3: Eliminar Registros Existentes (si hay)
1. Busca registros A existentes para:
   - `@` o `stvaldivia.cl` (dominio raíz)
   - `www`
2. Si existen y apuntan a otra IP, **edítalos** o **elimínalos**

### PASO 4: Crear/Editar Registro A para stvaldivia.cl (dominio raíz)
1. Busca o crea un registro de tipo **A**
2. Configura:
   - **Nombre/Host:** `@` o `stvaldivia.cl` (depende de la interfaz)
   - **Tipo:** `A`
   - **Valor/Dirección:** `34.176.68.46`
   - **TTL:** `3600` (1 hora) o deja el default
3. Click en **"Guardar"** o **"Aplicar"**

### PASO 5: Crear/Editar Registro A para www.stvaldivia.cl
1. Crea otro registro de tipo **A**
2. Configura:
   - **Nombre/Host:** `www`
   - **Tipo:** `A`
   - **Valor/Dirección:** `34.176.68.46`
   - **TTL:** `3600` (1 hora) o deja el default
3. Click en **"Guardar"** o **"Aplicar"**

---

## 📸 EJEMPLO DE CONFIGURACIÓN

Después de configurar, deberías ver algo así:

```
Tipo    Nombre          Valor/Dirección    TTL
A       @               34.176.68.46       3600
A       www             34.176.68.46       3600
```

O en algunos paneles:

```
Host                Tipo    Dirección IP      TTL
stvaldivia.cl      A       34.176.68.46      3600
www.stvaldivia.cl  A       34.176.68.46      3600
```

---

## ✅ VERIFICAR CONFIGURACIÓN

### Esperar 5-30 minutos después de guardar
La propagación DNS puede tardar entre 5-30 minutos (generalmente 10-15 minutos).

### Verificar desde terminal:

```bash
# Verificar stvaldivia.cl
dig stvaldivia.cl +short
# Debe mostrar: 34.176.68.46

# Verificar www.stvaldivia.cl
dig www.stvaldivia.cl +short
# Debe mostrar: 34.176.68.46

# Verificar con nslookup
nslookup stvaldivia.cl
# Debe mostrar: 34.176.68.46
```

### Verificar acceso web:

```bash
# Probar acceso HTTP
curl -I http://stvaldivia.cl
# Debe responder: HTTP/1.1 200 OK

# Probar endpoint API
curl http://stvaldivia.cl/api/v1/public/evento/hoy
# Debe responder: {"evento":null,"status":"no_event"}
```

---

## 🔧 CONFIGURACIÓN EN EL SERVIDOR

El servidor ya está configurado para responder a:
- ✅ `stvaldivia.cl`
- ✅ `www.stvaldivia.cl`
- ✅ IP directa: `34.176.68.46`

**Nginx está listo** y esperando el tráfico del dominio.

---

## ⏱️ TIEMPO ESTIMADO

- **Guardar cambios en NIC.CL:** Inmediato
- **Propagación DNS:** 5-30 minutos (típicamente 10-15 minutos)
- **Verificación:** Una vez propagado, acceso inmediato

---

## 🎯 RESULTADO FINAL

Una vez que DNS esté propagado:

```bash
# Debe funcionar
curl http://stvaldivia.cl
# Respuesta: HTML de la aplicación

curl http://stvaldivia.cl/api/v1/public/evento/hoy
# Respuesta: {"evento":null,"status":"no_event"}

# En navegador
# http://stvaldivia.cl debe cargar
# http://www.stvaldivia.cl debe cargar
```

---

## ⚠️ TROUBLESHOOTING

### Error: "Nombre de host NS inválido"

**Causa:** Estás intentando cambiar los servidores de nombres (NS) cuando no es necesario.

**Solución:**
1. **NO cambies los servidores NS** - Déjalos como están (A.NIC.CL, B.NIC.CL, C.NIC.CL)
2. Ve directamente a la sección de **"Registros DNS"** o **"Zona DNS"**
3. Crea solo **registros A** (no toques NS, MX, CNAME, etc.)
4. Los registros A que necesitas:
   - `@` → `34.176.68.46`
   - `www` → `34.176.68.46`

### Si el DNS no propaga después de 30 minutos:

1. **Verificar en NIC.CL:**
   - Confirma que los registros A están guardados correctamente
   - Verifica que la IP es exactamente: `34.176.68.46`

2. **Verificar desde diferentes ubicaciones:**
   ```bash
   # Usar diferentes servidores DNS
   dig @8.8.8.8 stvaldivia.cl +short
   dig @1.1.1.1 stvaldivia.cl +short
   ```

3. **Limpiar cache DNS local:**
   ```bash
   # En macOS
   sudo dscacheutil -flushcache
   
   # En Linux
   sudo systemd-resolve --flush-caches
   ```

### Si el dominio no carga pero el DNS está correcto:

1. Verificar que Nginx está corriendo:
   ```bash
   sudo systemctl status nginx
   ```

2. Verificar logs de Nginx:
   ```bash
   sudo tail -f /var/log/nginx/error.log
   ```

3. Verificar que el firewall permite tráfico HTTP:
   ```bash
   sudo ufw status
   ```

---

## 📊 CHECKLIST

- [ ] Accedido a NIC.CL
- [ ] Navegado a sección DNS/Zona DNS
- [ ] Eliminado/Editado registros A antiguos (si existen)
- [ ] Creado/Editado registro A: `@` → `34.176.68.46`
- [ ] Creado/Editado registro A: `www` → `34.176.68.46`
- [ ] Guardado cambios
- [ ] Esperado 10-15 minutos
- [ ] Verificado con `dig stvaldivia.cl +short`
- [ ] Verificado que muestra `34.176.68.46`
- [ ] Probado `curl http://stvaldivia.cl`
- [ ] Probado `curl http://stvaldivia.cl/api/v1/public/evento/hoy`

---

## 📝 NOTAS ADICIONALES

### Sobre NIC.CL:
- NIC.CL es el registro oficial de dominios .cl
- Tiene restricciones más estrictas que otros registradores
- Solo permite registros A directamente (no CNAME para raíz)
- La propagación puede ser ligeramente más lenta que otros proveedores

### Próximos pasos (después de DNS):
1. **Configurar SSL/HTTPS** con Let's Encrypt (Certbot)
2. **Redirección HTTP → HTTPS**
3. **Optimizaciones de rendimiento**

---

**IP para DNS:** `34.176.68.46`  
**URL de NIC.CL:** https://www.nic.cl  
**Zona VM:** southamerica-west1-a  
**Proyecto:** stvaldivia

