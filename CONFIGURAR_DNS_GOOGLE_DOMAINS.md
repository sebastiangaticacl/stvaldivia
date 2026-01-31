# 🌐 CONFIGURAR DNS EN GOOGLE DOMAINS

**Proveedor:** Google Domains  
**IP de la VM:** `34.176.68.46`

---

## 📋 PASO A PASO

### PASO 1: Acceder a Google Domains
1. Ve a: **https://domains.google.com**
2. Inicia sesión con tu cuenta de Google
3. Busca el dominio **stvaldivia.cl** en la lista
4. Click en el dominio

### PASO 2: Ir a Configuración DNS
1. En el menú lateral, click en **"DNS"**
2. Busca la sección **"Registros de recursos personalizados"** o **"Custom resource records"**

### PASO 3: Eliminar Registros Existentes (si hay)
1. Busca registros A existentes para:
   - `@` o `stvaldivia.cl`
   - `www`
2. Si existen, elimínalos o edítalos

### PASO 4: Crear Registro A para stvaldivia.cl
1. Click en **"Agregar registro"** o **"Add record"**
2. Configura:
   - **Tipo de registro:** `A`
   - **Nombre de host:** `@` (esto representa el dominio raíz)
   - **Dirección IPv4:** `34.176.68.46`
   - **TTL:** `3600` (1 hora) o deja el default
3. Click en **"Guardar"** o **"Save"**

### PASO 5: Crear Registro A para www.stvaldivia.cl
1. Click en **"Agregar registro"** o **"Add record"** nuevamente
2. Configura:
   - **Tipo de registro:** `A`
   - **Nombre de host:** `www`
   - **Dirección IPv4:** `34.176.68.46`
   - **TTL:** `3600` (1 hora) o deja el default
3. Click en **"Guardar"** o **"Save"**

---

## 📸 EJEMPLO VISUAL

Después de configurar, deberías ver algo así:

```
Tipo    Nombre de host    Dirección IPv4        TTL
A       @                 34.120.239.226        3600
A       www               34.120.239.226        3600
```

---

## ✅ VERIFICAR CONFIGURACIÓN

### Esperar 5-10 minutos después de guardar

Luego verifica desde terminal:

```bash
# Verificar stvaldivia.cl
dig stvaldivia.cl +short
# Debe mostrar: 34.120.239.226

# Verificar www.stvaldivia.cl
dig www.stvaldivia.cl +short
# Debe mostrar: 34.120.239.226
```

### Verificar en Google Domains
1. Vuelve a la sección DNS
2. Verifica que los registros aparecen correctamente
3. Deberías ver ambos registros A con la IP `34.120.239.226`

---

## ⏱️ TIEMPO ESTIMADO

- **Guardar cambios:** Inmediato
- **Propagación DNS:** 5-30 minutos (generalmente 5-10 minutos)
- **SSL aprovisionamiento:** 10-60 minutos después de que DNS esté correcto

---

## 🔍 VERIFICAR ESTADO SSL

Después de que DNS esté configurado, verifica el certificado SSL:

```bash
gcloud compute ssl-certificates describe stvaldivia-cert --global --format="value(managed.status)"
```

**Estados:**
- `PROVISIONING` - Aún aprovisionándose (esperar)
- `ACTIVE` - ✅ Listo y funcionando
- `FAILED` - ❌ Verificar DNS

---

## 🎯 RESULTADO FINAL

Una vez que DNS esté propagado y SSL aprovisionado:

```bash
# Debe funcionar
curl https://stvaldivia.cl/api/v1/public/evento/hoy
# Respuesta: {"evento":null,"status":"no_event"}

# En navegador
# https://stvaldivia.cl debe cargar
# https://www.stvaldivia.cl debe cargar
# Certificado SSL válido (candado verde)
```

---

## ⚠️ IMPORTANTE

### Si hay registros CNAME
Si ves registros CNAME para `@` o `www`, **elimínalos primero**. Los registros CNAME no pueden coexistir con registros A para el mismo nombre.

### Si hay otros registros A
Si hay otros registros A apuntando a otras IPs, elimínalos o cámbialos a `34.120.239.226`.

---

## 📊 CHECKLIST

- [ ] Accedido a Google Domains
- [ ] Navegado a sección DNS
- [ ] Eliminado registros A/CNAME antiguos (si existen)
- [ ] Creado registro A: `@` → `34.120.239.226`
- [ ] Creado registro A: `www` → `34.120.239.226`
- [ ] Guardado cambios
- [ ] Esperado 5-10 minutos
- [ ] Verificado con `dig stvaldivia.cl +short`
- [ ] Verificado que muestra `34.120.239.226`
- [ ] Esperado aprovisionamiento SSL
- [ ] Probado https://stvaldivia.cl

---

**IP para DNS:** `34.176.68.46`

**URL de Google Domains:** https://domains.google.com

