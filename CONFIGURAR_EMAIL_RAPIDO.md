# 📧 Configuración Rápida de Email

## Opción 1: Gmail (Recomendado)

### Paso 1: Obtener App Password de Gmail

1. Ve a: https://myaccount.google.com/apppasswords
2. Si no tienes verificación en 2 pasos, actívala primero
3. Selecciona:
   - **App**: Correo
   - **Dispositivo**: Otro (nombre personalizado) → "BIMBA Sistema"
4. Copia la contraseña de 16 caracteres (ejemplo: `abcd efgh ijkl mnop`)

### Paso 2: Agregar al archivo .env

Edita el archivo `.env` en la raíz del proyecto y agrega:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
SMTP_FROM=tu-email@gmail.com
```

**⚠️ IMPORTANTE**: 
- Usa la App Password (16 caracteres), NO tu contraseña normal
- Quita los espacios de la App Password si los tiene

### Paso 3: Reiniciar el servidor

```bash
# Si estás en desarrollo local
# Detén el servidor (Ctrl+C) y vuelve a iniciarlo

# Si estás en producción
sudo systemctl restart stvaldivia
```

## Opción 2: Configuración Manual

Si prefieres otro proveedor, edita el `.env` con:

```bash
SMTP_SERVER=tu-servidor-smtp.com
SMTP_PORT=587
SMTP_USER=tu-usuario
SMTP_PASSWORD=tu-contraseña
SMTP_FROM=remitente@email.com
```

## Verificar que Funciona

1. Realiza una compra de prueba en `/ecommerce/landing`
2. Revisa los logs del servidor - deberías ver:
   ```
   ✅ Email enviado exitosamente a usuario@email.com
   ```
3. Verifica la bandeja de entrada del comprador

## Troubleshooting

**Error: "SMTP authentication failed"**
- Verifica que uses una App Password (Gmail), no tu contraseña normal
- Asegúrate de que la verificación en 2 pasos esté activada

**Email no se envía**
- Revisa los logs: `tail -f logs/app.log`
- Verifica que todas las variables SMTP estén en el `.env`
- Reinicia el servidor después de agregar las variables


