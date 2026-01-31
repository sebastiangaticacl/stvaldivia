# 📈 Configurar API Operacional para el Chatbot

## ¿Qué es la API Operacional?

La API Operacional es un endpoint interno que proporciona contexto adicional al chatbot BIMBA sobre el estado operativo del día:

- 📊 **Resumen de ventas** - Total de ventas y ingresos del día
- 🎯 **Estado del ambiente** - Si la noche está movida, tranquila, etc.
- 🏆 **Ranking de productos** - Productos más vendidos
- 🍺 **Información de entregas** - Entregas por bartender
- 🛡️ **Detección de fugas** - Intentos de fraude detectados

Este contexto permite que el chatbot responda preguntas como:
- "¿Cómo va la noche?" → Puede responder con feeling real basado en ventas
- "¿Qué está vendiendo más?" → Puede mencionar productos top
- "¿Está movido?" → Puede dar una respuesta contextualizada

## ⚠️ Importante

**La API Operacional es OPCIONAL**. El chatbot funciona perfectamente sin ella, pero con menos contexto operativo.

Si no está configurada:
- ✅ El chatbot sigue funcionando
- ✅ Puede responder sobre eventos, horarios, precios
- ❌ No puede dar contexto sobre el estado de la noche
- ❌ No puede mencionar ventas o ambiente

## 🚀 Configuración Rápida

### Opción 1: Script Automático (Recomendado)

```bash
./configurar_api_operacional_vm.sh
```

El script:
1. Genera una API Key automáticamente
2. Configura la URL base (por defecto: `http://127.0.0.1:5001`)
3. Agrega las variables al servicio systemd
4. Reinicia el servicio

### Opción 2: Configuración Manual

#### Paso 1: Generar API Key

```bash
# Generar una API key segura
openssl rand -hex 32
```

Copia la API key generada.

#### Paso 2: Conectarse a la VM

```bash
ssh stvaldiviazal@34.176.144.166
```

#### Paso 3: Editar el servicio systemd

```bash
sudo nano /etc/systemd/system/stvaldivia.service
```

#### Paso 4: Agregar variables en la sección [Service]

Agrega estas líneas **antes** de `ExecStart=`:

```ini
[Service]
# ... otras configuraciones ...
Environment="BIMBA_INTERNAL_API_KEY=tu-api-key-generada-aqui"
Environment="BIMBA_INTERNAL_API_BASE_URL=http://127.0.0.1:5001"
ExecStart=/var/www/stvaldivia/venv/bin/gunicorn ...
```

#### Paso 5: Recargar y reiniciar

```bash
sudo systemctl daemon-reload
sudo systemctl restart stvaldivia.service
```

## ✅ Verificación

### 1. Verificar en el Panel de Configuración

Ve a: `/admin/bot/config`

Deberías ver:
- **API Operacional**: ✅ Habilitada

### 2. Probar el Endpoint (desde la VM)

```bash
# Desde dentro de la VM
curl -H "X-API-KEY: tu-api-key" http://127.0.0.1:5001/api/v1/operational/summary
```

Deberías recibir un JSON con datos operativos.

### 3. Probar el Chatbot

Pregunta al chatbot:
- "¿Cómo va la noche?"
- "¿Está movido?"

Si está configurado correctamente, debería responder con contexto operativo.

## 🔧 Variables de Entorno

### Requeridas

- `BIMBA_INTERNAL_API_KEY` - Clave de API para autenticación (generar con `openssl rand -hex 32`)
- `BIMBA_INTERNAL_API_BASE_URL` - URL base del servidor (normalmente `http://127.0.0.1:5001`)

### Dónde Configurarlas

**Opción A: Servicio Systemd (Recomendado)**
- Archivo: `/etc/systemd/system/stvaldivia.service`
- Sección: `[Service]`
- Formato: `Environment="BIMBA_INTERNAL_API_KEY=valor"`

**Opción B: Archivo .env**
- Archivo: `/var/www/stvaldivia/.env`
- Formato: `BIMBA_INTERNAL_API_KEY=valor`

## 📋 Endpoints Disponibles

La API Operacional expone estos endpoints:

### `/api/v1/operational/summary`
Resumen completo del día (ventas, productos, entregas, fugas)

### `/api/v1/operational/sales/summary`
Solo resumen de ventas

### `/api/v1/operational/products/ranking`
Ranking de productos más vendidos

### `/api/v1/operational/deliveries/summary`
Resumen de entregas por bartender

### `/api/v1/operational/leaks/today`
Detección de fugas/antifraude del día

**Todos requieren el header:** `X-API-KEY: tu-api-key`

## 🔒 Seguridad

- ✅ La API Operacional es **solo interna** (no expuesta públicamente)
- ✅ Requiere autenticación con API Key
- ✅ Solo accesible desde `127.0.0.1` (localhost)
- ✅ No expone datos sensibles al público

## 🐛 Troubleshooting

### Error: "API Operacional no configurada"

**Causa:** Las variables de entorno no están configuradas.

**Solución:**
1. Verifica que las variables estén en el servicio systemd
2. Reinicia el servicio: `sudo systemctl restart stvaldivia.service`
3. Verifica los logs: `sudo journalctl -u stvaldivia.service -n 50`

### Error: "API key inválida"

**Causa:** La API key no coincide.

**Solución:**
1. Verifica que `BIMBA_INTERNAL_API_KEY` sea la misma en:
   - El servicio systemd
   - La llamada al endpoint
2. Regenera la API key si es necesario

### El chatbot no usa datos operativos

**Causa:** El servicio puede estar fallando silenciosamente.

**Solución:**
1. Revisa los logs del servicio
2. Prueba el endpoint manualmente con `curl`
3. Verifica que la URL base sea correcta

## 📝 Notas

- La API Operacional tiene un **timeout de 2 segundos**
- Si falla, el chatbot continúa sin datos operativos (no es crítico)
- Los datos operativos solo se usan para enriquecer respuestas, no son obligatorios
- El chatbot funciona perfectamente sin la API operacional

## 💡 Recomendación

**Configurar la API Operacional es recomendado pero no crítico.**

Si quieres que el chatbot tenga más contexto sobre el estado del día, configúrala. Si prefieres mantenerlo simple, no es necesario.

