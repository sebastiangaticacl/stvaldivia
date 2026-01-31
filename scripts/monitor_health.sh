#!/usr/bin/env bash
#
# Script de monitoreo y healthcheck profesional
# Verifica estado del sistema, servicios, recursos y aplicación
#
set -euo pipefail

# Configuración
APP_NAME="stvaldivia"
APP_DIR="/var/www/stvaldivia"
SERVICE_NAME="${APP_NAME}"
UPSTREAM="127.0.0.1:5001"
LOG_FILE="/var/log/${APP_NAME}_health.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=85
ALERT_THRESHOLD_DISK=85

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Resultados
EXIT_CODE=0
ALERTS=()

log() {
    echo -e "$1" | tee -a "$LOG_FILE" 2>/dev/null || echo -e "$1"
}

check_service() {
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "${GREEN}✓${NC} Servicio ${SERVICE_NAME} está activo"
        return 0
    else
        log "${RED}✗${NC} Servicio ${SERVICE_NAME} NO está activo"
        ALERTS+=("Servicio ${SERVICE_NAME} no está corriendo")
        EXIT_CODE=1
        return 1
    fi
}

check_port() {
    local port=$1
    local name=$2
    if ss -tuln | grep -q ":${port}"; then
        log "${GREEN}✓${NC} Puerto ${port} (${name}) está escuchando"
        return 0
    else
        log "${RED}✗${NC} Puerto ${port} (${name}) NO está escuchando"
        ALERTS+=("Puerto ${port} no está escuchando")
        EXIT_CODE=1
        return 1
    fi
}

check_http() {
    local url=$1
    local name=$2
    local expected_code=${3:-200}
    
    local code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    
    if [[ "$code" == "$expected_code" ]] || [[ "$expected_code" == "2xx" && "$code" =~ ^2[0-9]{2}$ ]]; then
        log "${GREEN}✓${NC} HTTP ${name}: ${code}"
        return 0
    elif [[ "$code" == "000" ]]; then
        log "${YELLOW}⚠${NC} HTTP ${name}: No responde (timeout/conexión rechazada)"
        ALERTS+=("${name} no responde HTTP")
        return 1
    else
        log "${YELLOW}⚠${NC} HTTP ${name}: ${code} (esperado: ${expected_code})"
        return 1
    fi
}

check_resources() {
    # CPU
    local cpu=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    cpu=${cpu%.*}
    if (( $(echo "$cpu > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        log "${YELLOW}⚠${NC} CPU: ${cpu}% (umbral: ${ALERT_THRESHOLD_CPU}%)"
        ALERTS+=("CPU alto: ${cpu}%")
    else
        log "${GREEN}✓${NC} CPU: ${cpu}%"
    fi
    
    # Memoria
    local mem=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
    if (( mem > ALERT_THRESHOLD_MEM )); then
        log "${YELLOW}⚠${NC} Memoria: ${mem}% (umbral: ${ALERT_THRESHOLD_MEM}%)"
        ALERTS+=("Memoria alta: ${mem}%")
    else
        log "${GREEN}✓${NC} Memoria: ${mem}%"
    fi
    
    # Disco
    local disk=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if (( disk > ALERT_THRESHOLD_DISK )); then
        log "${YELLOW}⚠${NC} Disco: ${disk}% (umbral: ${ALERT_THRESHOLD_DISK}%)"
        ALERTS+=("Espacio en disco bajo: ${disk}%")
    else
        log "${GREEN}✓${NC} Disco: ${disk}%"
    fi
}

check_logs() {
    local error_log="${APP_DIR}/logs/error.log"
    if [ -f "$error_log" ]; then
        local recent_errors=$(tail -n 100 "$error_log" | grep -i "error\|exception\|critical" | wc -l)
        if (( recent_errors > 50 )); then
            log "${YELLOW}⚠${NC} Logs: ${recent_errors} errores recientes en últimas 100 líneas"
            ALERTS+=("Muchos errores en logs: ${recent_errors}")
        else
            log "${GREEN}✓${NC} Logs: ${recent_errors} errores recientes (OK)"
        fi
    fi
}

check_database() {
    # Verificar PostgreSQL
    if systemctl is-active --quiet postgresql; then
        log "${GREEN}✓${NC} PostgreSQL está activo"
    else
        log "${YELLOW}⚠${NC} PostgreSQL no está activo"
    fi
    
    # Verificar MySQL
    if systemctl is-active --quiet mysql; then
        log "${GREEN}✓${NC} MySQL está activo"
    else
        log "${YELLOW}⚠${NC} MySQL no está activo"
    fi
}

# Main
main() {
    log "\n${BLUE}========================================${NC}"
    log "${BLUE}HEALTHCHECK - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    log "${BLUE}========================================${NC}\n"
    
    log "${BLUE}[Servicios]${NC}"
    check_service
    check_port 80 "Nginx HTTP"
    check_port 5001 "Gunicorn"
    
    log "\n${BLUE}[HTTP Endpoints]${NC}"
    check_http "http://${UPSTREAM}/" "Gunicorn directo" "2xx"
    check_http "http://127.0.0.1/" "Nginx proxy" "2xx"
    check_http "http://${UPSTREAM}/api/system/health" "Health API" "2xx" 2>/dev/null || true
    
    log "\n${BLUE}[Recursos del Sistema]${NC}"
    check_resources
    
    log "\n${BLUE}[Bases de Datos]${NC}"
    check_database
    
    log "\n${BLUE}[Logs]${NC}"
    check_logs
    
    # Resumen
    log "\n${BLUE}========================================${NC}"
    if [ ${#ALERTS[@]} -eq 0 ]; then
        log "${GREEN}✓ TODO OK${NC}"
        log "${BLUE}========================================${NC}\n"
    else
        log "${YELLOW}⚠ ALERTAS DETECTADAS:${NC}"
        for alert in "${ALERTS[@]}"; do
            log "${YELLOW}  - ${alert}${NC}"
        done
        log "${BLUE}========================================${NC}\n"
        EXIT_CODE=1
    fi
    
    exit $EXIT_CODE
}

main "$@"

