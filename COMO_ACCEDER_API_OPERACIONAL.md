# 📍 ¿Dónde está la API Operacional?

## ✅ La API Operacional YA EXISTE

La API Operacional **ya está implementada** en tu código. Solo necesitas **configurarla** para usarla.

## 📍 Ubicación de los Endpoints

### URLs Disponibles

**En Producción (VM):**
- `http://127.0.0.1:5001/api/v1/operational/summary`
- `http://127.0.0.1:5001/api/v1/operational/sales/summary`
- `http://127.0.0.1:5001/api/v1/operational/products/ranking`
- `http://127.0.0.1:5001/api/v1/operational/deliveries/summary`
- `http://127.0.0.1:5001/api/v1/operational/leaks/today`

**En Desarrollo Local:**
- `http://127.0.0.1:5001/api/v1/operational/summary`
- (mismos endpoints)

## 🔑 Cómo Acceder

### Paso 1: Configurar las Variables

Primero necesitas configurar las variables de entorno. Ejecuta:

```bash
./configurar_api_operacional_vm.sh
```

O manualmente:
1. Genera una API Key: `openssl rand -hex 32`
2. Configura en el servicio systemd o .env:
   - `BIMBA_INTERNAL_API_KEY=tu-api-key-aqui`
   - `BIMBA_INTERNAL_API_BASE_URL=http://127.0.0.1:5001`

### Paso 2: Probar el Endpoint

Una vez configurado, puedes acceder desde:

#### Opción A: Desde la VM (SSH)

```bash
# Conectarse a la VM
ssh stvaldiviazal@34.176.144.166

# Probar el endpoint
curl -H "X-API-KEY: tu-api-key" http://127.0.0.1:5001/api/v1/operational/summary
```

#### Opción B: Desde tu Computadora Local

Si tienes acceso SSH con port forwarding:

```bash
# Crear túnel SSH
ssh -L 5001:127.0.0.1:5001 stvaldiviazal@34.176.144.166

# En otra terminal, probar
curl -H "X-API-KEY: tu-api-key" http://127.0.0.1:5001/api/v1/operational/summary
```

#### Opción C: Panel de Administración

Ve a: **`/admin/bot/config`**

Ahí verás el estado de la API Operacional:
- ✅ Habilitada (si está configurada)
- ⚠️ No configurada (si falta)

## 📋 Endpoints Disponibles

### 1. `/api/v1/operational/summary`
**Resumen completo del día**

```bash
curl -H "X-API-KEY: tu-api-key" \
  http://127.0.0.1:5001/api/v1/operational/summary
```

**Respuesta:**
```json
{
  "status": "ok",
  "date": "2025-01-15",
  "sales": {
    "total_sales": 45,
    "total_revenue": 125000.0,
    "by_payment_method": {
      "cash": 50000.0,
      "debit": 40000.0,
      "credit": 35000.0
    }
  },
  "products": {
    "top": [
      {"product_name": "Cerveza", "quantity_sold": 30, "revenue": 45000.0}
    ]
  },
  "deliveries": {
    "by_bartender": [
      {"bartender_name": "Juan", "total_deliveries": 20}
    ]
  },
  "leaks": {
    "total_suspect_tickets": 0,
    "total_confirmed_leaks": 0
  }
}
```

### 2. `/api/v1/operational/sales/summary`
**Solo resumen de ventas**

```bash
curl -H "X-API-KEY: tu-api-key" \
  http://127.0.0.1:5001/api/v1/operational/sales/summary
```

### 3. `/api/v1/operational/products/ranking`
**Ranking de productos más vendidos**

```bash
curl -H "X-API-KEY: tu-api-key" \
  "http://127.0.0.1:5001/api/v1/operational/products/ranking?limit=10"
```

### 4. `/api/v1/operational/deliveries/summary`
**Resumen de entregas por bartender**

```bash
curl -H "X-API-KEY: tu-api-key" \
  http://127.0.0.1:5001/api/v1/operational/deliveries/summary
```

### 5. `/api/v1/operational/leaks/today`
**Detección de fugas/antifraude**

```bash
curl -H "X-API-KEY: tu-api-key" \
  http://127.0.0.1:5001/api/v1/operational/leaks/today
```

## 🔍 Dónde Está el Código

### Archivo Principal
- **`app/blueprints/api/api_operational.py`** - Todos los endpoints

### Servicio que la Usa
- **`app/application/services/operational_insights_service.py`** - Cliente que llama a la API

### Dónde se Registra
- **`app/__init__.py`** - Se registra el blueprint `operational_api`

## 🎯 Cómo la Usa el Chatbot

El chatbot llama automáticamente a la API Operacional cuando:
1. Detecta intención "estado_noche" (¿cómo va la noche?)
2. Necesita contexto operativo para enriquecer respuestas

**Flujo:**
```
Usuario pregunta → Chatbot detecta intención → 
OperationalInsightsService.get_daily_summary() → 
Llama a /api/v1/operational/summary → 
Usa datos para generar respuesta contextualizada
```

## ✅ Verificar que Funciona

### 1. Verificar Configuración

```bash
# En la VM
ssh stvaldiviazal@34.176.144.166

# Verificar variables en el servicio
sudo systemctl show stvaldivia.service | grep BIMBA_INTERNAL
```

Deberías ver:
```
Environment="BIMBA_INTERNAL_API_KEY=..."
Environment="BIMBA_INTERNAL_API_BASE_URL=..."
```

### 2. Probar el Endpoint

```bash
# Obtener la API key del servicio
API_KEY=$(sudo systemctl show stvaldivia.service | grep BIMBA_INTERNAL_API_KEY | cut -d= -f2 | tr -d '"')

# Probar
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5001/api/v1/operational/summary
```

### 3. Verificar en el Panel

Ve a: **`https://stvaldivia.cl/admin/bot/config`**

Deberías ver:
- **API Operacional**: ✅ Habilitada

## 🚀 Resumen Rápido

1. **La API ya existe** - Está en `app/blueprints/api/api_operational.py`
2. **Solo falta configurarla** - Ejecuta `./configurar_api_operacional_vm.sh`
3. **Accede desde la VM** - `curl -H "X-API-KEY: ..." http://127.0.0.1:5001/api/v1/operational/summary`
4. **El chatbot la usa automáticamente** - No necesitas hacer nada más

## 💡 Nota Importante

La API Operacional es **solo interna** (localhost). No está expuesta públicamente por seguridad. Solo se puede acceder desde:
- La misma VM (127.0.0.1)
- O mediante túnel SSH desde tu computadora

