# Configuración de Correo Electrónico - stvaldivia.cl

## Arquitectura

### Componentes

- **Dominio:** stvaldivia.cl
- **DNS Autoritativo:** Google Cloud DNS
- **Hosting de Correo:** cPanel Reseller (externo al DNS)
- **Servidor SMTP:** s3418.mex1.stableserver.net
- **Puerto SMTP:** 465 (SSL/TLS)
- **Usuario SMTP:** hola@stvaldivia.cl

### Separación DNS y Correo

El DNS está gestionado en Google Cloud DNS y el correo está alojado en un servidor cPanel externo. Esta separación significa que:

- Los registros DNS (SPF, DKIM, DMARC) se configuran en Google Cloud DNS
- El servidor de correo (cPanel) no tiene control sobre estos registros DNS
- cPanel puede mostrar advertencias sobre la configuración DNS que son falsas porque no tiene visibilidad de los registros DNS reales
- La validación real debe hacerse mediante consultas DNS directas a los nameservers autoritativos

### Nameservers Autoritativos

- ns-cloud-b1.googledomains.com
- ns-cloud-b2.googledomains.com
- ns-cloud-b3.googledomains.com
- ns-cloud-b4.googledomains.com

## Registros DNS

### SPF Record

**Tipo:** TXT  
**Nombre:** @ (stvaldivia.cl)  
**Valor:**
```
v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all
```

**Explicación:**
- `v=spf1` - Versión del protocolo SPF
- `ip4:195.250.27.30` - Permite envío desde la IP 195.250.27.30
- `include:spf.mysecurecloudhost.com` - Incluye las políticas SPF del hosting
- `~all` - Soft fail para otros servidores no listados

### DKIM Record

**Tipo:** TXT  
**Nombre:** default._domainkey.stvaldivia.cl  
**Valor:** Clave DKIM publicada en múltiples fragmentos (chunks)

**Limitación de Longitud de TXT Records:**

Los registros TXT en DNS tienen un límite de 255 caracteres por fragmento. Las claves DKIM suelen exceder este límite y deben dividirse en múltiples fragmentos TXT. Cada fragmento debe tener 255 caracteres o menos, y los fragmentos se concatenan automáticamente por los resolvers DNS.

**Formato de Chunking:**

Cuando una clave DKIM es demasiado larga, se publica como múltiples registros TXT con el mismo nombre. El formato típico es:

```
default._domainkey.stvaldivia.cl IN TXT "v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..." (chunk 1, ≤255 chars)
default._domainkey.stvaldivia.cl IN TXT "...continuación de la clave..." (chunk 2, ≤255 chars)
```

Los resolvers DNS concatenan automáticamente estos fragmentos al resolver el registro.

**Verificación de Chunking:**

Para verificar que todos los fragmentos están presentes:

```bash
dig @ns-cloud-b1.googledomains.com default._domainkey.stvaldivia.cl TXT +short
```

El resultado mostrará todos los fragmentos, que deben concatenarse para formar la clave completa.

### DMARC Record

**Tipo:** TXT  
**Nombre:** _dmarc.stvaldivia.cl  
**Valor:**
```
v=DMARC1; p=none; rua=mailto:admin@stvaldivia.cl; ruf=mailto:admin@stvaldivia.cl; fo=1
```

**Parámetros:**
- `v=DMARC1` - Versión del protocolo DMARC
- `p=none` - Política: no tomar acción (modo de monitoreo)
- `rua=mailto:admin@stvaldivia.cl` - Dirección para agregados de reportes
- `ruf=mailto:admin@stvaldivia.cl` - Dirección para reportes de fallas forenses
- `fo=1` - Opciones de fallas: generar reportes para SPF y/o DKIM fallidos

## Advertencias Falsas en cPanel

### Comportamiento Esperado

cPanel Email Deliverability puede mostrar advertencias sobre SPF, DKIM o DMARC, indicando que los registros no están configurados o son incorrectos.

**Estas advertencias son falsas y se deben ignorar.**

### Razón Técnica

- cPanel no controla el DNS de stvaldivia.cl
- cPanel consulta DNS públicos que pueden no estar sincronizados con los nameservers autoritativos
- cPanel no tiene visibilidad de los registros DNS reales configurados en Google Cloud DNS
- Los registros están correctamente configurados en los nameservers autoritativos

### Validación Correcta

La validación real debe hacerse mediante:

1. Consultas DNS directas a los nameservers autoritativos
2. Análisis de headers de correo recibido (Gmail "Show original")

Las advertencias de cPanel no reflejan el estado real de la configuración.

## Checklist de Verificación

### Verificación DNS

#### SPF

```bash
dig @ns-cloud-b1.googledomains.com stvaldivia.cl TXT +short | grep spf
```

Resultado esperado:
```
"v=spf1 ip4:195.250.27.30 include:spf.mysecurecloudhost.com ~all"
```

#### DKIM

```bash
dig @ns-cloud-b1.googledomains.com default._domainkey.stvaldivia.cl TXT +short
```

Resultado esperado:
- Múltiples fragmentos TXT que contienen la clave DKIM completa
- Todos los fragmentos deben estar presentes

#### DMARC

```bash
dig @ns-cloud-b1.googledomains.com _dmarc.stvaldivia.cl TXT +short
```

Resultado esperado:
```
"v=DMARC1; p=none; rua=mailto:admin@stvaldivia.cl; ruf=mailto:admin@stvaldivia.cl; fo=1"
```

### Verificación mediante Correo Recibido (Gmail)

1. Enviar un correo de prueba desde hola@stvaldivia.cl a una cuenta de Gmail
2. En Gmail, abrir el mensaje recibido
3. Click en los tres puntos (menú) → "Show original"
4. Verificar en la sección "SPF", "DKIM", "DMARC":

**Resultado esperado:**
- SPF: PASS
- DKIM: PASS
- DMARC: PASS (p=none)

Si los tres muestran PASS, la configuración es correcta.

## Configuración de Gmail para Envío

### Configurar "Send mail as"

Para enviar correo desde Gmail usando la cuenta hola@stvaldivia.cl:

1. Gmail → Settings (Configuración) → Accounts and Import (Cuentas e importación)
2. Section "Send mail as" → "Add another email address"
3. Configurar:
   - Name: Nombre a mostrar
   - Email address: hola@stvaldivia.cl
   - Treat as alias: NO (desmarcar)
   - Uncheck "Make default"
4. Click "Next Step"
5. Configuración SMTP:
   - SMTP Server: s3418.mex1.stableserver.net
   - Port: 465
   - Username: hola@stvaldivia.cl
   - Password: [contraseña de la cuenta]
   - Secure connection: SSL
6. Click "Add Account"
7. Verificar el código de confirmación enviado a hola@stvaldivia.cl

### Verificación de Envío

Después de configurar, al redactar un correo en Gmail:

1. Click en "From" (De)
2. Seleccionar hola@stvaldivia.cl
3. El correo se enviará usando el servidor SMTP configurado

## Recomendaciones de Seguridad

### Evolución de DMARC

La política DMARC actual está configurada como `p=none`, que es una política de monitoreo que no toma acción sobre correos que fallan la autenticación.

**Proceso Recomendado:**

#### Fase 1: Monitoreo (Actual)
- Política: `p=none`
- Duración: Mínimo 2-4 semanas
- Objetivo: Recopilar datos de reportes DMARC para identificar fuentes legítimas de envío

#### Fase 2: Cuarentena
- Política: `p=quarantine`
- Cambio gradual:
  1. Configurar porcentaje inicial: `pct=25` (25% de correos fallidos van a spam)
  2. Monitorear durante 1-2 semanas
  3. Aumentar gradualmente: `pct=50`, luego `pct=100`
  4. Si no hay problemas, cambiar a `p=quarantine` sin pct

Registro DNS:
```
v=DMARC1; p=quarantine; pct=25; rua=mailto:admin@stvaldivia.cl; ruf=mailto:admin@stvaldivia.cl; fo=1
```

#### Fase 3: Rechazo
- Política: `p=reject`
- Solo aplicar después de:
  - Al menos 2-4 semanas en `p=quarantine` sin problemas
  - Verificación de que todos los remitentes legítimos están autenticados
  - Análisis de reportes DMARC confirma que no hay remitentes legítimos bloqueados

Registro DNS:
```
v=DMARC1; p=reject; rua=mailto:admin@stvaldivia.cl; ruf=mailto:admin@stvaldivia.cl; fo=1
```

### Análisis de Reportes DMARC

Durante la fase de monitoreo (`p=none`):

1. Revisar reportes agregados (rua) diariamente
2. Identificar fuentes legítimas de envío
3. Verificar que todas las fuentes legítimas tienen SPF/DKIM configurados
4. Documentar cualquier fuente no autenticada y determinar si es legítima

### Consideraciones

- No cambiar de `p=none` a `p=reject` directamente sin pasar por `p=quarantine`
- Los cambios en políticas DMARC pueden afectar la entrega de correos legítimos
- Mantener `rua` y `ruf` configurados para recibir reportes durante todas las fases
- Verificar regularmente los reportes para detectar problemas de autenticación

