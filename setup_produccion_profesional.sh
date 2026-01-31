#!/usr/bin/env bash
#
# Script de configuración profesional para producción
# Configura: systemd, nginx, seguridad, logging, monitoreo
#
set -euo pipefail

# ============================================
# CONFIGURACIÓN
# ============================================
APP_NAME="stvaldivia"
APP_DIR="/var/www/stvaldivia"
VENV_DIR="${APP_DIR}/venv"
SERVICE_NAME="${APP_NAME}"
RUN_USER="deploy"
RUN_GROUP="www-data"
UPSTREAM_HOST="127.0.0.1"
UPSTREAM_PORT="5001"
UPSTREAM="${UPSTREAM_HOST}:${UPSTREAM_PORT}"

# Directorios de configuración
ENV_DIR="/etc/${APP_NAME}"
ENV_FILE="${ENV_DIR}/${APP_NAME}.env"
NGINX_SITE="/etc/nginx/sites-available/${APP_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${APP_NAME}"
LOG_DIR="${APP_DIR}/logs"
SYSTEMD_SERVICE="/etc/systemd/system/${SERVICE_NAME}.service"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# ============================================
# VALIDACIONES PRELIMINARES
# ============================================
log_info "Validando prerequisitos..."

if [ ! -d "$APP_DIR" ]; then
    log_error "El directorio de la aplicación no existe: $APP_DIR"
    exit 1
fi

if [ ! -x "${VENV_DIR}/bin/python" ]; then
    log_error "El entorno virtual no existe o no es válido: $VENV_DIR"
    exit 1
fi

if ! id "$RUN_USER" &>/dev/null; then
    log_error "El usuario $RUN_USER no existe"
    exit 1
fi

log_success "Prerequisitos validados"

# ============================================
# ACTUALIZACIÓN DE PAQUETES
# ============================================
log_info "Actualizando paquetes del sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl git nginx ufw fail2ban unattended-upgrades >/dev/null 2>&1 || true
log_success "Paquetes actualizados"

# ============================================
# CONFIGURACIÓN DE LOGS
# ============================================
log_info "Configurando directorio de logs..."
mkdir -p "$LOG_DIR"
chown -R "${RUN_USER}:${RUN_GROUP}" "$LOG_DIR"
chmod 755 "$LOG_DIR"
log_success "Logs configurados: $LOG_DIR"

# ============================================
# VARIABLES DE ENTORNO SEGURAS
# ============================================
log_info "Configurando variables de entorno..."
mkdir -p "$ENV_DIR"
chmod 700 "$ENV_DIR"

if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" <<EOF
# Variables de entorno para ${APP_NAME}
# Este archivo es sensible - NO subir a git
# Permisos: root:root 600

# Flask
FLASK_ENV=production
FLASK_SECRET_KEY=CHANGE_ME_TO_A_STRONG_SECRET_KEY_MIN_32_CHARS

# Database (PostgreSQL recomendado en producción)
# DATABASE_URL=postgresql://user:password@127.0.0.1:5432/dbname

# APIs externas (opcionales)
# OPENAI_API_KEY=<OPENAI_API_KEY>
# BIMBA_INTERNAL_API_KEY=...

# Logging
ENABLE_FILE_LOGGING=true
EOF
    log_warning "Archivo de entorno creado: $ENV_FILE"
    log_warning "IMPORTANTE: Edita $ENV_FILE y configura FLASK_SECRET_KEY y DATABASE_URL"
else
    log_info "Archivo de entorno ya existe: $ENV_FILE"
fi

chown root:root "$ENV_FILE"
chmod 600 "$ENV_FILE"
log_success "Variables de entorno configuradas"

# ============================================
# DETENER PROCESOS ANTIGUOS
# ============================================
log_info "Deteniendo procesos gunicorn antiguos..."
pkill -f "gunicorn.*--bind.*${UPSTREAM_PORT}" || true
pkill -f "gunicorn.*--bind.*0.0.0.0:${UPSTREAM_PORT}" || true
sleep 2
log_success "Procesos antiguos detenidos"

# ============================================
# SERVICIO SYSTEMD
# ============================================
log_info "Configurando servicio systemd..."

# Verificar punto de entrada de la app (gunicorn usa callable sin paréntesis)
if [ -f "${APP_DIR}/app/__init__.py" ] && grep -q "def create_app" "${APP_DIR}/app/__init__.py"; then
    APP_ENTRY="app:create_app"
    log_info "Usando factory pattern: $APP_ENTRY"
else
    APP_ENTRY="app:app"
    log_info "Usando aplicación directa: $APP_ENTRY"
fi

cat > "$SYSTEMD_SERVICE" <<EOF
[Unit]
Description=${APP_NAME} Gunicorn Application Server
Documentation=https://docs.gunicorn.org/
After=network.target postgresql.service mysql.service
Wants=postgresql.service mysql.service

[Service]
Type=notify
User=${RUN_USER}
Group=${RUN_GROUP}
RuntimeDirectory=${SERVICE_NAME}
RuntimeDirectoryMode=0755

WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
Environment="PATH=${VENV_DIR}/bin"
Environment="PYTHONUNBUFFERED=1"

# Gunicorn
ExecStart=${VENV_DIR}/bin/gunicorn \\
    --pythonpath ${APP_DIR} \\
    --bind ${UPSTREAM} \\
    --workers 4 \\
    --worker-class eventlet \\
    --worker-connections 1000 \\
    --timeout 30 \\
    --keep-alive 5 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --access-logfile ${LOG_DIR}/access.log \\
    --error-logfile ${LOG_DIR}/error.log \\
    --log-level info \\
    --capture-output \\
    --enable-stdio-inheritance \\
    ${APP_ENTRY}

ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5
StartLimitInterval=60s
StartLimitBurst=3

# Security
NoNewPrivileges=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${APP_DIR} ${LOG_DIR}
ReadOnlyPaths=/usr /bin /sbin /lib /lib64
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
log_success "Servicio systemd configurado: ${SERVICE_NAME}.service"

# ============================================
# NGINX REVERSE PROXY
# ============================================
log_info "Configurando Nginx reverse proxy..."

# Backup configuración existente si existe
if [ -f "$NGINX_SITE" ]; then
    cp "$NGINX_SITE" "${NGINX_SITE}.backup.$(date +%Y%m%d_%H%M%S)"
fi

cat > "$NGINX_SITE" <<'NGINX_EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Logging
    access_log /var/log/nginx/stvaldivia_access.log;
    error_log /var/log/nginx/stvaldivia_error.log warn;

    # Tamaño máximo de upload
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # Buffer sizes
    client_body_buffer_size 128k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;

    # Security headers (básicos, la app Flask ya tiene algunos)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Location principal
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        
        # WebSocket support (si se usa SocketIO)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Healthcheck endpoint (si existe)
    location /health {
        proxy_pass http://127.0.0.1:5001/health;
        access_log off;
    }

    # Denegar acceso a archivos sensibles
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
NGINX_EOF

# Habilitar sitio
ln -sf "$NGINX_SITE" "$NGINX_ENABLED"

# Verificar configuración
if nginx -t >/dev/null 2>&1; then
    log_success "Configuración de Nginx válida"
    systemctl reload nginx
else
    log_error "Error en configuración de Nginx"
    nginx -t
    exit 1
fi

log_success "Nginx configurado y recargado"

# ============================================
# FIREWALL BÁSICO (UFW)
# ============================================
log_info "Configurando firewall..."
if command -v ufw >/dev/null 2>&1; then
    # Permitir SSH (crítico)
    ufw allow 22/tcp >/dev/null 2>&1 || true
    
    # Permitir HTTP/HTTPS
    ufw allow 80/tcp >/dev/null 2>&1 || true
    ufw allow 443/tcp >/dev/null 2>&1 || true
    
    # No activar automáticamente (puede bloquear conexiones)
    # ufw --force enable >/dev/null 2>&1 || true
    log_info "Reglas de firewall configuradas (no activado automáticamente)"
else
    log_warning "ufw no disponible, saltando configuración de firewall"
fi

# ============================================
# FAIL2BAN BÁSICO
# ============================================
log_info "Configurando fail2ban básico..."
if command -v fail2ban-client >/dev/null 2>&1; then
    systemctl enable fail2ban >/dev/null 2>&1 || true
    systemctl start fail2ban >/dev/null 2>&1 || true
    log_success "Fail2ban habilitado"
else
    log_warning "fail2ban no disponible"
fi

# ============================================
# INICIAR SERVICIO
# ============================================
log_info "Iniciando servicio ${SERVICE_NAME}..."
systemctl restart "${SERVICE_NAME}"

# Esperar un momento para que el servicio inicie
sleep 3

if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log_success "Servicio ${SERVICE_NAME} iniciado correctamente"
else
    log_error "El servicio ${SERVICE_NAME} no pudo iniciarse"
    systemctl status "${SERVICE_NAME}" --no-pager -l
    journalctl -u "${SERVICE_NAME}" --no-pager -n 50
    exit 1
fi

# ============================================
# HEALTHCHECKS
# ============================================
log_info "Realizando healthchecks..."

# Healthcheck 1: Puerto upstream
if ss -tuln | grep -q ":${UPSTREAM_PORT}"; then
    log_success "Puerto ${UPSTREAM_PORT} está escuchando"
else
    log_error "Puerto ${UPSTREAM_PORT} NO está escuchando"
fi

# Healthcheck 2: HTTP a través de Nginx
if curl -fsS -o /dev/null -w "%{http_code}" "http://127.0.0.1/" | grep -q "200\|302\|301"; then
    log_success "Nginx está proxyando correctamente"
else
    log_warning "Nginx healthcheck falló (puede ser normal si requiere autenticación)"
fi

# Healthcheck 3: Directo a gunicorn
if curl -fsS -o /dev/null -w "%{http_code}" "http://${UPSTREAM}/" | grep -q "200\|302\|301"; then
    log_success "Gunicorn está respondiendo correctamente"
else
    log_warning "Gunicorn healthcheck falló (puede ser normal si requiere autenticación)"
fi

# ============================================
# RESUMEN FINAL
# ============================================
echo ""
echo "=========================================="
echo -e "${GREEN}✅ CONFIGURACIÓN COMPLETADA${NC}"
echo "=========================================="
echo ""
echo "📋 Servicios:"
echo "   • systemd: ${SERVICE_NAME}.service"
echo "   • nginx: reverse proxy en puerto 80"
echo "   • gunicorn: ${UPSTREAM}"
echo ""
echo "📁 Archivos importantes:"
echo "   • Variables de entorno: ${ENV_FILE}"
echo "   • Logs de aplicación: ${LOG_DIR}/"
echo "   • Logs de systemd: journalctl -u ${SERVICE_NAME} -f"
echo "   • Logs de nginx: /var/log/nginx/stvaldivia_*.log"
echo ""
echo "🔧 Comandos útiles:"
echo "   • Estado del servicio: sudo systemctl status ${SERVICE_NAME}"
echo "   • Reiniciar servicio: sudo systemctl restart ${SERVICE_NAME}"
echo "   • Ver logs en tiempo real: sudo journalctl -u ${SERVICE_NAME} -f"
echo "   • Ver logs de nginx: sudo tail -f /var/log/nginx/stvaldivia_error.log"
echo ""
echo "🔒 Seguridad:"
echo "   • Edita ${ENV_FILE} y configura FLASK_SECRET_KEY"
echo "   • Configura DATABASE_URL en ${ENV_FILE}"
echo "   • Revisa configuración de firewall: sudo ufw status"
echo ""
echo "=========================================="

