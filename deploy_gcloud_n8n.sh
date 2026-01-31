#!/bin/bash
# Script para deploy en Google Cloud Run con integración n8n
# Incluye todas las correcciones recientes

set -e

echo "🚀 DEPLOY A GOOGLE CLOUD RUN"
echo "============================"
echo ""

# Configuración del proyecto
PROJECT_ID="${GCP_PROJECT:-stvaldivia}"
REGION="${GCP_REGION:-southamerica-west1}"
SERVICE_NAME="${SERVICE_NAME:-bimba}"

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
echo "✅ Proyecto configurado: $(gcloud config get-value project)"
echo ""

# Habilitar APIs necesarias
echo "🔧 Habilitando APIs necesarias..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    --project=$PROJECT_ID 2>/dev/null || echo "⚠️  Algunas APIs ya están habilitadas"
echo ""

# Variables de entorno OBLIGATORIAS
FLASK_ENV="production"
FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-}"

# DATABASE_URL - Si no está configurado, pedir al usuario
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL no está configurado"
    echo "Por favor, proporciona el DATABASE_URL de tu base de datos:"
    echo "   Ejemplo PostgreSQL: postgresql://user:pass@host:5432/database"
    echo "   Ejemplo Cloud SQL: postgresql://user:pass@/database?host=/cloudsql/PROJECT:REGION:INSTANCE"
    echo ""
    read -p "DATABASE_URL: " DATABASE_URL
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ ERROR: DATABASE_URL es requerido"
        exit 1
    fi
fi

# Variables de entorno OPCIONALES (pueden estar vacías)
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
N8N_WEBHOOK_URL="${N8N_WEBHOOK_URL:-}"
N8N_WEBHOOK_SECRET="${N8N_WEBHOOK_SECRET:-}"
N8N_API_KEY="${N8N_API_KEY:-}"

echo "📦 Variables de entorno:"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  FLASK_SECRET_KEY=***"
echo "  DATABASE_URL=${DATABASE_URL:0:30}***"
if [ -n "$OPENAI_API_KEY" ]; then
    echo "  OPENAI_API_KEY=***configurado"
fi
if [ -n "$N8N_WEBHOOK_URL" ]; then
    echo "  N8N_WEBHOOK_URL=***configurado"
fi
if [ -n "$N8N_WEBHOOK_SECRET" ]; then
    echo "  N8N_WEBHOOK_SECRET=***configurado"
fi
if [ -n "$N8N_API_KEY" ]; then
    echo "  N8N_API_KEY=***configurado"
fi
echo ""

# Verificar archivos necesarios
echo "🔍 Verificando archivos necesarios..."
if [ ! -f "Dockerfile" ]; then
    echo "❌ ERROR: Dockerfile no encontrado"
    exit 1
fi
echo "✅ Dockerfile encontrado"

if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt no encontrado"
    exit 1
fi
echo "✅ requirements.txt encontrado"

# Verificar que las correcciones de n8n están presentes
echo "🔍 Verificando integración n8n..."
if grep -q "send_delivery_created" app/helpers/logs.py && \
   grep -q "send_sale_created" app/blueprints/pos/views/sales.py && \
   grep -q "openN8nConfigModal" app/templates/admin/panel_control.html; then
    echo "✅ Integración n8n verificada"
else
    echo "⚠️  Advertencia: Algunas integraciones de n8n podrían no estar presentes"
fi
echo ""

# Construir lista de variables de entorno
ENV_VARS="FLASK_ENV=$FLASK_ENV,FLASK_SECRET_KEY=$FLASK_SECRET_KEY,DATABASE_URL=$DATABASE_URL"

# Agregar variables opcionales si están configuradas
if [ -n "$OPENAI_API_KEY" ]; then
    ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
fi
if [ -n "$N8N_WEBHOOK_URL" ]; then
    ENV_VARS="$ENV_VARS,N8N_WEBHOOK_URL=$N8N_WEBHOOK_URL"
fi
if [ -n "$N8N_WEBHOOK_SECRET" ]; then
    ENV_VARS="$ENV_VARS,N8N_WEBHOOK_SECRET=$N8N_WEBHOOK_SECRET"
fi
if [ -n "$N8N_API_KEY" ]; then
    ENV_VARS="$ENV_VARS,N8N_API_KEY=$N8N_API_KEY"
fi

# Deploy a Cloud Run
echo "🚀 Iniciando deploy a Cloud Run..."
echo "   Esto puede tardar 5-10 minutos..."
echo ""

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

# Probar endpoint
echo "🧪 Probando endpoint..."
sleep 5  # Esperar un poco para que el servicio esté listo
if curl -s -f "$SERVICE_URL/api/v1/public/evento/hoy" > /dev/null 2>&1; then
    echo "✅ Servicio respondiendo correctamente"
    curl -s "$SERVICE_URL/api/v1/public/evento/hoy" | head -c 200
    echo ""
else
    echo "⚠️  El servicio podría estar iniciando. Espera unos minutos y prueba de nuevo."
fi
echo ""

echo "📊 Comandos útiles:"
echo "   Ver logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""
echo "   Ver detalles del servicio:"
echo "   gcloud run services describe $SERVICE_NAME --region=$REGION"
echo ""
echo "   Actualizar variables de entorno:"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --update-env-vars KEY=VALUE"
echo ""

echo "🎯 Próximos pasos:"
echo "   1. Verificar que el servicio funciona: $SERVICE_URL"
echo "   2. Configurar n8n desde: $SERVICE_URL/admin/panel_control"
echo "   3. Configurar dominio personalizado si es necesario"
echo ""
