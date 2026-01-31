#!/bin/bash
# Script para verificar que el sistema está funcionando correctamente en producción

set -e

echo "🔍 VERIFICACIÓN DE PRODUCCIÓN"
echo "=============================="
echo ""

# Configuración
PROJECT_ID="stvaldiviacl"
REGION="southamerica-west1"
SERVICE_NAME="bimba"

# Obtener URL del servicio
echo "📍 Obteniendo URL del servicio..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(status.url)" \
    --project=$PROJECT_ID 2>/dev/null || echo "")

if [ -z "$SERVICE_URL" ]; then
    echo "❌ ERROR: No se pudo obtener la URL del servicio"
    echo "   Verifica que el servicio '$SERVICE_NAME' existe en la región '$REGION'"
    exit 1
fi

echo "✅ URL del servicio: $SERVICE_URL"
echo ""

# Verificar que el servicio responde
echo "🧪 Verificando que el servicio responde..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/" || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "✅ Servicio respondiendo correctamente (HTTP $HTTP_CODE)"
else
    echo "⚠️  Servicio respondió con código HTTP $HTTP_CODE"
fi
echo ""

# Verificar endpoint de ecommerce
echo "🛒 Verificando endpoint de ecommerce..."
ECOMMERCE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/ecommerce/" || echo "000")

if [ "$ECOMMERCE_CODE" = "200" ]; then
    echo "✅ Endpoint de ecommerce funcionando (HTTP $ECOMMERCE_CODE)"
else
    echo "⚠️  Endpoint de ecommerce respondió con código HTTP $ECOMMERCE_CODE"
fi
echo ""

# Verificar variables de entorno
echo "⚙️  Verificando variables de entorno..."
ENV_VARS=$(gcloud run services describe $SERVICE_NAME \
    --region=$REGION \
    --format="value(spec.template.spec.containers[0].env)" \
    --project=$PROJECT_ID 2>/dev/null || echo "")

if [ -n "$ENV_VARS" ]; then
    echo "✅ Variables de entorno configuradas"
    
    # Verificar variables críticas
    if echo "$ENV_VARS" | grep -q "FLASK_ENV=production"; then
        echo "  ✅ FLASK_ENV=production"
    else
        echo "  ⚠️  FLASK_ENV no está configurado como 'production'"
    fi
    
    if echo "$ENV_VARS" | grep -q "DATABASE_URL"; then
        echo "  ✅ DATABASE_URL configurado"
    else
        echo "  ❌ DATABASE_URL no configurado"
    fi
    
    if echo "$ENV_VARS" | grep -q "PUBLIC_BASE_URL"; then
        echo "  ✅ PUBLIC_BASE_URL configurado"
    else
        echo "  ⚠️  PUBLIC_BASE_URL no configurado (necesario para pagos online)"
    fi
    
    if echo "$ENV_VARS" | grep -q "GETNET_LOGIN"; then
        echo "  ✅ GETNET_LOGIN configurado"
    else
        echo "  ⚠️  GETNET_LOGIN no configurado (necesario para pagos online reales)"
    fi
    
    if echo "$ENV_VARS" | grep -q "GETNET_TRANKEY"; then
        echo "  ✅ GETNET_TRANKEY configurado"
    else
        echo "  ⚠️  GETNET_TRANKEY no configurado (necesario para pagos online reales)"
    fi
else
    echo "⚠️  No se pudieron obtener las variables de entorno"
fi
echo ""

# Verificar logs recientes
echo "📋 Verificando logs recientes..."
echo "   (últimas 10 líneas)"
gcloud run services logs read $SERVICE_NAME \
    --region=$REGION \
    --limit=10 \
    --project=$PROJECT_ID 2>/dev/null | tail -10 || echo "⚠️  No se pudieron obtener los logs"
echo ""

echo "=============================="
echo "✅ VERIFICACIÓN COMPLETADA"
echo "=============================="
echo ""
echo "🔗 URL del servicio: $SERVICE_URL"
echo "🛒 Ecommerce: $SERVICE_URL/ecommerce/"
echo ""
echo "📊 Ver todos los logs:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50"
echo ""



