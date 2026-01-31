# 🤖 Configurar Dialogflow para BIMBA

## 📋 Resumen

El sistema BIMBA ahora soporta **Google Dialogflow** como motor de inteligencia generativa. Dialogflow es ideal para chatbots conversacionales con intenciones y entidades predefinidas.

## 🎯 Ventajas de Dialogflow

- ✅ **Gratis hasta cierto límite** (muy generoso para uso básico)
- ✅ **Gestión visual de intenciones** en la consola de Dialogflow
- ✅ **Entrenamiento fácil** con ejemplos de frases
- ✅ **Manejo de contexto** y sesiones conversacionales
- ✅ **Integración nativa con Google Cloud**

## 📝 Pasos para Configurar

### 1. Crear un Proyecto en Google Cloud

1. Ve a: **https://console.cloud.google.com/**
2. Crea un nuevo proyecto o selecciona uno existente
3. Anota el **Project ID** (necesario para la configuración)

### 2. Habilitar Dialogflow API

1. En la consola de Google Cloud, ve a **"APIs y servicios" > "Biblioteca"**
2. Busca **"Dialogflow API"**
3. Click en **"Habilitar"**

### 3. Crear un Agente en Dialogflow

1. Ve a: **https://dialogflow.cloud.google.com/**
2. Selecciona tu proyecto de Google Cloud
3. Click en **"Crear agente"**
4. Configura:
   - **Nombre**: BIMBA Chatbot (o el que prefieras)
   - **Idioma**: Español (es)
   - **Zona horaria**: America/Santiago
5. Click en **"Crear"**

### 4. Crear una Cuenta de Servicio

1. En Google Cloud Console, ve a **"IAM y administración" > "Cuentas de servicio"**
2. Click en **"Crear cuenta de servicio"**
3. Configura:
   - **Nombre**: `bimba-dialogflow-client`
   - **Descripción**: Cliente para Dialogflow de BIMBA
4. Click en **"Crear y continuar"**
5. Asigna el rol: **"Cliente API de Dialogflow"**
6. Click en **"Continuar"** y luego **"Listo"**

### 5. Generar Clave JSON

1. En la lista de cuentas de servicio, click en la cuenta que acabas de crear
2. Ve a la pestaña **"Claves"**
3. Click en **"Agregar clave" > "Crear nueva clave"**
4. Selecciona **JSON**
5. Click en **"Crear"**
6. **Guarda el archivo JSON** en un lugar seguro (ej: `credentials/dialogflow-credentials.json`)

### 6. Configurar Intenciones en Dialogflow

1. En la consola de Dialogflow, ve a **"Intenciones"**
2. Crea intenciones básicas como:
   - **Saludo**: "Hola", "Buenos días", "¿Cómo estás?"
   - **Eventos**: "¿Qué eventos hay hoy?", "¿Cuándo es el próximo evento?"
   - **Horarios**: "¿A qué hora abren?", "¿Cuál es el horario?"
   - **Precios**: "¿Cuánto cuesta la entrada?", "¿Hay descuentos?"
3. Para cada intención:
   - Agrega **Frases de entrenamiento** (ejemplos de lo que los usuarios dirían)
   - Configura **Respuestas** (lo que el bot responderá)

### 7. Configurar en el Proyecto

#### Opción A: Archivo `.env` (Recomendado para desarrollo)

Edita el archivo `.env` en la raíz del proyecto:

```bash
# Habilitar Dialogflow (por defecto está habilitado)
USE_DIALOGFLOW=true

# Project ID de Google Cloud
DIALOGFLOW_PROJECT_ID=tu-project-id-aqui

# Ruta al archivo JSON de credenciales
DIALOGFLOW_CREDENTIALS_PATH=./credentials/dialogflow-credentials.json

# Código de idioma (español por defecto)
DIALOGFLOW_LANGUAGE_CODE=es
```

#### Opción B: Variable de Entorno del Sistema

```bash
export USE_DIALOGFLOW=true
export DIALOGFLOW_PROJECT_ID=tu-project-id-aqui
export DIALOGFLOW_CREDENTIALS_PATH=/ruta/completa/credentials.json
export DIALOGFLOW_LANGUAGE_CODE=es
```

### 8. Instalar Dependencias

```bash
pip install google-cloud-dialogflow
```

O si usas `requirements.txt`:

```bash
pip install -r requirements.txt
```

## ✅ Verificar que Funciona

### 1. Reiniciar el servidor

Si tu servidor Flask está corriendo, reinícialo:

```bash
python run_local.py
# O
flask run
```

### 2. Probar el chatbot

1. Visita: **http://localhost:5000/bimba**
2. Envía un mensaje de prueba
3. El bot debería responder usando Dialogflow

### 3. Verificar en los logs

Busca mensajes como:
- `✅ Dialogflow configurado correctamente`
- `source: "dialogflow"` en las respuestas

## 🔄 Cambiar entre Dialogflow y OpenAI

Puedes cambiar fácilmente entre Dialogflow y OpenAI usando la variable `USE_DIALOGFLOW`:

- **`USE_DIALOGFLOW=true`**: Usa Dialogflow (por defecto)
- **`USE_DIALOGFLOW=false`**: Usa OpenAI como fallback

El sistema intentará usar Dialogflow primero, y si falla, usará OpenAI automáticamente.

## 🔍 Solución de Problemas

### Error: "DIALOGFLOW_PROJECT_ID no configurado"

- Verifica que `DIALOGFLOW_PROJECT_ID` esté en tu `.env`
- Asegúrate de que el Project ID sea correcto (no el nombre del proyecto, sino el ID)

### Error: "google-cloud-dialogflow no está instalado"

```bash
pip install google-cloud-dialogflow
```

### Error: "No se pudo autenticar"

- Verifica que el archivo JSON de credenciales exista y esté en la ruta correcta
- Asegúrate de que la cuenta de servicio tenga el rol "Cliente API de Dialogflow"
- Verifica que la Dialogflow API esté habilitada en tu proyecto

### El bot no responde

- Revisa los logs del servidor para ver errores específicos
- Verifica que el agente de Dialogflow tenga intenciones configuradas
- Asegúrate de que las intenciones tengan respuestas configuradas

## 📚 Recursos Adicionales

- **Documentación de Dialogflow**: https://cloud.google.com/dialogflow/docs
- **Consola de Dialogflow**: https://dialogflow.cloud.google.com/
- **Google Cloud Console**: https://console.cloud.google.com/

## 🎉 ¡Listo!

Una vez configurado, BIMBA usará Dialogflow para generar respuestas inteligentes basadas en las intenciones que configures en la consola.

