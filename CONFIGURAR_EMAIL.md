# 📧 Configuración de Envío de Emails

Este documento explica cómo configurar el envío automático de emails con tickets de entrada.

## Variables de Entorno Requeridas

Agrega estas variables a tu archivo `.env` (desarrollo) o variables de entorno del sistema (producción):

```bash
# Configuración SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
```

## Configuración por Proveedor

### Gmail

1. **Habilita la verificación en 2 pasos** en tu cuenta de Google
2. **Genera una App Password**:
   - Ve a: https://myaccount.google.com/apppasswords
   - Selecciona "Correo" y "Otro (nombre personalizado)"
   - Ingresa "BIMBA Sistema"
   - Copia la contraseña generada (16 caracteres)

3. **Configuración**:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx  # La App Password de 16 caracteres (sin espacios)
SMTP_FROM=tu-email@gmail.com
```

### Outlook/Hotmail

```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=tu-email@outlook.com
SMTP_PASSWORD=tu-contraseña
SMTP_FROM=tu-email@outlook.com
```

### Otros Proveedores SMTP

**SendGrid:**
```bash
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=tu-sendgrid-api-key
SMTP_FROM=noreply@tudominio.com
```

**Mailgun:**
```bash
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@tudominio.mailgun.org
SMTP_PASSWORD=tu-mailgun-password
SMTP_FROM=noreply@tudominio.com
```

## Configuración en Desarrollo Local

1. Crea o edita el archivo `.env` en la raíz del proyecto:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
```

2. Reinicia el servidor Flask para que cargue las nuevas variables.

## Configuración en Producción (Google VM)

1. **SSH al servidor**:
```bash
ssh stvaldiviazal@34.176.144.166
```

2. **Edita el archivo de variables de entorno** (depende de cómo esté configurado):
```bash
# Si usas systemd, edita el archivo de servicio
sudo nano /etc/systemd/system/stvaldivia.service

# O si usas un archivo .env en producción
sudo nano /var/www/stvaldivia/.env
```

3. **Agrega las variables SMTP**:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com
```

4. **Reinicia el servicio**:
```bash
sudo systemctl restart stvaldivia
# O si usas Gunicorn directamente
sudo systemctl restart gunicorn
```

## Verificación

Después de configurar, realiza una compra de prueba y verifica:

1. **Logs del servidor** - Deberías ver:
   ```
   ✅ Email enviado exitosamente a usuario@email.com
   ```

2. **Bandeja de entrada** - El usuario debería recibir el email con:
   - Asunto: "Tu entrada para [nombre del evento]"
   - Código del ticket
   - Link para ver el ticket completo

## Troubleshooting

### Error: "SMTP authentication failed"
- Verifica que `SMTP_USER` y `SMTP_PASSWORD` sean correctos
- Para Gmail, asegúrate de usar una App Password, no tu contraseña normal
- Verifica que la verificación en 2 pasos esté habilitada

### Error: "Connection refused"
- Verifica que `SMTP_SERVER` y `SMTP_PORT` sean correctos
- Asegúrate de que el firewall permita conexiones salientes en el puerto SMTP

### Email no se envía pero no hay error
- Revisa los logs del servidor para ver mensajes de advertencia
- Verifica que todas las variables estén configuradas correctamente
- El sistema no falla si el email no se puede enviar, solo loguea el error

### Email va a spam
- Configura SPF, DKIM y DMARC en tu dominio
- Usa un email profesional (no Gmail personal si es posible)
- Considera usar un servicio profesional como SendGrid o Mailgun

## Notas Importantes

- ⚠️ **Seguridad**: Nunca commitees el archivo `.env` con contraseñas al repositorio
- ✅ **Fallback**: Si el email falla, la compra se completa igual (el ticket se crea)
- 📝 **Logs**: Todos los intentos de envío se registran en los logs del servidor
- 🔄 **Reintentos**: Actualmente no hay reintentos automáticos, pero puedes implementarlos si es necesario


