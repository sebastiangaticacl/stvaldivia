#!/bin/bash
# Script para revisar todos los procesos del sistema de forma completa
# Uso: ./scripts/revisar_procesos_completos.sh

echo "🔍 REVISIÓN COMPLETA DE PROCESOS"
echo "=================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar si estamos en el servidor o localmente
if [ -d "/var/www/stvaldivia" ]; then
    PROJECT_DIR="/var/www/stvaldivia"
    IS_SERVER=true
else
    PROJECT_DIR="$(pwd)"
    IS_SERVER=false
fi

echo "📁 Directorio del proyecto: $PROJECT_DIR"
echo "🖥️  Ejecutando en: $(if [ "$IS_SERVER" = true ]; then echo "SERVIDOR"; else echo "LOCAL"; fi)"
echo ""

# 1. PROCESOS DEL SISTEMA
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}1. PROCESOS DE GUNICORN/FLASK${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if pgrep -f "gunicorn.*app:create_app" > /dev/null; then
    echo "✅ Gunicorn está corriendo:"
    echo ""
    ps aux | grep -E "gunicorn.*app:create_app" | grep -v grep | while read line; do
        PID=$(echo "$line" | awk '{print $2}')
        CPU=$(echo "$line" | awk '{print $3}')
        MEM=$(echo "$line" | awk '{print $4}')
        CMD=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}')
        echo "  PID: $PID | CPU: $CPU% | MEM: $MEM%"
        echo "  Comando: $CMD"
        echo ""
    done
    
    # Contar workers
    WORKER_COUNT=$(ps aux | grep -E "gunicorn.*app:create_app" | grep -v grep | wc -l)
    echo "  Total de procesos (master + workers): $WORKER_COUNT"
else
    echo -e "${RED}❌ Gunicorn NO está corriendo${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}2. PROCESOS DE NGINX${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if pgrep -f "nginx" > /dev/null; then
    echo "✅ Nginx está corriendo:"
    echo ""
    ps aux | grep -E "nginx" | grep -v grep | head -5
    echo ""
    echo "  Total de procesos Nginx: $(ps aux | grep -E "nginx" | grep -v grep | wc -l)"
else
    echo -e "${RED}❌ Nginx NO está corriendo${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}3. PROCESOS DE POSTGRESQL${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if pgrep -f "postgres" > /dev/null; then
    echo "✅ PostgreSQL está corriendo:"
    echo ""
    ps aux | grep -E "postgres" | grep -v grep | head -5
    echo ""
    echo "  Total de procesos PostgreSQL: $(ps aux | grep -E "postgres" | grep -v grep | wc -l)"
else
    echo -e "${YELLOW}⚠️  PostgreSQL NO está corriendo (puede ser normal si se accede remotamente)${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}4. SERVICIOS SYSTEMD${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if command -v systemctl > /dev/null 2>&1; then
    echo "Estado de servicios relevantes:"
    echo ""
    
    for service in "stvaldivia" "gunicorn" "nginx" "postgresql"; do
        if systemctl list-unit-files | grep -q "$service.service"; then
            STATUS=$(systemctl is-active "$service.service" 2>/dev/null || echo "inactive")
            ENABLED=$(systemctl is-enabled "$service.service" 2>/dev/null || echo "unknown")
            
            if [ "$STATUS" = "active" ]; then
                echo -e "  ✅ $service: ${GREEN}$STATUS${NC} (enabled: $ENABLED)"
            else
                echo -e "  ${RED}❌${NC} $service: $STATUS (enabled: $ENABLED)"
            fi
        fi
    done
else
    echo "⚠️  systemctl no disponible (probablemente ejecutando localmente)"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}5. PUERTOS EN USO${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if uname | grep -q "Darwin"; then
    # macOS
    if command -v lsof > /dev/null 2>&1; then
        echo "Puertos relevantes:"
        echo ""
        lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | grep -E ":(80|443|5001|5432|7777)" | awk '{printf "  %-8s %-20s %s\n", $2, $9, $1}' || echo "  No se encontraron puertos relevantes"
    else
        echo "⚠️  lsof no disponible"
    fi
else
    # Linux
    if command -v ss > /dev/null 2>&1; then
        echo "Puertos relevantes:"
        echo ""
        ss -tlnp 2>/dev/null | grep -E ":(80|443|5001|5432|7777)" | while read line; do
            echo "  $line"
        done
    elif command -v netstat > /dev/null 2>&1; then
        echo "Puertos relevantes:"
        echo ""
        netstat -tlnp 2>/dev/null | grep -E ":(80|443|5001|5432|7777)" | while read line; do
            echo "  $line"
        done
    else
        echo "⚠️  netstat/ss no disponible"
    fi
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}6. USO DE RECURSOS (TOP 10)${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Procesos usando más CPU:"
if uname | grep -q "Darwin"; then
    # macOS
    ps aux | sort -nrk 3,3 | head -10 | awk '{printf "  %-8s %6s%% %6s%% %s\n", $2, $3, $4, $11}'
else
    # Linux
    ps aux --sort=-%cpu | head -11 | tail -10 | awk '{printf "  %-8s %6s%% %6s%% %s\n", $2, $3, $4, $11}'
fi
echo ""

echo "Procesos usando más MEMORIA:"
if uname | grep -q "Darwin"; then
    # macOS
    ps aux | sort -nrk 4,4 | head -10 | awk '{printf "  %-8s %6s%% %6s%% %s\n", $2, $3, $4, $11}'
else
    # Linux
    ps aux --sort=-%mem | head -11 | tail -10 | awk '{printf "  %-8s %6s%% %6s%% %s\n", $2, $3, $4, $11}'
fi
echo ""

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}7. LOGS RECIENTES${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -d "$PROJECT_DIR/logs" ]; then
    echo "📋 Últimas 10 líneas del log de errores:"
    echo ""
    if [ -f "$PROJECT_DIR/logs/error.log" ]; then
        tail -10 "$PROJECT_DIR/logs/error.log" | sed 's/^/  /'
    else
        echo "  ⚠️  error.log no encontrado"
    fi
    
    echo ""
    echo "📋 Últimas 10 líneas del log de acceso:"
    echo ""
    if [ -f "$PROJECT_DIR/logs/access.log" ]; then
        tail -10 "$PROJECT_DIR/logs/access.log" | sed 's/^/  /'
    else
        echo "  ⚠️  access.log no encontrado"
    fi
else
    echo "⚠️  Directorio de logs no encontrado: $PROJECT_DIR/logs"
fi

if [ "$IS_SERVER" = true ] && command -v journalctl > /dev/null 2>&1; then
    echo ""
    echo "📋 Logs de systemd para stvaldivia (últimas 5 líneas):"
    echo ""
    sudo journalctl -u stvaldivia.service -n 5 --no-pager 2>/dev/null | sed 's/^/  /' || echo "  ⚠️  No se pudo acceder a logs de systemd"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}8. VERIFICACIÓN DE CONECTIVIDAD${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Verificando puertos locales:"
echo ""

# Verificar puertos
check_port() {
    local port=$1
    local name=$2
    
    if command -v nc > /dev/null 2>&1; then
        if nc -z localhost "$port" 2>/dev/null; then
            echo -e "  ✅ Puerto $port ($name): ${GREEN}ABIERTO${NC}"
        else
            echo -e "  ${RED}❌${NC} Puerto $port ($name): CERRADO"
        fi
    elif command -v lsof > /dev/null 2>&1; then
        if lsof -i ":$port" > /dev/null 2>&1; then
            echo -e "  ✅ Puerto $port ($name): ${GREEN}ABIERTO${NC}"
        else
            echo -e "  ${RED}❌${NC} Puerto $port ($name): CERRADO"
        fi
    else
        echo -e "  ⚠️  Puerto $port ($name): No se puede verificar (nc/lsof no disponible)"
    fi
}

check_port 5001 "Gunicorn"
check_port 80 "HTTP"
check_port 443 "HTTPS"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}9. INFORMACIÓN DEL SISTEMA${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "Uptime del sistema:"
uptime | sed 's/^/  /'
echo ""

echo "Uso de disco:"
df -h / | tail -1 | awk '{print "  Usado: " $3 " de " $2 " (" $5 " usado)"}'
echo ""

echo "Uso de memoria:"
if uname | grep -q "Darwin"; then
    # macOS - usar vm_stat
    if command -v vm_stat > /dev/null 2>&1; then
        TOTAL_MEM=$(sysctl -n hw.memsize 2>/dev/null)
        if [ -n "$TOTAL_MEM" ]; then
            TOTAL_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
            FREE_PAGES=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
            PAGE_SIZE=$(vm_stat | grep "page size" | awk '{print $8}')
            if [ -n "$FREE_PAGES" ] && [ -n "$PAGE_SIZE" ]; then
                FREE_MB=$((FREE_PAGES * PAGE_SIZE / 1024 / 1024))
                FREE_GB=$((FREE_MB / 1024))
                USED_GB=$((TOTAL_GB - FREE_GB))
                echo "  Total: ${TOTAL_GB}GB | Usado: ${USED_GB}GB | Libre: ${FREE_GB}GB"
            else
                echo "  Total: ${TOTAL_GB}GB (detalle no disponible)"
            fi
        else
            echo "  ⚠️  No se pudo obtener información de memoria"
        fi
    else
        echo "  ⚠️  vm_stat no disponible"
    fi
else
    # Linux
    free -h 2>/dev/null | grep Mem | awk '{print "  Total: " $2 " | Usado: " $3 " | Libre: " $4 " | Disponible: " $7}' || echo "  ⚠️  comando free no disponible"
fi
echo ""

echo "Carga del sistema:"
if uname | grep -q "Darwin"; then
    # macOS
    sysctl -n vm.loadavg 2>/dev/null | awk '{print "  1 min: " $1 " | 5 min: " $2 " | 15 min: " $3}' || uptime | awk -F'load averages:' '{print "  " $2}'
else
    # Linux
    cat /proc/loadavg 2>/dev/null | awk '{print "  1 min: " $1 " | 5 min: " $2 " | 15 min: " $3}' || echo "  ⚠️  /proc/loadavg no disponible"
fi
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ REVISIÓN COMPLETA FINALIZADA${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

