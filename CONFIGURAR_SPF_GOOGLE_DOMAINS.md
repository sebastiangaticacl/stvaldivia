# 📧 CONFIGURAR REGISTRO SPF EN GOOGLE DOMAINS

**Objetivo:** Agregar registro SPF (TXT) para stvaldivia.cl  
**Dominio:** stvaldivia.cl  
**DNS:** Google Domains

---

## 🎯 CONFIGURACIÓN A AGREGAR

**Tipo de registro:** TXT  
**Nombre de host:** `@` o `stvaldivia.cl`  
**TTL:** 300  
**Datos del registro:** `v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all`

---

## 📋 PASO A PASO

### PASO 1: Acceder a Google Domains

1. Ve a: **https://domains.google.com**
2. Inicia sesión con tu cuenta de Google
3. Selecciona el dominio **stvaldivia.cl**

### PASO 2: Ir a Configuración DNS

1. En el menú lateral, haz clic en **"DNS"** o **"Registros DNS"**
2. Busca la sección **"Registros de recursos personalizados"** o **"Custom resource records"**

### PASO 3: Verificar Registros SPF Existentes

1. Busca si ya existe un registro **TXT** con datos que contengan `v=spf1`
2. Si encuentras uno, **elimínalo** primero (solo debe haber un registro SPF por dominio)
3. Si NO hay registro SPF, continúa al siguiente paso

### PASO 4: Agregar Nuevo Registro TXT (SPF)

1. Haz clic en **"Agregar registro"** o **"Add record"**
2. Completa los campos:
   - **Tipo de registro / Record type:** Selecciona `TXT` del dropdown
   - **Nombre de host / Host name:** Escribe `@` (esto representa el dominio raíz)
     - *Nota: Google Domains puede mostrar esto como `stvaldivia.cl` después de guardar, pero debes escribir `@`*
   - **Datos del registro / Data:** Copia exactamente este texto:
     ```
     v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all
     ```
     - ⚠️ **IMPORTANTE:** No incluyas las comillas dobles, solo el texto
     - El valor debe ser exactamente: `v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all`
   - **TTL:** Escribe `300` (5 minutos)

3. Haz clic en **"Guardar"** o **"Save"**

### PASO 5: Verificar la Configuración

Después de guardar, deberías ver un registro como este:

```
Tipo    Nombre de host    Datos del registro                                                      TTL
TXT     @                 v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all         300
```

O puede aparecer como:

```
Tipo    Nombre de host    Datos del registro                                                      TTL
TXT     stvaldivia.cl     v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all         300
```

Ambas formas son correctas.

---

## ✅ VERIFICACIÓN

Espera **5-10 minutos** para que se propague el cambio, luego verifica desde terminal:

```bash
dig stvaldivia.cl TXT +short
```

**Resultado esperado:**
```
"v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all"
```

O puede aparecer sin las comillas:
```
v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all
```

**Verificación alternativa:**
```bash
# Ver todos los registros TXT
nslookup -type=TXT stvaldivia.cl
```

---

## 📝 DETALLES DE LA CONFIGURACIÓN SPF

El registro SPF configurado permite enviar emails desde:

1. **IP específica:** `195.250.27.30` (IP del servidor de hostingdelsur.cl)
2. **Servicios incluidos:** `spf.mysecurecloudhost.com` (servicios de email del hosting)
3. **Política final:** `~all` (soft fail - otros servidores pueden enviar pero no es recomendado)

### Explicación de los componentes:

- `v=spf1` - Versión del protocolo SPF
- `ip4:195.250.27.30` - Permite enviar desde esta IP específica
- `include:spf.mysecurecloudhost.com` - Incluye las reglas SPF del dominio del hosting
- `~all` - Soft fail para cualquier otro servidor (no recomendado pero no bloqueado)

---

## ⚠️ IMPORTANTE

- **Solo un registro SPF:** Solo puede haber UN registro SPF por dominio. Si ya existe uno, elimínalo antes de agregar el nuevo.
- **Sin comillas:** Al agregar el registro en Google Domains, NO incluyas comillas dobles en el campo de datos. Solo escribe el texto directamente.
- **TTL 300:** 300 segundos = 5 minutos (propagación rápida)
- **Tiempo de propagación:** Los cambios pueden tardar entre 5 minutos y 48 horas en propagarse globalmente (normalmente 5-30 minutos)

---

## 🆘 TROUBLESHOOTING

### Error: "Invalid format" o formato inválido

- Verifica que el texto sea exactamente: `v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all`
- No incluyas comillas dobles en Google Domains
- Asegúrate de que haya un espacio entre cada componente

### Ya existe un registro SPF

- Solo puede haber un registro SPF por dominio
- Elimina el registro SPF antiguo antes de agregar el nuevo
- Puedes tener múltiples registros TXT, pero solo uno debe contener `v=spf1`

### El registro no aparece después de guardar

- Refresca la página
- Espera unos minutos y verifica con `dig stvaldivia.cl TXT +short`
- Verifica que estés viendo la sección correcta (Registros de recursos personalizados)

### El nombre de host aparece como "stvaldivia.cl" en lugar de "@"

- Esto es normal, Google Domains muestra el dominio completo
- Lo importante es que el registro funcione, verifica con `dig stvaldivia.cl TXT +short`

---

## 📸 EJEMPLO VISUAL

```
┌─────────────────────────────────────────────────────────────┐
│ Google Domains - stvaldivia.cl                               │
├─────────────────────────────────────────────────────────────┤
│ DNS → Registros de recursos personalizados                   │
├─────────────────────────────────────────────────────────────┤
│ Tipo de registro: TXT                                       │
│ Nombre de host: @                                           │
│ Datos del registro:                                          │
│ v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all │
│ TTL: 300                                                     │
│                                                             │
│ [Guardar]                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 RELACIÓN CON EL REGISTRO MX

Este registro SPF debe configurarse **junto con** el registro MX que configuraste anteriormente:

- **MX:** `0 hostingdelsur.cl` (indica dónde recibir emails)
- **SPF:** `v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all` (indica desde dónde se permite enviar emails)

Ambos registros trabajan juntos para asegurar la correcta entrega de emails.

---

**✅ Listo!** Una vez configurado el SPF, los emails enviados desde stvaldivia.cl serán reconocidos como legítimos por los servidores de recepción.










