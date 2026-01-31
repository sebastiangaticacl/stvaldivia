# 🤖 CONFIGURAR IA GENERATIVA (OpenAI) PARA BIMBA

## 📋 Resumen

El sistema BIMBA está **listo para usar OpenAI** para generar respuestas inteligentes. Solo necesitas configurar la API key.

## 🎯 Pasos para Configurar

### 1. Obtener API Key de OpenAI

1. Ve a: https://platform.openai.com/api-keys
2. Inicia sesión o crea una cuenta
3. Click en **"Create new secret key"**
4. **Copia la clave** (empieza con `sk-...`)
   - ⚠️ **IMPORTANTE:** Solo se muestra una vez. Guárdala segura.

### 2. Configurar en Desarrollo Local

#### Opción A: Archivo `.env` (recomendado para desarrollo)

Edita el archivo `.env` en la raíz del proyecto:

```bash
OPENAI_API_KEY=${OPENAI_API_KEY}
```

#### Opción B: Variable de entorno del sistema

```bash
export OPENAI_API_KEY="${OPENAI_API_KEY}"
```

### 3. Configurar en Producción (VM)

#### Para el servidor de producción (stvaldivia.cl):

**Opción 1: Variable de entorno permanente**

Edita el archivo de configuración del servicio (systemd, gunicorn, etc.):

```bash
# Ejemplo: /etc/systemd/system/stvaldivia.service
# O donde tengas configurado gunicorn

[Service]
Environment="OPENAI_API_KEY=${OPENAI_API_KEY}"
```

Luego reinicia el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl restart stvaldivia  # o el nombre de tu servicio
```

**Opción 2: Exportar en el script de inicio**

Si tienes un script de inicio, agrega:

```bash
export OPENAI_API_KEY="${OPENAI_API_KEY}"
```

### 4. Verificar que Funciona

Una vez configurado, puedes verificar:

#### A) En el panel de superadmin:

1. Ve a: `https://stvaldivia.cl/admin/bot/logs`
2. Si eres superadmin (`sebagatica`), verás un panel que muestra:
   - Estado del sistema
   - **OpenAI disponible:** ✅ Disponible (gpt-4o-mini)

#### B) Probar el bot:

1. Ve a: `https://stvaldivia.cl/bimba`
2. Envía un mensaje
3. El bot debería responder usando OpenAI generativo

#### C) En los logs:

En `/admin/bot/logs`, los logs mostrarán:
- `source: "openai"` cuando usa IA generativa
- `source: "rule_based"` cuando usa reglas
- `modelo: "gpt-4o-mini"` cuando usa OpenAI

## 🔧 Configuración Avanzada (Opcional)

### Modelo de OpenAI

Por defecto usa `gpt-4o-mini` (más económico). Puedes cambiarlo:

```bash
export OPENAI_DEFAULT_MODEL="gpt-4o"
# o
export OPENAI_DEFAULT_MODEL="gpt-3.5-turbo"
```

### Temperatura

Controla la creatividad de las respuestas (0.0 = más preciso, 1.0 = más creativo):

```bash
export OPENAI_DEFAULT_TEMPERATURE="0.7"  # Por defecto: 0.7
```

### Organization ID (Opcional)

Si tienes una organización en OpenAI:

```bash
export OPENAI_ORGANIZATION_ID="org-..."
```

### Project ID (Opcional)

Para Admin Keys de OpenAI:

```bash
export OPENAI_PROJECT_ID="proj-..."
```

## 🎨 Cómo Funciona el Sistema

El sistema tiene **3 capas** de respuesta:

1. **Capa 1: Detección de Intención**
   - Analiza el mensaje para detectar qué quiere el usuario
   - Ejemplos: "evento_hoy", "precios", "horarios", "djs"

2. **Capa 2: Respuestas por Reglas**
   - Si detecta una intención específica, usa respuestas predefinidas
   - Más rápido y sin costo
   - Ejemplos: horarios, precios básicos, información de eventos

3. **Capa 3: IA Generativa (OpenAI)**
   - Si no hay regla específica, usa OpenAI para generar respuesta
   - Accede al conocimiento completo del sistema BIMBA
   - Respuestas más naturales y contextuales

## 💰 Costos de OpenAI

- **Modelo por defecto:** `gpt-4o-mini`
- **Costo aproximado:** ~$0.15 por 1M tokens de entrada, ~$0.60 por 1M tokens de salida
- **Cada respuesta:** ~500-1000 tokens (muy económico)

**Recomendación:** `gpt-4o-mini` es perfecto para chatbots y muy económico.

## 🚨 Troubleshooting

### El bot no usa OpenAI

1. Verifica que `OPENAI_API_KEY` esté configurada:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. Revisa los logs en `/admin/bot/logs`
   - Si `source: "fallback"` o `source: "rule_based"`, OpenAI no está disponible

3. En producción, verifica que el servicio tenga la variable:
   ```bash
   sudo systemctl show stvaldivia | grep OPENAI
   ```

### Error de autenticación

- Verifica que la API key sea correcta (empieza con `sk-`)
- Verifica que no tenga espacios extra
- Verifica que la cuenta de OpenAI tenga créditos

### Error de rate limit

- OpenAI tiene límites de uso
- El sistema tiene fallback automático a reglas
- Considera usar un modelo más económico o aumentar límites

## ✅ Checklist

- [ ] API key de OpenAI obtenida
- [ ] API key configurada en `.env` (local) o variables de entorno (producción)
- [ ] Servicio reiniciado (si es producción)
- [ ] Verificado en `/admin/bot/logs` que OpenAI está disponible
- [ ] Probado el bot en `/bimba` o `/admin/bot/logs`

## 📚 Más Información

- Código del cliente OpenAI: `app/infrastructure/external/openai_client.py`
- Endpoint del bot: `app/blueprints/api/api_v1.py` → `/api/v1/bot/responder`
- Panel de superadmin: `app/blueprints/admin/bot_routes.py` → `/admin/bot/logs`









