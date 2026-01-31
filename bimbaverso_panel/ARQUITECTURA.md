# Arquitectura BIMBAVERSO

## Flujo de Datos

```
Agentes operan → Backend recibe datos → Panel controla agentes
                ↓
        Métricas expuestas vía API
                ↓
        Dashboard visualiza
```

## Componentes

### 1. Agentes
Los agentes del BIMBAVERSO operan de forma independiente:
- **RRSS**: Agente de redes sociales
- **Optimización**: Agente de optimización
- **Mixología**: Agente de mixología

### 2. Backend (Flask - Puerto 5002)
- Recibe datos de los agentes
- Gestiona estado de agentes (activo/inactivo)
- Expone métricas vía API REST
- Persiste estado en `agentes_state.json`

**Endpoints:**
- `GET /api/panel/status` - Estado general del sistema
- `GET /api/panel/agentes` - Estado de agentes (True/False)
- `POST /api/panel/agente/toggle` - Activar/desactivar agente
- `GET /api/panel/metricas` - Métricas del día

### 3. Panel de Control
Interfaz para controlar agentes:
- `controls.html` - Activar/desactivar agentes
- `index.html` - Ver estado general

### 4. Dashboard
Visualización de métricas:
- `dashboard.html` - Gráficos interactivos (Chart.js)
- `metricas.html` - Métricas en formato JSON

## Flujo Completo

1. **Agentes operan** → Generan datos y eventos
2. **Backend recibe datos** → Procesa y almacena información
3. **Panel controla agentes** → Administrador activa/desactiva agentes
4. **Métricas expuestas vía API** → Backend sirve datos estructurados
5. **Dashboard visualiza** → Frontend muestra gráficos y métricas

## Archivos del Sistema

```
bimbaverso_panel/
├── backend/
│   ├── app/
│   │   ├── __init__.py         # Factory Flask
│   │   ├── routes/
│   │   │   └── panel.py        # Endpoints API
│   │   └── services/
│   │       └── agentes.py      # Gestión de estado
│   ├── run.py                  # Servidor Flask
│   └── agentes_state.json      # Estado persistente
└── frontend/
    ├── index.html              # Panel principal
    ├── controls.html           # Control de agentes
    ├── metricas.html           # Métricas JSON
    └── dashboard.html          # Dashboard con gráficos
```

## Tecnologías

- **Backend**: Flask, Python
- **Frontend**: HTML, JavaScript, Chart.js
- **API**: REST JSON
- **Persistencia**: JSON files

