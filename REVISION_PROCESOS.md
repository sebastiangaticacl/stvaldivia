# 🔍 Guía para Revisar Procesos Completos

Esta guía te ayuda a revisar todos los procesos del sistema de forma exhaustiva.

## 🚀 Uso Rápido

### Script Automatizado
```bash
# Ejecutar el script completo
./scripts/revisar_procesos_completos.sh

# O desde el servidor
ssh stvaldivia "cd /var/www/stvaldivia && ./scripts/revisar_procesos_completos.sh"
```

## 📋 Comandos Manuales

### 1. Procesos de Gunicorn/Flask

```bash
# Ver todos los procesos de Gunicorn
ps aux | grep gunicorn | grep -v grep

# Contar workers
ps aux | grep gunicorn | grep -v grep | wc -l

# Ver PID del proceso maestro
pgrep -f "gunicorn.*app:create_app"

# Ver detalles de un proceso específico
ps -p $(pgrep -f "gunicorn.*app:create_app" | head -1) -f
```

### 2. Servicios Systemd

```bash
# Ver estado de servicios
sudo systemctl status stvaldivia.service
sudo systemctl status nginx.service
sudo systemctl status gunicorn.service

# Ver todos los servicios relacionados
systemctl list-units --type=service | grep -E "(stvaldivia|gunicorn|nginx)"

# Ver logs de un servicio
sudo journalctl -u stvaldivia.service -n 50 --no-pager
sudo journalctl -u stvaldivia.service -f  # Seguir logs en tiempo real
```

### 3. Puertos y Conectividad

```bash
# Ver puertos en uso
sudo netstat -tlnp | grep -E ":(80|443|5001|5432)"
# O con ss (más moderno)
sudo ss -tlnp | grep -E ":(80|443|5001|5432)"

# Verificar si un puerto está abierto
nc -z localhost 5001 && echo "Puerto 5001 abierto" || echo "Puerto 5001 cerrado"
curl -I http://localhost:5001
```

### 4. Uso de Recursos

```bash
# Top 10 procesos por CPU
ps aux --sort=-%cpu | head -11

# Top 10 procesos por memoria
ps aux --sort=-%mem | head -11

# Ver uso de memoria del sistema
free -h

# Ver uso de disco
df -h

# Ver carga del sistema
uptime
cat /proc/loadavg
```

### 5. Logs

```bash
# Logs de errores de la aplicación
tail -50 /var/www/stvaldivia/logs/error.log
tail -f /var/www/stvaldivia/logs/error.log  # Seguir en tiempo real

# Logs de acceso
tail -50 /var/www/stvaldivia/logs/access.log

# Logs de systemd
sudo journalctl -u stvaldivia.service -n 100 --no-pager

# Buscar errores en logs
grep -i error /var/www/stvaldivia/logs/error.log | tail -20
grep -i "exception\|traceback" /var/www/stvaldivia/logs/error.log | tail -20
```

### 6. Procesos de Base de Datos

```bash
# Ver procesos de PostgreSQL
ps aux | grep postgres

# Conectarse a PostgreSQL
sudo -u postgres psql -d bimba

# Ver conexiones activas
sudo -u postgres psql -d bimba -c "SELECT count(*) FROM pg_stat_activity;"
sudo -u postgres psql -d bimba -c "SELECT pid, usename, application_name, state, query_start, state_change FROM pg_stat_activity WHERE datname = 'bimba';"
```

### 7. Procesos de Nginx

```bash
# Ver procesos de Nginx
ps aux | grep nginx

# Verificar configuración
sudo nginx -t

# Ver estado
sudo systemctl status nginx

# Recargar configuración
sudo nginx -s reload
```

## 🔍 Búsqueda de Procesos Específicos

```bash
# Buscar proceso por nombre
ps aux | grep "nombre_proceso"

# Buscar proceso por puerto
sudo lsof -i :5001
sudo netstat -tlnp | grep 5001

# Buscar proceso por PID
ps -p PID -f

# Ver árbol de procesos
pstree -p $(pgrep -f "gunicorn.*app:create_app" | head -1)
```

## 🐛 Debugging de Procesos

### Si Gunicorn no responde

```bash
# 1. Verificar si está corriendo
ps aux | grep gunicorn

# 2. Ver logs recientes
tail -100 /var/www/stvaldivia/logs/error.log

# 3. Intentar reiniciar
sudo systemctl restart stvaldivia.service
# O manualmente:
sudo pkill -f "gunicorn.*app:create_app"
# Luego iniciar de nuevo
```

### Si hay procesos zombie

```bash
# Ver procesos zombie
ps aux | grep "<defunct>"

# Ver hijos huérfanos
ps -eo pid,ppid,stat,comm | grep " Z "

# Limpiar procesos zombie (matar el padre)
kill -CHLD PPID
```

## 📊 Monitoreo Continuo

### Usar `htop` o `top`

```bash
# Instalar htop si no está
sudo apt install htop

# Ejecutar
htop

# Filtrar por proceso
# Presiona F4 y escribe "gunicorn"
```

### Usar `watch` para monitoreo periódico

```bash
# Ver procesos cada 2 segundos
watch -n 2 'ps aux | grep gunicorn | grep -v grep'

# Ver uso de recursos
watch -n 2 'free -h && echo "" && df -h /'
```

## 🔐 Desde SSH (Producción)

```bash
# Conectar al servidor
ssh -i ~/.ssh/id_ed25519_gcp stvaldiviazal@34.176.144.166

# O usando alias
ssh stvaldivia

# Ejecutar revisión completa
cd /var/www/stvaldivia && ./scripts/revisar_procesos_completos.sh
```

## 📝 Notas Importantes

1. **Procesos de Gunicorn**: Normalmente hay 1 proceso maestro + N workers (configurado con `--workers`)
2. **Puerto 5001**: Gunicorn escucha en `127.0.0.1:5001` (solo local, Nginx hace proxy)
3. **Puertos 80/443**: Nginx escucha en estos puertos y hace proxy a Gunicorn
4. **Logs**: Siempre revisa los logs si hay problemas
5. **systemd**: Si hay servicio systemd, úsalo para gestionar procesos (más seguro que kill manual)

## 🆘 Comandos de Emergencia

```bash
# Matar todos los procesos de Gunicorn
sudo pkill -9 -f "gunicorn.*app:create_app"

# Reiniciar todos los servicios
sudo systemctl restart stvaldivia.service nginx.service

# Ver qué está bloqueando un puerto
sudo lsof -i :5001

# Ver conexiones activas
netstat -an | grep ESTABLISHED | wc -l
```









