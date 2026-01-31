# 🌐 CONFIGURAR DNS PARA stvaldivia.cl

**IP del Load Balancer:** `34.120.239.226`

---

## 📋 REGISTROS DNS NECESARIOS

Necesitas crear **2 registros A** en tu proveedor de DNS:

### Registro 1: stvaldivia.cl
- **Type:** A
- **Name:** `@` o `stvaldivia.cl` (depende del proveedor)
- **Value:** `34.120.239.226`
- **TTL:** `3600` (1 hora) o `600` (10 minutos)

### Registro 2: www.stvaldivia.cl
- **Type:** A
- **Name:** `www`
- **Value:** `34.120.239.226`
- **TTL:** `3600` (1 hora) o `600` (10 minutos)

---

## 🔍 PASO 1: IDENTIFICAR TU PROVEEDOR DE DNS

### Opción A: Verificar desde terminal
```bash
dig stvaldivia.cl NS +short
```

Esto mostrará los servidores de nombres (nameservers) que manejan tu dominio.

### Opción B: Verificar en whois
```bash
whois stvaldivia.cl | grep -i "name server"
```

---

## 📝 PASO 2: ACCEDER A TU PROVEEDOR DE DNS

Dependiendo de dónde compraste el dominio, accede a:

### Proveedores Comunes:

**Google Domains:**
- https://domains.google.com
- Ve a "DNS" → "Registros de recursos personalizados"

**Namecheap:**
- https://www.namecheap.com
- Ve a "Domain List" → Click en "Manage" → "Advanced DNS"

**GoDaddy:**
- https://www.godaddy.com
- Ve a "My Products" → "DNS" → "Manage DNS"

**Cloudflare:**
- https://dash.cloudflare.com
- Selecciona tu dominio → "DNS" → "Records"

**Google Cloud DNS:**
- https://console.cloud.google.com/net-services/dns/zones
- Selecciona la zona → "Add record set"

**Otros proveedores:**
- Busca en tu panel de control: "DNS", "Zone Records", "DNS Management"

---

## 🎯 PASO 3: CREAR REGISTROS A

### Instrucciones Generales:

1. **Busca la sección de registros DNS** (puede llamarse "DNS Records", "Zone Records", "Resource Records")

2. **Elimina registros A existentes** (si hay):
   - Busca registros A para `stvaldivia.cl` o `@`
   - Busca registros A para `www`
   - Elimínalos o edítalos

3. **Crea el primer registro:**
   - Click en **"Add Record"** o **"Create Record"**
   - **Type:** Selecciona **A**
   - **Name:** 
     - Algunos proveedores: `@` o `stvaldivia.cl`
     - Otros: deja vacío o pon `@`
   - **Value/Points to:** `34.120.239.226`
   - **TTL:** `3600` o `Auto`
   - Click **"Save"** o **"Add"**

4. **Crea el segundo registro:**
   - Click en **"Add Record"** o **"Create Record"**
   - **Type:** Selecciona **A**
   - **Name:** `www`
   - **Value/Points to:** `34.120.239.226`
   - **TTL:** `3600` o `Auto`
   - Click **"Save"** o **"Add"**

---

## 📸 EJEMPLOS POR PROVEEDOR

### Google Domains
```
Type: A
Name: @
Data: 34.120.239.226
TTL: 3600

Type: A
Name: www
Data: 34.120.239.226
TTL: 3600
```

### Cloudflare
```
Type: A
Name: @
IPv4 address: 34.120.239.226
Proxy status: DNS only (naranja apagado)
TTL: Auto

Type: A
Name: www
IPv4 address: 34.120.239.226
Proxy status: DNS only (naranja apagado)
TTL: Auto
```

### Namecheap
```
Type: A Record
Host: @
Value: 34.120.239.226
TTL: Automatic

Type: A Record
Host: www
Value: 34.120.239.226
TTL: Automatic
```

---

## ✅ PASO 4: VERIFICAR CONFIGURACIÓN

### Esperar 5-10 minutos después de guardar

Luego verifica:

```bash
# Verificar stvaldivia.cl
dig stvaldivia.cl +short
# Debe mostrar: 34.120.239.226

# Verificar www.stvaldivia.cl
dig www.stvaldivia.cl +short
# Debe mostrar: 34.120.239.226

# Verificar con nslookup
nslookup stvaldivia.cl
# Debe mostrar: 34.120.239.226
```

### Si no funciona inmediatamente:
- Espera 5-30 minutos (propagación DNS)
- Verifica que guardaste los cambios
- Verifica que no hay otros registros A conflictivos

---

## ⚠️ IMPORTANTE

### SSL Certificate
El certificado SSL **NO se aprovisionará** hasta que DNS esté configurado correctamente y apunte a `34.120.239.226`.

**Verificar estado del certificado:**
```bash
gcloud compute ssl-certificates describe stvaldivia-cert --global --format="value(managed.status)"
```

**Estados:**
- `PROVISIONING` - Esperando DNS
- `ACTIVE` - ✅ Listo (después de DNS)
- `FAILED` - ❌ DNS incorrecto

---

## 🔧 TROUBLESHOOTING

### DNS no resuelve a la IP correcta
1. Verifica que guardaste los cambios
2. Espera más tiempo (hasta 24 horas en casos raros)
3. Verifica que no hay registros CNAME conflictivos
4. Verifica que no hay otros registros A

### Certificado SSL no se aprovisiona
1. Verifica que DNS apunta correctamente:
   ```bash
   dig stvaldivia.cl +short
   # Debe ser: 34.120.239.226
   ```
2. Espera 10-60 minutos después de que DNS esté correcto
3. Verifica estado:
   ```bash
   gcloud compute ssl-certificates describe stvaldivia-cert --global
   ```

### Error 502 Bad Gateway
- Verifica que Cloud Run está activo
- Verifica logs de Cloud Run
- Verifica que el Load Balancer está funcionando

---

## 📊 CHECKLIST

- [ ] Identificado proveedor de DNS
- [ ] Accedido al panel de DNS
- [ ] Eliminado registros A antiguos (si existen)
- [ ] Creado registro A para `stvaldivia.cl` → `34.120.239.226`
- [ ] Creado registro A para `www.stvaldivia.cl` → `34.120.239.226`
- [ ] Guardado cambios
- [ ] Esperado 5-10 minutos
- [ ] Verificado DNS con `dig stvaldivia.cl +short`
- [ ] Verificado que muestra `34.120.239.226`
- [ ] Esperado aprovisionamiento SSL (10-60 minutos)
- [ ] Probado https://stvaldivia.cl

---

## 🎯 RESULTADO ESPERADO

Después de configurar DNS y esperar aprovisionamiento SSL:

```bash
# Debe funcionar
curl https://stvaldivia.cl/api/v1/public/evento/hoy
# Respuesta: {"evento":null,"status":"no_event"}

# En navegador
# https://stvaldivia.cl debe cargar correctamente
# https://www.stvaldivia.cl debe cargar correctamente
# Certificado SSL válido (candado verde)
```

---

**IP para DNS:** `34.120.239.226`

**¿Necesitas ayuda con un proveedor específico?** Dime cuál es y te doy instrucciones detalladas.

