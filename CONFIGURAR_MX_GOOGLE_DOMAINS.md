# 📧 CONFIGURAR REGISTRO MX EN GOOGLE DOMAINS

**Objetivo:** Configurar `hola@stvaldivia.cl` para que funcione con hostingdelsur.cl  
**Dominio:** stvaldivia.cl  
**DNS:** Google Domains  
**Email:** hostingdelsur.cl

---

## 🎯 PASO A PASO

### PASO 1: Acceder a Google Domains

1. Ve a: **https://domains.google.com**
2. Inicia sesión con tu cuenta de Google
3. Busca y selecciona el dominio **stvaldivia.cl**

### PASO 2: Ir a Configuración DNS

1. En el menú lateral, haz clic en **"DNS"** o **"Registros DNS"**
2. Busca la sección **"Registros de recursos personalizados"** o **"Custom resource records"**

### PASO 3: Verificar/Eliminar Registros MX Existentes

1. Busca si hay registros **MX** existentes para stvaldivia.cl
2. Si encuentras registros MX (por ejemplo, de Google Workspace), **elimínalos** haciendo clic en el icono de papelera o botón "Eliminar"
3. Si NO hay registros MX, continúa al siguiente paso

### PASO 4: Agregar Nuevo Registro MX

1. Haz clic en **"Agregar registro"** o **"Add record"**
2. Completa los campos:
   - **Tipo de registro / Record type:** Selecciona `MX` del dropdown
   - **Nombre de host / Host name:** Escribe `@` (esto representa el dominio raíz)
   - **Datos del registro / Data:** Escribe `0 hostingdelsur.cl`
     - El `0` es la prioridad (más bajo = mayor prioridad)
     - `hostingdelsur.cl` es el servidor de email
   - **TTL:** Deja el valor por defecto (generalmente 3600 segundos = 1 hora)

3. Haz clic en **"Guardar"** o **"Save"**

### PASO 5: Verificar la Configuración

Después de guardar, deberías ver un registro como este:

```
Tipo    Nombre de host    Datos del registro        TTL
MX      @                 0 hostingdelsur.cl        3600
```

---

## ✅ VERIFICACIÓN

Espera **5-10 minutos** para que se propague el cambio, luego verifica desde terminal:

```bash
dig stvaldivia.cl MX +short
```

**Resultado esperado:**
```
0 hostingdelsur.cl.
```

Si ves este resultado, el registro MX está configurado correctamente.

---

## 📋 PRÓXIMOS PASOS (Después de configurar MX)

Una vez que el registro MX esté activo, necesitas configurar el forwarder en cPanel:

1. **Acceder a cPanel:** https://hostingdelsur.cl:2083
2. **Verificar dominio:** Asegúrate de que `stvaldivia.cl` esté agregado como dominio adicional
3. **Configurar forwarder:**
   - Ve a **Email** → **Forwarders**
   - Crea un forwarder: `hola@stvaldivia.cl` → `[email destino]@hostingdelsur.cl`

---

## ⚠️ IMPORTANTE

- **Tiempo de propagación:** Los cambios en registros MX pueden tardar entre 5 minutos y 48 horas en propagarse globalmente (normalmente 5-30 minutos)
- **Dominio en cPanel:** El dominio `stvaldivia.cl` debe estar agregado en cPanel de hostingdelsur.cl antes de poder crear el forwarder
- **Dirección destino:** Necesitas saber a qué dirección de email en hostingdelsur.cl quieres que lleguen los correos de `hola@stvaldivia.cl`

---

## 🆘 TROUBLESHOOTING

### No puedo ver la opción "Agregar registro"

- Asegúrate de estar en la sección correcta: **"Registros de recursos personalizados"** o **"Custom resource records"**
- No uses la sección "Registros de recursos sintéticos" (synthetic records)

### El registro no aparece después de guardar

- Refresca la página
- Espera unos minutos y verifica con `dig stvaldivia.cl MX +short`

### Error al guardar

- Verifica que el formato sea exactamente: `0 hostingdelsur.cl` (con un espacio entre el número y el dominio)
- Asegúrate de que el nombre de host sea `@` (sin espacios)

---

## 📸 EJEMPLO VISUAL

```
┌─────────────────────────────────────────────────────────┐
│ Google Domains - stvaldivia.cl                          │
├─────────────────────────────────────────────────────────┤
│ DNS → Registros de recursos personalizados              │
├─────────────────────────────────────────────────────────┤
│ Tipo: MX                                                │
│ Nombre de host: @                                       │
│ Datos del registro: 0 hostingdelsur.cl                  │
│ TTL: 3600                                               │
│                                                         │
│ [Guardar]                                               │
└─────────────────────────────────────────────────────────┘
```

---

**¿Listo?** Una vez configurado el MX, procede a configurar el forwarder en cPanel.










