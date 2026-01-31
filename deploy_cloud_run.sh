#!/bin/bash
# Script para deploy automático en Cloud Run
# Ejecutar después de: gcloud auth login

# No usar set -e para permitir continuar si algunas APIs ya están habilitadas

echo "🚀 DEPLOY AUTOMÁTICO A CLOUD RUN"
echo "=================================="
echo ""

# Configurar proyecto
PROJECT_ID="stvaldivia"
REGION="southamerica-west1"
SERVICE_NAME="bimba"

echo "📋 Configuración:"
echo "  Proyecto: $PROJECT_ID"
echo "  Región: $REGION"
echo "  Servicio: $SERVICE_NAME"
echo ""

# Verificar autenticación
echo "🔐 Verificando autenticación..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ ERROR: No hay cuenta autenticada"
    echo "Ejecuta primero: gcloud auth login"
    exit 1
fi

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "✅ Autenticado como: $ACTIVE_ACCOUNT"
echo ""

# Configurar proyecto
echo "⚙️  Configurando proyecto..."
gcloud config set project $PROJECT_ID
gcloud config get-value project
echo ""

# Habilitar APIs necesarias
echo "🔧 Habilitando APIs..."
gcloud services enable run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project=$PROJECT_ID || echo "⚠️  Algunas APIs ya están habilitadas"
echo ""

# Variables de entorno
FLASK_ENV="production"
FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-}"
DATABASE_URL="${DATABASE_URL:-}"

# Variables de OpenAI para el chatbot BIMBA
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
USE_DIALOGFLOW="${USE_DIALOGFLOW:-false}"

# Variables de GetNet (para pagos online)
# IMPORTANTE: Configurar estas variables según tu cuenta GetNet
GETNET_API_BASE_URL="${GETNET_API_BASE_URL:-https://checkout.test.getnet.cl}"
GETNET_LOGIN="${GETNET_LOGIN:-}"
GETNET_TRANKEY="${GETNET_TRANKEY:-}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://stvaldivia.cl}"
GETNET_DEMO_MODE="${GETNET_DEMO_MODE:-false}"

echo "📦 Variables de entorno configuradas:"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  FLASK_SECRET_KEY=***"
echo "  DATABASE_URL=***"
echo "  OPENAI_API_KEY=${OPENAI_API_KEY:+***configurado}"
echo "  USE_DIALOGFLOW=$USE_DIALOGFLOW"
echo "  GETNET_API_BASE_URL=$GETNET_API_BASE_URL"
echo "  GETNET_LOGIN=${GETNET_LOGIN:+***configurado}"
echo "  GETNET_TRANKEY=${GETNET_TRANKEY:+***configurado}"
echo "  PUBLIC_BASE_URL=$PUBLIC_BASE_URL"
echo "  GETNET_DEMO_MODE=$GETNET_DEMO_MODE"
echo ""

# Validación mínima (evita deploy con valores hardcodeados o vacíos)
if [ -z "$FLASK_SECRET_KEY" ]; then
  echo "❌ ERROR: FLASK_SECRET_KEY no está configurada. Exporta la variable antes de ejecutar."
  exit 1
fi
if [ -z "$DATABASE_URL" ]; then
  echo "❌ ERROR: DATABASE_URL no está configurada. Exporta la variable antes de ejecutar."
  exit 1
fi

# Verificar que Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo "❌ ERROR: Dockerfile no encontrado"
    exit 1
fi

echo "✅ Dockerfile encontrado"
echo ""

# Deploy a Cloud Run
echo "🚀 Iniciando deploy a Cloud Run..."
echo "   Esto puede tardar 5-10 minutos..."
echo ""

# Construir lista de variables de entorno
ENV_VARS="FLASK_ENV=$FLASK_ENV,FLASK_SECRET_KEY=$FLASK_SECRET_KEY,DATABASE_URL=$DATABASE_URL"
ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
ENV_VARS="$ENV_VARS,USE_DIALOGFLOW=$USE_DIALOGFLOW"
ENV_VARS="$ENV_VARS,GETNET_API_BASE_URL=$GETNET_API_BASE_URL"
ENV_VARS="$ENV_VARS,PUBLIC_BASE_URL=$PUBLIC_BASE_URL"
ENV_VARS="$ENV_VARS,GETNET_DEMO_MODE=$GETNET_DEMO_MODE"

# Agregar credenciales de GetNet si están configuradas
if [ -n "$GETNET_LOGIN" ]; then
    ENV_VARS="$ENV_VARS,GETNET_LOGIN=$GETNET_LOGIN"
fi
if [ -n "$GETNET_TRANKEY" ]; then
    ENV_VARS="$ENV_VARS,GETNET_TRANKEY=$GETNET_TRANKEY"
fi

gcloud run deploy $SERVICE_NAME \
    --source . \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="$ENV_VARS" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0 \
    --project=$PROJECT_ID

echo ""
echo "✅ DEPLOY COMPLETADO"
echo ""

# Obtener URL del servicio
echo "🔗 Obteniendo URL del servicio..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)" \
    --project=$PROJECT_ID)

echo ""
echo "=================================="
echo "✅ SERVICIO DESPLEGADO EXITOSAMENTE"
echo "=================================="
echo ""
echo "📍 URL del servicio:"
echo "   $SERVICE_URL"
echo ""
echo "🧪 Probando endpoint..."
curl -s "$SERVICE_URL/api/v1/public/evento/hoy" | head -c 200
echo ""
echo ""
echo "📊 Ver logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""
echo "🎯 Próximos pasos:"
echo "   1. Crear Load Balancer con IP estática"
echo "   2. Configurar DNS para apuntar al Load Balancer"
echo "   3. Configurar SSL automático"
echo ""

