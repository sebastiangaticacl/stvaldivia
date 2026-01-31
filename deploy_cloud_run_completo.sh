#!/bin/bash
# Script para deploy completo en Cloud Run
# Configura y despliega el servicio BIMBA en Google Cloud Run

set -e  # Salir si hay errores

echo "🚀 DEPLOY AUTOMÁTICO A CLOUD RUN"
echo "=================================="
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

# Variables de entorno
FLASK_ENV="production"
FLASK_SECRET_KEY="${FLASK_SECRET_KEY:-}"

# DATABASE_URL - Si no está configurado, pedir al usuario
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL no está configurado"
    echo "Por favor, proporciona el DATABASE_URL de tu base de datos MySQL/PostgreSQL:"
    echo "   Ejemplo MySQL: mysql+mysqlconnector://user:pass@host:3306/database"
    echo "   Ejemplo PostgreSQL: postgresql://user:pass@host:5432/database"
    echo ""
    read -p "DATABASE_URL: " DATABASE_URL
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ ERROR: DATABASE_URL es requerido"
        exit 1
    fi
fi

echo "📦 Variables de entorno:"
echo "  FLASK_ENV=$FLASK_ENV"
echo "  FLASK_SECRET_KEY=***"
echo "  DATABASE_URL=${DATABASE_URL:0:30}***"
echo ""

# Verificar que Dockerfile existe
if [ ! -f "Dockerfile" ]; then
    echo "❌ ERROR: Dockerfile no encontrado"
    exit 1
fi

echo "✅ Dockerfile encontrado"
echo ""

# Verificar que requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "❌ ERROR: requirements.txt no encontrado"
    exit 1
fi

echo "✅ requirements.txt encontrado"
echo ""

# Deploy a Cloud Run
echo "🚀 Iniciando deploy a Cloud Run..."
echo "   Esto puede tardar 5-10 minutos..."
echo ""

gcloud run deploy $SERVICE_NAME \
    --source . \
    --region=$REGION \
    --platform=managed \
    --allow-unauthenticated \
    --set-env-vars="FLASK_ENV=$FLASK_ENV,FLASK_SECRET_KEY=$FLASK_SECRET_KEY,DATABASE_URL=$DATABASE_URL" \
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
if curl -s -f "$SERVICE_URL/api/v1/public/evento/hoy" > /dev/null 2>&1; then
    echo "✅ Servicio respondiendo correctamente"
    curl -s "$SERVICE_URL/api/v1/public/evento/hoy" | head -c 200
    echo ""
else
    echo "⚠️  El servicio podría estar iniciando. Espera unos minutos y prueba de nuevo."
fi
echo ""
echo "📊 Ver logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""
echo "🎯 Próximos pasos:"
echo "   1. Verificar que el servicio funciona correctamente"
echo "   2. Configurar dominio personalizado si es necesario"
echo "   3. Configurar Load Balancer con IP estática si es necesario"
echo ""

