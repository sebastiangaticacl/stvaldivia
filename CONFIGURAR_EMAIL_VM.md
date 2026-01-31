# 📧 Configurar Email en la VM de Producción

Esta guía explica cómo habilitar el envío de correos electrónicos en la VM de producción.

## 🚀 Opción Rápida: Script Automático

El método más fácil es usar el script interactivo:

```bash
./configurar_email_vm.sh
```

El script te guiará paso a paso para configurar el correo.

## 📋 Opciones Disponibles

### 1. Gmail (Recomendado)

**Ventajas:**
- Fácil de configurar
- Confiable y gratuito
- Buena entrega de correos

**Requisitos:**
- Cuenta de Gmail con verificación en 2 pasos habilitada
- App Password generada (no usar contraseña normal)

**Pasos:**
1. Ve a: https://myaccount.google.com/apppasswords
2. Genera una App Password para "Correo"
3. Usa la contraseña de 16 caracteres (sin espacios)

**Configuración:**
- Servidor: `smtp.gmail.com`
- Puerto: `587`
- Usuario: Tu email de Gmail
- Contraseña: App Password (16 caracteres)

### 2. Servidor SMTP del Hosting (stvaldivia.cl)

**Ventajas:**
- Usa el dominio propio (hola@stvaldivia.cl)
- Ya está configurado con SPF, DKIM y DMARC
- No requiere servicios externos

**Configuración:**
- Servidor: `s3418.mex1.stableserver.net`
- Puerto: `465` (SSL)
- Usuario: `hola@stvaldivia.cl` (o el email que tengas configurado)
- Contraseña: La contraseña del email en cPanel

**Nota:** Esta es la opción recomendada si ya tienes el email configurado en el hosting.

### 3. Outlook/Hotmail

**Configuración:**
- Servidor: `smtp-mail.outlook.com`
- Puerto: `587`
- Usuario: Tu email de Outlook
- Contraseña: Tu contraseña de Outlook

### 4. SendGrid

**Ventajas:**
- Servicio profesional de email transaccional
- Buena entrega y analytics
- Plan gratuito disponible (100 emails/día)

**Configuración:**
- Servidor: `smtp.sendgrid.net`
- Puerto: `587`
- Usuario: `apikey`
- Contraseña: Tu API Key de SendGrid
- Remitente: `noreply@stvaldivia.cl` (o el que configures)

### 5. Mailgun

**Ventajas:**
- Servicio profesional de email
- Plan gratuito disponible (5,000 emails/mes)

**Configuración:**
- Servidor: `smtp.mailgun.org`
- Puerto: `587`
- Usuario: `postmaster@tudominio.mailgun.org`
- Contraseña: Tu contraseña SMTP de Mailgun
- Remitente: `noreply@stvaldivia.cl`

### 6. Otro Proveedor SMTP

Si tienes otro proveedor, necesitarás:
- Servidor SMTP
- Puerto (587 para TLS, 465 para SSL)
- Usuario y contraseña
- Email remitente

## 🔧 Configuración Manual

Si prefieres configurar manualmente en la VM:

### Opción A: En el Servicio Systemd (Recomendado)

1. Conectarse a la VM:
```bash
ssh stvaldiviazal@34.176.144.166
```

2. Editar el servicio:
```bash
sudo nano /etc/systemd/system/stvaldivia.service
```

3. Agregar las variables de entorno en la sección `[Service]`, antes de `ExecStart`:
```ini
[Service]
# ... otras configuraciones ...
Environment="SMTP_SERVER=smtp.gmail.com"
Environment="SMTP_PORT=587"
Environment="SMTP_USER=tu-email@gmail.com"
Environment="SMTP_PASSWORD=tu-app-password"
Environment="SMTP_FROM=tu-email@gmail.com"
ExecStart=/var/www/stvaldivia/venv/bin/gunicorn ...
```

4. Recargar y reiniciar:
```bash
sudo systemctl daemon-reload
sudo systemctl restart stvaldivia.service
```

### Opción B: En Archivo .env

1. Conectarse a la VM:
```bash
ssh stvaldiviazal@34.176.144.166
```

2. Editar el archivo .env:
```bash
sudo nano /var/www/stvaldivia/.env
```

3. Agregar las variables:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
```

4. Reiniciar el servicio:
```bash
sudo systemctl restart stvaldivia.service
```

## ✅ Verificación

Después de configurar, verifica que funciona:

1. **Revisar logs del servicio:**
```bash
ssh stvaldiviazal@34.176.144.166
sudo journalctl -u stvaldivia.service -f
```

2. **Realizar una compra de prueba:**
   - Ve a la página de ecommerce
   - Completa una compra de prueba
   - Verifica los logs para ver si el email se envió

3. **Verificar envío:**
   - Deberías ver en los logs: `✅ Email enviado exitosamente a hola@valdiviaesbimba.cl`
   - El email se envía a `hola@valdiviaesbimba.cl` (configurado en el código)

## 🔍 Troubleshooting

### Error: "SMTP authentication failed"
- Verifica que las credenciales sean correctas
- Para Gmail, asegúrate de usar una App Password, no tu contraseña normal
- Verifica que la verificación en 2 pasos esté habilitada (Gmail)

### Error: "Connection refused"
- Verifica que el servidor SMTP y puerto sean correctos
- Asegúrate de que el firewall de la VM permita conexiones salientes en el puerto SMTP
- Prueba conectarte manualmente: `telnet smtp.gmail.com 587`

### El servicio no inicia después de agregar variables
- Revisa los logs: `sudo journalctl -u stvaldivia.service -n 50`
- Verifica que las variables estén correctamente formateadas (sin espacios extra)
- Asegúrate de que las comillas estén correctas en el archivo systemd

### Email no se envía pero no hay error
- Revisa los logs del servidor
- Verifica que todas las variables SMTP estén configuradas
- El sistema no falla si el email no se puede enviar, solo loguea el error

## 📝 Notas Importantes

- ⚠️ **Seguridad**: Las contraseñas se almacenan en texto plano en el servicio systemd o .env. Asegúrate de que estos archivos tengan permisos restrictivos.
- ✅ **Fallback**: Si el email falla, la compra se completa igual (el ticket se crea)
- 📧 **Destino**: Los emails se envían a `hola@valdiviaesbimba.cl` (configurado en el código)
- 🔄 **Reinicio**: Después de cambiar las variables, siempre reinicia el servicio: `sudo systemctl restart stvaldivia.service`

## 🎯 Recomendación

Para producción, se recomienda usar:
1. **Servidor SMTP del hosting** (s3418.mex1.stableserver.net) - Si ya tienes el email configurado
2. **Gmail con App Password** - Si necesitas una solución rápida y confiable
3. **SendGrid o Mailgun** - Si necesitas un servicio profesional con analytics

