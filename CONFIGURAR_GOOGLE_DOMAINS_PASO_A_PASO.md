# 🚀 CONFIGURAR GOOGLE DOMAINS - PASO A PASO

**Dominio:** stvaldivia.cl  
**IP de la VM:** `34.176.68.46`  
**URL Google Domains:** https://domains.google.com

---

## 📋 INSTRUCCIONES PASO A PASO

### PASO 1: Acceder a Google Domains
1. Abre tu navegador y ve a: **https://domains.google.com**
2. Inicia sesión con tu cuenta de Google
3. En la lista de dominios, busca y haz clic en **stvaldivia.cl**

### PASO 2: Ir a la Sección DNS
1. En el menú lateral izquierdo, busca y haz clic en **"DNS"**
2. Desplázate hasta la sección **"Registros de recursos personalizados"** o **"Custom resource records"**
3. Esta sección muestra una tabla con los registros DNS actuales

### PASO 3: Verificar/Editar Registros Existentes
1. Busca si ya existen registros A para:
   - `@` (o `stvaldivia.cl`)
   - `www`
2. **Si existen y apuntan a otra IP:**
   - Haz clic en el ícono de editar (lápiz) ✏️
   - Cambia la IP a: `34.176.68.46`
   - Guarda los cambios
3. **Si no existen:** Continúa al siguiente paso

### PASO 4: Crear Registro A para stvaldivia.cl (dominio raíz)
1. Haz clic en el botón **"Agregar registro"** o **"Add record"**
2. Se abrirá un formulario. Completa:
   - **Tipo de registro:** Selecciona `A` del menú desplegable
   - **Nombre de host:** Escribe `@` (esto representa el dominio raíz stvaldivia.cl)
   - **Dirección IPv4:** Escribe `34.176.68.46`
   - **TTL:** Deja `3600` (1 hora) o el valor por defecto
3. Haz clic en **"Guardar"** o **"Save"**

### PASO 5: Crear Registro A para www.stvaldivia.cl
1. Haz clic nuevamente en **"Agregar registro"** o **"Add record"**
2. Completa el formulario:
   - **Tipo de registro:** Selecciona `A`
   - **Nombre de host:** Escribe `www`
   - **Dirección IPv4:** Escribe `34.176.68.46`
   - **TTL:** Deja `3600` o el valor por defecto
3. Haz clic en **"Guardar"** o **"Save"**

---

## ✅ VERIFICAR CONFIGURACIÓN

Después de guardar, deberías ver en la tabla algo como:

```
Tipo    Nombre de host    Dirección IPv4      TTL
A       @                 34.176.68.46        3600
A       www               34.176.68.46        3600
```

---

## ⏱️ PROPAGACIÓN DNS

- **Cambios guardados:** Inmediato
- **Propagación DNS:** 5-30 minutos (típicamente 10-15 minutos)
- **Verificación:** Espera 10-15 minutos y luego prueba

---

## 🔍 VERIFICAR DESDE TERMINAL

Después de esperar 10-15 minutos, verifica:

```bash
# Verificar que DNS apunta correctamente
dig stvaldivia.cl +short
# Debe mostrar: 34.176.68.46

dig www.stvaldivia.cl +short
# Debe mostrar: 34.176.68.46

# Probar acceso HTTP
curl -I http://stvaldivia.cl
# Debe responder: HTTP/1.1 200 OK

# Probar endpoint API
curl http://stvaldivia.cl/api/v1/public/evento/hoy
# Debe responder: {"evento":null,"status":"no_event"}
```

---

## 🎯 RESULTADO ESPERADO

Una vez que DNS esté propagado:

✅ **http://stvaldivia.cl** → Carga la aplicación Flask  
✅ **http://www.stvaldivia.cl** → Carga la aplicación Flask  
✅ **http://stvaldivia.cl/api/v1/public/evento/hoy** → Responde JSON

---

## ⚠️ NOTAS IMPORTANTES

1. **No cambies los servidores DNS en NIC.CL** - Déjalos como están (Google Domains)
2. **Solo crea registros A** - No necesitas CNAME, MX, TXT, etc. (a menos que los necesites para otros servicios)
3. **La IP debe ser exacta:** `34.176.68.46` (sin espacios, sin puntos al final)
4. **El servidor ya está listo** - Nginx está configurado para responder a stvaldivia.cl

---

## 🆘 SI ALGO NO FUNCIONA

### Si no ves la sección "Registros de recursos personalizados":
- Busca "DNS" en el menú lateral
- Puede estar en "Configuración DNS" o "DNS Settings"
- Algunas interfaces muestran "Resource records" o "Registros de recursos"

### Si el DNS no propaga después de 30 minutos:
1. Verifica que los registros están guardados correctamente en Google Domains
2. Verifica que la IP es exactamente `34.176.68.46`
3. Prueba desde diferentes ubicaciones:
   ```bash
   dig @8.8.8.8 stvaldivia.cl +short
   dig @1.1.1.1 stvaldivia.cl +short
   ```

### Si el dominio no carga pero DNS está correcto:
1. Verifica que el servidor está corriendo:
   ```bash
   # En la VM
   sudo systemctl status nginx
   sudo systemctl status flask_app
   ```

---

**IP para configurar:** `34.176.68.46`  
**URL Google Domains:** https://domains.google.com  
**Servidor listo:** ✅ Sí, esperando tráfico del dominio


