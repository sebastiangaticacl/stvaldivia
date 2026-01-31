# 📧 CONFIGURAR REDIRECCIÓN DE EMAIL EN GOOGLE - hola@stvaldivia.cl

**Dominio:** stvaldivia.cl  
**Proveedor DNS:** Google Domains (solo para la web)  
**Proveedor Email:** hostingdelsur.cl (cPanel)  
**Objetivo:** Redirigir `hola@stvaldivia.cl` → dirección de email en hostingdelsur.cl

---

## 🎯 OPCIONES PARA CONFIGURAR EN GOOGLE

Dependiendo de tu configuración actual, hay dos escenarios principales:

### Escenario 1: Google Workspace (Gmail Empresarial)
Si tienes Google Workspace configurado para stvaldivia.cl

### Escenario 2: Google Domains + Servidor de Email Externo
Si solo usas Google Domains para DNS pero el email está en otro servidor

---

## 📋 OPCIÓN 1: GOOGLE WORKSPACE (Si tienes cuenta de Google Workspace)

### PASO 1: Acceder a Google Admin Console

1. Ve a: **https://admin.google.com**
2. Inicia sesión con tu cuenta de administrador de Google Workspace
3. Selecciona el dominio `stvaldivia.cl`

### PASO 2: Configurar Email Routing (Ruteo de Email)

1. En el panel de administración, ve a **Apps** → **Google Workspace** → **Gmail**
2. Click en **Routing** (Ruteo)
3. Click en **"Configure"** o **"Configurar"** en la sección "Routing"

### PASO 3: Crear Regla de Ruteo

1. Click en **"Add Another Rule"** o **"Agregar otra regla"**
2. Configura la regla:
   - **Description:** `Forward hola@stvaldivia.cl`
   - **Affected Users:** 
     - Selecciona **"Specific Users"**
     - Ingresa: `hola@stvaldivia.cl`
   - **Messages to Affect:**
     - Selecciona **"All messages"** o **"Todas las mensajes"**
   - **Also deliver to:** 
     - Selecciona **"Add more recipients"**
     - Ingresa la dirección destino: `[email]@hostingvaldivia.cl`
     - Marca **"Keep a copy in the recipient's inbox"** si quieres guardar copia
   - **Advanced:** 
     - **Change route:** Selecciona **"Modify message"** → **"Change recipient"**
     - Ingresa el email destino final

3. Click en **"Save"** o **"Guardar"**

---

## 📋 OPCIÓN 2: GOOGLE DOMAINS + REDIRECCIÓN DE EMAIL

Si solo usas Google Domains para DNS y el email está en otro servidor (cPanel), necesitas configurar los registros MX:

### PASO 1: Acceder a Google Domains

1. Ve a: **https://domains.google.com**
2. Inicia sesión con tu cuenta de Google
3. Selecciona el dominio `stvaldivia.cl`
4. Ve a la sección **"DNS"** o **"Registros de recursos"**

### PASO 2: Verificar/Configurar Registros MX

Los registros MX deben apuntar al servidor de email donde quieres recibir los correos:

1. Busca los registros **MX** existentes
2. Si no existen o apuntan a Google, necesitas cambiarlos al servidor de hostingvaldivia.cl

**Registros MX para hostingdelsur.cl:**
```
Tipo: MX
Nombre: @
Valor: hostingdelsur.cl
Prioridad: 0
TTL: 3600
```

### PASO 3: Configurar Forwarder en cPanel (Hosting del Sur)

Una vez que los MX apuntan correctamente, configura el forwarder en cPanel:

1. Accede a cPanel de hostingdelsur.cl: `https://hostingdelsur.cl:2083` (o `https://195.250.27.30:2083`)
2. Ve a **Email** → **Forwarders**
3. Crear forwarder:
   - **From:** `hola@stvaldivia.cl`
   - **To:** `[dirección destino]@hostingdelsur.cl` (ejemplo: info@hostingdelsur.cl)

---

## 📋 OPCIÓN 3: USAR GOOGLE CLOUD DNS + SERVICIO DE EMAIL

Si el dominio está completamente en Google Cloud:

### PASO 1: Verificar Configuración Actual

```bash
# Ver registros MX actuales
dig stvaldivia.cl MX +short

# Ver registros DNS
dig stvaldivia.cl ANY +short
```

### PASO 2: Configurar en Google Cloud DNS

1. Ve a: **https://console.cloud.google.com/net-services/dns/zones**
2. Selecciona la zona DNS para `stvaldivia.cl`
3. **Si quieres usar Google Workspace:**
   - Agrega registros MX de Google Workspace
   - Luego configura la redirección como en Opción 1

4. **Si quieres usar servidor externo (cPanel):**
   - Agrega registros MX apuntando al servidor de email externo
   - Configura el forwarder en el servidor externo

---

## 🔍 VERIFICAR CONFIGURACIÓN ACTUAL

Primero, verifica qué tienes configurado actualmente:

```bash
# Ver registros MX
dig stvaldivia.cl MX +short

# Ver todos los registros DNS
dig stvaldivia.cl ANY +short
```

**Interpretación:**
- Si ves `*.google.com` o `*.googlemail.com` → Estás usando Google Workspace/Gmail
- Si ves `hostingdelsur.cl` o similar → Estás usando servidor externo (cPanel)
- Si no ves registros MX → No hay email configurado (es tu caso actual)

---

## ✅ PASOS RECOMENDADOS (Basado en tu caso)

Como quieres redirigir a hostingdelsur.cl, sigue estos pasos:

### 1. Configurar registros MX en Google Domains

1. Accede a **https://domains.google.com**
2. Selecciona `stvaldivia.cl`
3. Ve a **DNS** → **Registros de recursos personalizados**
4. Busca si hay registros **MX** existentes
5. Si hay registros MX (probablemente de Google), **elimínalos**
6. Agrega **nuevo registro MX**:
   - **Tipo de registro:** `MX`
   - **Nombre de host:** `@` (representa el dominio raíz)
   - **Datos del registro:** `0 hostingdelsur.cl` (prioridad 0, servidor hostingdelsur.cl)
   - **TTL:** `3600` (1 hora) o deja el default

**Ejemplo visual:**
```
Tipo    Nombre de host    Datos del registro      TTL
MX      @                 0 hostingdelsur.cl      3600
```

### 2. Verificar que stvaldivia.cl esté en cPanel

**IMPORTANTE:** Antes de configurar el forwarder, el dominio `stvaldivia.cl` debe estar agregado en cPanel de hostingdelsur.cl:

1. Accede a cPanel: `https://hostingdelsur.cl:2083` (o `https://195.250.27.30:2083`)
2. Ve a **"Addon Domains"** o **"Dominios adicionales"**
3. Verifica que `stvaldivia.cl` esté listado
4. Si NO está, agrégalo como dominio adicional

### 3. Configurar forwarder en cPanel

Una vez que:
- ✅ Los registros MX están configurados en Google Domains
- ✅ El dominio `stvaldivia.cl` está en cPanel

Configura el forwarder:

1. En cPanel de hostingdelsur.cl, ve a **Email** → **Forwarders**
2. Click en **"Add Forwarder"** o **"Agregar Forwarder"**
3. Configura:
   - **Address to Forward:** `hola` (esto creará hola@stvaldivia.cl)
   - **Domain:** Selecciona `stvaldivia.cl` del dropdown
   - **Destination:** Ingresa la dirección de email destino:
     - Ejemplo: `info@hostingdelsur.cl`
     - O la dirección que necesites
4. Click en **"Add Forwarder"** o **"Agregar"**

---

## ⚠️ IMPORTANTE

### ¿Cuál es la dirección de destino exacta?

Necesitas confirmar la dirección de email exacta en hostingdelsur.cl:
- ¿Es `info@hostingdelsur.cl`?
- ¿Es `contacto@hostingdelsur.cl`?
- ¿Es `administrador@hostingdelsur.cl`?
- ¿O es otra dirección específica?

**Pregunta al administrador de hostingdelsur.cl cuál es la dirección de email correcta para recibir los correos.**

### Tiempo de propagación

- Los cambios en registros MX pueden tardar **4-48 horas** en propagarse
- Los forwarders en cPanel son **inmediatos** una vez que los MX están correctos

### Verificación

Después de configurar, prueba enviando un email:
```bash
# Desde otra cuenta, envía un email a hola@stvaldivia.cl
# Verifica que llegue a la dirección destino
```

---

## 🆘 TROUBLESHOOTING

### Los emails no llegan

1. **Verifica registros MX:**
   ```bash
   dig stvaldivia.cl MX +short
   ```
   Deben apuntar al servidor correcto

2. **Verifica que el dominio esté configurado en cPanel:**
   - cPanel debe tener `stvaldivia.cl` como dominio adicional o principal

3. **Verifica logs en cPanel:**
   - Email → Email Delivery Reports
   - Busca errores de entrega

### Error: "Domain not found" en cPanel

- El dominio `stvaldivia.cl` debe estar agregado en cPanel
- Si no está, agrégalo como dominio adicional o principal

---

## 📞 PRÓXIMOS PASOS

1. ✅ Verificar que stvaldivia.cl esté agregado en cPanel de hostingdelsur.cl
2. ✅ Configurar registros MX en Google Domains (0 hostingdelsur.cl)
3. ✅ Esperar la propagación (5-30 minutos, máximo 48 horas)
4. ✅ Confirmar la dirección de email destino en hostingdelsur.cl
5. ✅ Configurar el forwarder en cPanel (hola@stvaldivia.cl → [destino]@hostingdelsur.cl)
6. ✅ Probar enviando un email a hola@stvaldivia.cl

**¿Necesitas ayuda con algún paso específico?** Puedo ayudarte a verificar la configuración actual o guiarte paso a paso.

