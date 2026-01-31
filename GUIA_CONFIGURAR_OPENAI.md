# 🤖 Guía Rápida: Configurar OpenAI para BIMBA

## ✅ Configuración Completada

El sistema está listo para usar inteligencia generativa. Solo necesitas agregar tu API key de OpenAI.

## 🚀 Opción 1: Script Automático (Recomendado)

Ejecuta el script interactivo:

```bash
./configurar_openai_local.sh
```

El script te guiará paso a paso para:
1. Obtener tu API key de OpenAI
2. Configurarla en el archivo `.env`
3. Verificar que todo esté correcto

## 🚀 Opción 2: Manual

### Paso 1: Obtener API Key de OpenAI

1. Ve a: **https://platform.openai.com/api-keys**
2. Inicia sesión o crea una cuenta en OpenAI
3. Click en **"Create new secret key"**
4. **Copia la clave** (empieza con `sk-...`)
   - ⚠️ **IMPORTANTE:** Solo se muestra una vez. Guárdala segura.

### Paso 2: Configurar en el archivo .env

Edita el archivo `.env` en la raíz del proyecto y reemplaza:

```bash
OPENAI_API_KEY=TU_API_KEY_AQUI
```

Por tu API key real:

```bash
OPENAI_API_KEY=<OPENAI_API_KEY>
```

## ✅ Verificar que Funciona

### 1. Reiniciar el servidor

Si tu servidor Flask está corriendo, reinícialo para que cargue la nueva configuración:

```bash
# Si usas run_local.py
python run_local.py

# O si usas flask run
flask run
```

### 2. Probar el chatbot

1. Visita: **http://localhost:5000/bimba**
2. Envía un mensaje de prueba (ej: "Hola, ¿qué eventos hay hoy?")
3. El bot debería responder usando inteligencia generativa

### 3. Verificar en el panel de admin

Si eres administrador, puedes verificar el estado en:

- **http://localhost:5000/admin/bot/config**

Deberías ver:
- ✅ **OpenAI disponible:** Disponible (gpt-4o-mini)

## 🔍 Solución de Problemas

### El bot no responde con IA generativa

1. **Verifica que la API key esté correcta:**
   ```bash
   cat .env | grep OPENAI_API_KEY
   ```

2. **Verifica que el archivo .env se esté cargando:**
   - Asegúrate de que el archivo `.env` esté en la raíz del proyecto
   - Reinicia el servidor Flask

3. **Revisa los logs:**
   - Busca mensajes de error relacionados con OpenAI
   - Verifica que no haya problemas de autenticación

### Error: "OPENAI_API_KEY no configurada"

- Asegúrate de que el archivo `.env` existe y tiene la variable `OPENAI_API_KEY`
- Verifica que no haya espacios extra alrededor del signo `=`
- Reinicia el servidor Flask

### El bot funciona pero usa respuestas por reglas

- Esto significa que OpenAI no está disponible
- Verifica tu API key
- Revisa que tengas créditos en tu cuenta de OpenAI
- Verifica tu conexión a internet

## 📊 Modelo por Defecto

El sistema usa **gpt-4o-mini** por defecto, que es:
- ✅ Más económico que GPT-4
- ✅ Rápido y eficiente
- ✅ Perfecto para chatbots

Si quieres cambiar el modelo, edita `.env`:

```bash
OPENAI_DEFAULT_MODEL=gpt-4o-mini  # Por defecto (recomendado)
# O usa otro modelo:
# OPENAI_DEFAULT_MODEL=gpt-4
# OPENAI_DEFAULT_MODEL=gpt-3.5-turbo
```

## 💡 Notas Importantes

- El archivo `.env` está en `.gitignore`, así que no se subirá a Git
- La API key es privada y no debe compartirse
- El bot tiene fallbacks: si OpenAI no está disponible, usará respuestas basadas en reglas
- Los costos de OpenAI se basan en el uso (tokens). gpt-4o-mini es muy económico

## 🎉 ¡Listo!

Una vez configurado, BIMBA usará inteligencia generativa para responder de forma más natural y contextual.

