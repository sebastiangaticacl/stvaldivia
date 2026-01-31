# BIMBA System

Sistema de gestión BIMBA.

## Inicio Rápido

### Instalación

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Ejecutar localmente

```bash
python3 run_local.py
```

El servidor estará disponible en: `http://localhost:5001/`

## Estructura del Proyecto

```
tickets/
├── app/              # Aplicación Flask principal
├── requirements.txt  # Dependencias Python
└── run_local.py     # Script para arrancar servidor
```

## Desarrollo

- Servidor local: `http://localhost:5001/`
- Base de datos: SQLite local (se crea automáticamente en `instance/`)
