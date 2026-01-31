# 📧 CONFIGURAR REDIRECCIÓN DE EMAIL - hola@stvaldivia.cl

**Objetivo:** Redirigir todos los correos enviados a `hola@stvaldivia.cl` hacia `cpanel hostingvaldivia.cl`

---

## 🎯 INFORMACIÓN NECESARIA

- **Email origen:** hola@stvaldivia.cl
- **Email destino:** cpanel@hostingvaldivia.cl (o la dirección completa del cPanel)
- **Dominio:** stvaldivia.cl

---

## 📋 PASO A PASO EN CPANEL

### PASO 1: Acceder a cPanel

1. Ve a: **https://hostingvaldivia.cl:2083** (puerto estándar de cPanel)
   - O **https://hostingvaldivia.cl/cpanel** (si está configurado)
   - O el URL específico que te haya proporcionado el hosting

2. **Inicia sesión** con tus credenciales de cPanel

### PASO 2: Ir a Email Forwarders

1. En el cPanel, busca la sección **"Email"**
2. Click en **"Forwarders"** o **"Email Forwarders"** o **"Reenviadores"**

### PASO 3: Crear el Forwarder

1. Click en el botón **"Add Forwarder"** o **"Agregar Reenviador"**

2. Configura el forwarder:
   - **Address to Forward** (Dirección a reenviar):
     - En el campo izquierdo: `hola`
     - En el menú desplegable derecho: selecciona `@stvaldivia.cl`
   
   - **Forward to** (Reenviar a):
     - Ingresa la dirección completa: `cpanel@hostingvaldivia.cl`
     - **NOTA:** Si no tienes la dirección exacta del cPanel, puede ser:
       - `info@hostingvaldivia.cl`
       - `contacto@hostingvaldivia.cl`
       - O cualquier email válido del dominio hostingvaldivia.cl

3. Opcional - **Deliver to the Forwarder Address and Forward to**:
   - Si quieres que se guarde una copia en `hola@stvaldivia.cl` Y se reenvíe, marca esta opción
   - Si solo quieres reenviar (sin guardar copia), déjala sin marcar

4. Click en **"Add Forwarder"** o **"Agregar Reenviador"**

---

## 📸 CONFIGURACIÓN EJEMPLO

```
Address to Forward:     hola@stvaldivia.cl
Forward to:             cpanel@hostingvaldivia.cl
Deliver to the Forwarder Address:  ☐ (sin marcar - solo reenviar)
```

---

## ✅ VERIFICAR CONFIGURACIÓN

Después de crear el forwarder:

1. Deberías ver en la lista de forwarders:
   ```
   hola@stvaldivia.cl → cpanel@hostingvaldivia.cl
   ```

2. **Probar el forwarder:**
   - Envía un email de prueba a `hola@stvaldivia.cl` desde otra cuenta
   - Verifica que el email llegue a `cpanel@hostingvaldivia.cl`

---

## 🔧 ALTERNATIVA: Usar Auto-Responder + Forwarder

Si necesitas más control, puedes combinar:

1. **Auto-Responder** (opcional): Para enviar una respuesta automática
   - cPanel → Email → Auto-Responders
   - Crear auto-responder para `hola@stvaldivia.cl`

2. **Forwarder**: Para reenviar los emails (configuración principal)

---

## ⚠️ NOTAS IMPORTANTES

### Validar dirección de destino

Antes de configurar, **verifica la dirección de destino exacta**:
- ¿Es `cpanel@hostingvaldivia.cl`?
- ¿O es otra dirección como `info@hostingvaldivia.cl` o `admin@hostingvaldivia.cl`?

### Dominio y DNS

- Asegúrate de que los **registros MX** estén configurados correctamente para `stvaldivia.cl`
- Los registros MX deben apuntar al servidor de email del hosting (normalmente el mismo servidor del cPanel)

### Verificar registros MX

Para verificar los registros MX actuales:

```bash
dig stvaldivia.cl MX +short
```

Deberías ver algo como:
```
10 mail.hostingvaldivia.cl
```

---

## 🔍 TROUBLESHOOTING

### El email no llega al destino

1. **Verifica la dirección de destino:**
   - Asegúrate de que `cpanel@hostingvaldivia.cl` existe y es válida
   - Prueba enviando un email directo a esa dirección

2. **Verifica registros MX:**
   ```bash
   dig stvaldivia.cl MX +short
   ```

3. **Revisa logs de cPanel:**
   - cPanel → Email → Email Delivery Reports
   - Busca errores de entrega

4. **Verifica spam:**
   - Revisa la carpeta de spam del email destino
   - El forwarder puede marcar algunos emails como spam

### Error: "Forwarder already exists"

- Si el forwarder ya existe, puedes editarlo:
  - Busca en la lista de forwarders
  - Click en "Edit" o "Editar"
  - Modifica la dirección de destino

### Error: "Invalid destination address"

- Verifica que la dirección de destino sea válida
- Asegúrate de que el dominio destino (hostingvaldivia.cl) esté configurado correctamente

---

## 📝 CONFIGURACIÓN ADICIONAL (Opcional)

### Crear múltiples forwarders

Si necesitas reenviar a múltiples direcciones:

1. Crea un forwarder principal
2. O usa una lista de distribución (cPanel → Email → Mailing Lists)

### Guardar copia local

Si quieres que los emails también se guarden en `hola@stvaldivia.cl`:

- Marca la opción **"Deliver to the Forwarder Address and Forward to"**
- Esto creará una cuenta de email `hola@stvaldivia.cl` además del forwarder

---

## 🎯 RESUMEN RÁPIDO

1. ✅ Acceder a cPanel: https://hostingvaldivia.cl:2083
2. ✅ Email → Forwarders
3. ✅ Add Forwarder
4. ✅ `hola@stvaldivia.cl` → `cpanel@hostingvaldivia.cl`
5. ✅ Guardar y verificar

---

**¿Necesitas ayuda con algún paso específico?** Si tienes acceso al cPanel, puedo ayudarte con los detalles exactos según la interfaz que veas.










