#!/usr/bin/env bash

# ==========================================================
# Objetivo:
#   - Detectar si ALGÚN virtualhost de Nginx o Apache
#     tiene Basic Auth (auth_basic / AuthType Basic, etc.)
#   - Ver específicamente si algo afecta a stvaldivia.cl
# ==========================================================

set -u

echo "=== Procesos web activos (nginx/apache/httpd) ==="
ps aux | egrep 'nginx|apache|httpd' | grep -v egrep || echo "No se ven procesos nginx/apache/httpd"

echo ""
echo "=== Puertos escuchando (80/443/5000/5001) ==="
# ss puede no existir en todos los sistemas; si no, no rompe el script
if command -v ss >/dev/null 2>&1; then
  sudo ss -ltnp | egrep ':80|:443|:5000|:5001' || echo "No hay nada escuchando en 80/443/5000/5001 o ss no devolvió resultados"
else
  echo "Comando ss no disponible, saltando esta parte."
fi

echo ""
echo "==============================================="
echo "   REVISANDO CONFIGURACIÓN DE NGINX (si existe)"
echo "==============================================="
if command -v nginx >/dev/null 2>&1 && [ -d /etc/nginx ]; then
  echo "✓ nginx instalado y /etc/nginx existe"

  echo ""
  echo "---- nginx -T (config efectiva) | server_name / auth_basic ----"
  # Mostramos server_name, location y auth_basic con un poco de contexto
  sudo nginx -T 2>/dev/null | \
    grep -n -E 'server_name|location|auth_basic' -A2 -B2 || \
    echo "No se encontraron líneas con server_name/location/auth_basic en nginx -T"

  echo ""
  echo "---- grep -R auth_basic en /etc/nginx ----"
  sudo grep -R "auth_basic" -n /etc/nginx 2>/dev/null || echo "Sin auth_basic en archivos bajo /etc/nginx"

  echo ""
  echo "---- Buscar específicamente stvaldivia en nginx -T ----"
  sudo nginx -T 2>/dev/null | \
    grep -n -E 'stvaldivia\.cl' -A5 -B5 || \
    echo "No se encontraron bloques con stvaldivia.cl en nginx -T (o no aparecen claramente)."

else
  echo "✗ Nginx no está instalado o no existe /etc/nginx en este servidor."
fi

echo ""
echo "==============================================="
echo "   REVISANDO CONFIGURACIÓN DE APACHE (si existe)"
echo "==============================================="
if command -v apache2ctl >/dev/null 2>&1 || command -v apachectl >/dev/null 2>&1; then
  # apache2ctl en Debian/Ubuntu, apachectl en otras distros
  if command -v apache2ctl >/dev/null 2>&1; then
    APACHECTL="apache2ctl"
  else
    APACHECTL="apachectl"
  fi

  echo "✓ Apache detectado (comando: $APACHECTL)"

  echo ""
  echo "---- $APACHECTL -S (vhosts activos) ----"
  sudo "$APACHECTL" -S 2>/dev/null || echo "No se pudo ejecutar $APACHECTL -S"

  echo ""
  echo "---- grep -R Basic Auth en /etc/apache2 (si existe) ----"
  if [ -d /etc/apache2 ]; then
    sudo grep -R "AuthType Basic\|Require valid-user\|AuthUserFile\|auth_basic" -n /etc/apache2 2>/dev/null || \
      echo "Sin reglas de Basic Auth en /etc/apache2"
  else
    echo "No existe /etc/apache2 en este servidor"
  fi

  echo ""
  echo "---- Buscar específicamente stvaldivia en config Apache ----"
  if [ -d /etc/apache2 ]; then
    sudo grep -R "stvaldivia\.cl" -n /etc/apache2 2>/dev/null || \
      echo "No se encontraron referencias a stvaldivia.cl en /etc/apache2"
  fi

else
  echo "✗ No se detectó Apache (apache2ctl/apachectl) en este servidor."
fi

echo ""
echo "==============================================="
echo "   PRUEBA DIRECTA A /socket.io EN ESTE HOST"
echo "==============================================="
# Ojo: esto prueba contra localhost; ajusta HOST si quieres probar otro dominio
HOST="127.0.0.1"
PORT="5001"
URL="http://$HOST:$PORT/socket.io/?EIO=4&transport=polling"

echo "Probando: $URL"
if command -v curl >/dev/null 2>&1; then
  curl -i "$URL" | head -60 || echo "No responde en $URL"
else
  echo "curl no está instalado, no se puede probar la URL $URL"
fi

echo ""
echo "=== FIN DEL SCRIPT ==="
date
