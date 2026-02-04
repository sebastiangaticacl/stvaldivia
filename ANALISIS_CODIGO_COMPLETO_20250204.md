# Análisis Completo del Sitio StValdivia
**Fecha:** 4 de febrero de 2025

## Resumen ejecutivo
Sistema BIMBA POS / StValdivia: aplicación Flask para operación nocturna (TPV, inventarios, entregas, guardarropía, ecommerce, kiosco). Soporta MySQL, PostgreSQL y SQLite. Deploy en Cloud Run, VM con Gunicorn, y hosting Antigravity.

---

## Arquitectura principal

### Stack
- **Backend:** Flask 2.3, Flask-SocketIO, SQLAlchemy 2.0
- **Bases de datos:** MySQL (producción), PostgreSQL (legacy), SQLite (desarrollo)
- **Servidor:** Gunicorn + eventlet, wsgi.py como entry point

### Estructura `app/`
```
app/
├── __init__.py          # create_app(), BIMBA POS v4.0
├── application/         # Servicios de aplicación (41 archivos)
├── blueprints/          # Módulos por dominio
│   ├── admin/           # Bot IA, payment machines
│   ├── api/             # api_v1, api_operational
│   ├── bartender_turnos/
│   ├── ecommerce/       # Venta entradas, GetNet
│   ├── equipo/
│   ├── guardarropia/    # POS guardarropía
│   ├── kiosk/
│   ├── notifications/
│   └── pos/             # Caja TPV principal
├── domain/              # delivery, inventory, shift, survey
├── helpers/             # ~70 helpers (auth, CSRF, GetNet, n8n, etc.)
├── models/              # 31 modelos SQLAlchemy
├── routes/              # home, auth, api, n8n, product, recipe, etc.
├── services/            # monitoring, pos, recipe, sale_delivery
├── static/              # CSS, JS, imágenes
└── templates/           # 102 templates Jinja2
```

### Rutas principales
- **/** — Home (gate PIN opcional, menú principal)
- **/opera** — Landing Ópera (sistema operativo nocturno)
- **/bimba** — Chat público con agente IA
- **/caja** — POS principal (login, ventas)
- **/kiosk** — Kiosco
- **/ecommerce** — Venta de entradas
- **/guardarropia** — POS guardarropía
- **/admin** — Panel admin Bot IA
- **/api** — APIs internas
- **/encuesta** — Encuestas

### Integraciones
- **Pagos:** GetNet (web checkout), SumUp
- **IA:** OpenAI, Dialogflow (opcional)
- **Automatización:** n8n webhooks
- **Meta:** Instagram, Facebook
- **Email:** SMTP configurable

### Configuración crítica (variables de entorno)
- `FLASK_SECRET_KEY` — Obligatorio en producción
- `DATABASE_URL` — Obligatorio en producción
- `APPLICATION_ROOT` — Prefijo (ej. /stvaldivia)
- `SITE_CLOSED` — Cerrar sitio al público
- `MENU_GATE_PIN` — PIN para acceso al menú
- `LOCAL_ONLY` — Desactiva integraciones externas

### index.html (raíz)
Landing estática **Ópera** — "Tú creas. Nosotros operamos." — Packs: Operar Entregas, Operar Entregas e Inventarios, Operar por Completo. Tema oscuro, minimalista.

### Bimbaverso
Chatbot en `bimbaverso/` (backend Flask + frontend). Panel de control en `bimbaverso_panel/`.

---

## Archivos de deploy
- `wsgi.py` — Entry point Gunicorn
- `Dockerfile` — Para Cloud Run
- `deploy_completo.sh`, `deploy_produccion_completo.sh`
- `backup_sitio_completo.sh` — Backup servidor (BD + archivos)
- `.cpanel.yml` — Deploy cPanel
- `.htaccess` — Apache

---

## Estado del repositorio (4 feb 2025)
- Rama: main
- Cambios pendientes: .vscode/settings.json
- node_modules: no está en .gitignore (debería agregarse)
