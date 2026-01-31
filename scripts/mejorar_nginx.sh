#!/usr/bin/env bash
#
# Mejoras profesionales para Nginx
# Agrega optimizaciones, rate limiting, y preparación para SSL
#
set -euo pipefail

APP_NAME="stvaldivia"
NGINX_SITE="/etc/nginx/sites-available/${APP_NAME}"
NGINX_MAIN="/etc/nginx/nginx.conf"
UPSTREAM="127.0.0.1:5001"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "$1"
}

log "${BLUE}========================================${NC}"
log "${BLUE}MEJORAS NGINX PROFESIONALES${NC}"
log "${BLUE}========================================${NC}\n"

# Backup configuración existente
if [ -f "$NGINX_SITE" ]; then
    cp "$NGINX_SITE" "${NGINX_SITE}.backup.$(date +%Y%m%d_%H%M%S)"
    log "${GREEN}✓${NC} Backup de configuración creado\n"
fi

# Mejorar configuración principal de Nginx
log "${BLUE}[1/3] Optimizando nginx.conf...${NC}"
if ! grep -q "worker_connections.*65535" "$NGINX_MAIN" 2>/dev/null; then
    # Crear backup
    cp "$NGINX_MAIN" "${NGINX_MAIN}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Agregar optimizaciones si no existen
    sed -i '/^worker_processes/a worker_rlimit_nofile 65535;' "$NGINX_MAIN" 2>/dev/null || true
    
    # Mejorar events block
    if grep -q "events {" "$NGINX_MAIN"; then
        sed -i '/events {/,/}/ {
            s/worker_connections [0-9]*;/worker_connections 65535;/
        }' "$NGINX_MAIN" 2>/dev/null || true
    fi
    
    log "${GREEN}✓${NC} nginx.conf optimizado"
else
    log "${YELLOW}⚠${NC} nginx.conf ya optimizado"
fi
echo ""

# Configurar rate limiting
log "${BLUE}[2/3] Configurando rate limiting...${NC}"
RATE_LIMIT_FILE="/etc/nginx/conf.d/rate_limit.conf"
cat > "$RATE_LIMIT_FILE" <<'EOF'
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;
EOF
log "${GREEN}✓${NC} Rate limiting configurado\n"

# Mejorar configuración del sitio
log "${BLUE}[3/3] Mejorando configuración del sitio...${NC}"
cat > "$NGINX_SITE" <<NGINX_EOF
# Upstream para balanceo (preparado para múltiples workers)
upstream ${APP_NAME}_backend {
    server ${UPSTREAM} max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Rate limiting para login
map \$request_uri \$is_login {
    ~^/.*login.* 1;
    default 0;
}

server {
    listen 80;
    listen [::]:80;
    server_name _;

    # Logging
    access_log /var/log/nginx/${APP_NAME}_access.log combined buffer=32k flush=5s;
    error_log /var/log/nginx/${APP_NAME}_error.log warn;

    # Tamaño máximo
    client_max_body_size 50M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    send_timeout 60s;

    # Buffer sizes optimizados
    client_body_buffer_size 128k;
    client_header_buffer_size 2k;
    large_client_header_buffers 4 16k;
    output_buffers 2 32k;
    postpone_output 1460;

    # Gzip compression mejorado
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_disable "msie6";
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/rss+xml
        font/truetype
        font/opentype
        application/vnd.ms-fontobject
        image/svg+xml;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate limiting por ubicación
    location / {
        # Conexiones por IP
        limit_conn conn_limit_per_ip 20;
        
        # Rate limiting general
        limit_req zone=general burst=20 nodelay;
        
        # Rate limiting estricto para login
        limit_req zone=login burst=3 nodelay;
        
        proxy_pass http://${APP_NAME}_backend;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_set_header Connection "";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering optimizado
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
        proxy_temp_file_write_size 16k;
        
        # Cache para assets estáticos (si los hay)
        proxy_cache_bypass \$http_upgrade;
        
        # WebSocket support
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API endpoints con rate limiting específico
    location /api/ {
        limit_req zone=api burst=50 nodelay;
        limit_conn conn_limit_per_ip 30;
        
        proxy_pass http://${APP_NAME}_backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
    }

    # Healthcheck sin rate limiting
    location /health {
        access_log off;
        proxy_pass http://${APP_NAME}_backend/health;
        proxy_set_header Host \$host;
    }

    # Denegar archivos sensibles
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ \.(env|log|sql|bak|backup)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
NGINX_EOF

# Verificar configuración
if nginx -t >/dev/null 2>&1; then
    log "${GREEN}✓${NC} Configuración válida"
    systemctl reload nginx
    log "${GREEN}✓${NC} Nginx recargado\n"
else
    log "${RED}✗${NC} Error en configuración"
    nginx -t
    exit 1
fi

log "${BLUE}========================================${NC}"
log "${GREEN}✓ NGINX MEJORADO${NC}"
log "${BLUE}========================================${NC}\n"
log "Mejoras aplicadas:"
log "  • Rate limiting (general, API, login)"
log "  • Connection limiting"
log "  • Gzip optimizado"
log "  • Buffers optimizados"
log "  • Security headers"
log "  • Upstream con keepalive"
log "  • Logging optimizado"
echo ""

