# Runbook de Operaciones - stvaldivia

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Comandos Esenciales](#comandos-esenciales)
4. [Procedimientos de Mantenimiento](#procedimientos-de-mantenimiento)
5. [Resolución de Problemas](#resolución-de-problemas)
6. [Monitoreo](#monitoreo)
7. [Backups](#backups)
8. [Seguridad](#seguridad)

---

## Visión General

**Aplicación:** stvaldivia (BIMBA POS System)  
**Entorno:** Producción - Google Cloud VM  
**Ubicación VM:** `/var/www/stvaldivia`  
**Servicio Systemd:** `stvaldivia.service`  
**Webserver:** Nginx (puerto 80) → Gunicorn (127.0.0.1:5001)

---

## Arquitectura

```
Internet
   ↓
Nginx (80/443)
   ↓
Gunicorn (127.0.0.1:5001)
   ↓
Flask Application
   ↓
PostgreSQL / MySQL
```

**Componentes:**
- **Systemd Service:** `stvaldivia.service` - Gestiona proceso Gunicorn
- **Nginx:** Reverse proxy y servidor web
- **Gunicorn:** WSGI server con 4 workers (eventlet)
- **Bases de datos:** PostgreSQL (5432), MySQL (3306)
- **Logs:** `/var/www/stvaldivia/logs/`

---

## Comandos Esenciales

### Estado del Servicio

```bash
# Estado general
sudo systemctl status stvaldivia

# Ver si está activo
sudo systemctl is-active stvaldivia

# Ver si está habilitado
sudo systemctl is-enabled stvaldivia
```

### Gestión del Servicio

```bash
# Iniciar
sudo systemctl start stvaldivia

# Detener
sudo systemctl stop stvaldivia

# Reiniciar
sudo systemctl restart stvaldivia

# Recargar (sin downtime si es posible)
sudo systemctl reload stvaldivia

# Habilitar inicio automático
sudo systemctl enable stvaldivia

# Deshabilitar inicio automático
sudo systemctl disable stvaldivia
```

### Logs

```bash
# Logs en tiempo real (systemd)
sudo journalctl -u stvaldivia -f

# Últimas 100 líneas
sudo journalctl -u stvaldivia -n 100

# Logs desde hoy
sudo journalctl -u stvaldivia --since today

# Logs de la aplicación
sudo tail -f /var/www/stvaldivia/logs/error.log
sudo tail -f /var/www/stvaldivia/logs/access.log

# Logs de Nginx
sudo tail -f /var/log/nginx/stvaldivia_error.log
sudo tail -f /var/log/nginx/stvaldivia_access.log
```

### Nginx

```bash
# Estado
sudo systemctl status nginx

# Reiniciar
sudo systemctl restart nginx

# Recargar configuración
sudo nginx -t && sudo systemctl reload nginx

# Verificar configuración
sudo nginx -t
```

---

## Procedimientos de Mantenimiento

### Deploy

**Método recomendado (mejorado):**
```bash
./deploy_vm_mejorado.sh
```

**Método rápido:**
```bash
./deploy_vm.sh
```

**Pasos manuales:**
1. `git push` (desde local)
2. SSH a la VM
3. `cd /var/www/stvaldivia`
4. `sudo -u deploy git pull`
5. `sudo -u deploy venv/bin/pip install -r requirements.txt`
6. `sudo systemctl restart stvaldivia`

### Backup Manual

```bash
# Ejecutar script de backup
sudo /var/www/stvaldivia/scripts/backup_sistema.sh

# Backup manual rápido
BACKUP_DIR="/var/backups/stvaldivia/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/code.tar.gz" -C /var/www stvaldivia --exclude='venv' --exclude='logs'
```

### Monitoreo

```bash
# Healthcheck completo
sudo /var/www/stvaldivia/scripts/monitor_health.sh

# Ver recursos del sistema
htop
df -h
free -h
```

### Actualizar Dependencias

```bash
cd /var/www/stvaldivia
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart stvaldivia
```

---

## Resolución de Problemas

### Servicio No Inicia

1. **Ver logs de error:**
   ```bash
   sudo journalctl -u stvaldivia -n 50 --no-pager
   ```

2. **Verificar configuración:**
   ```bash
   sudo systemctl status stvaldivia -l
   ```

3. **Verificar variables de entorno:**
   ```bash
   sudo cat /etc/stvaldivia/stvaldivia.env
   ```

4. **Probar manualmente:**
   ```bash
   cd /var/www/stvaldivia
   sudo -u deploy venv/bin/gunicorn --pythonpath /var/www/stvaldivia --bind 127.0.0.1:5001 app:create_app
   ```

### Puerto 5001 en Uso

```bash
# Encontrar proceso
sudo lsof -i :5001

# Matar proceso
sudo pkill -f "gunicorn.*5001"

# O más específico
sudo pkill -f "gunicorn.*app:create_app"
```

### Errores 500 en la Aplicación

1. **Ver logs de error:**
   ```bash
   sudo tail -100 /var/www/stvaldivia/logs/error.log
   ```

2. **Verificar base de datos:**
   ```bash
   sudo systemctl status postgresql
   sudo systemctl status mysql
   ```

3. **Verificar permisos:**
   ```bash
   ls -la /var/www/stvaldivia/logs
   ```

### Nginx No Responde

1. **Verificar estado:**
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```

2. **Ver logs:**
   ```bash
   sudo tail -50 /var/log/nginx/error.log
   ```

3. **Verificar puerto:**
   ```bash
   sudo ss -tulpn | grep :80
   ```

### Espacio en Disco Bajo

```bash
# Ver uso
df -h

# Limpiar logs antiguos
sudo find /var/www/stvaldivia/logs -name "*.log.*" -mtime +7 -delete

# Limpiar backups antiguos
sudo find /var/backups/stvaldivia -type d -mtime +30 -exec rm -rf {} +

# Limpiar paquetes apt
sudo apt-get clean
sudo apt-get autoremove
```

---

## Monitoreo

### Healthcheck Automatizado

```bash
# Ejecutar manualmente
sudo /var/www/stvaldivia/scripts/monitor_health.sh

# Agregar a crontab (cada hora)
0 * * * * /var/www/stvaldivia/scripts/monitor_health.sh >> /var/log/stvaldivia_health.log 2>&1
```

### Métricas Clave

- **CPU:** < 80%
- **Memoria:** < 85%
- **Disco:** < 85%
- **HTTP Status:** 2xx/3xx
- **Servicio:** Activo

### Endpoints de Monitoreo

- `/api/system/health` - Health check completo
- `/api/health` - Health check básico
- `/health` - Health check simple (si existe)

---

## Backups

### Automáticos

Los backups se pueden configurar en crontab:
```bash
# Backup diario a las 2 AM
0 2 * * * /var/www/stvaldivia/scripts/backup_sistema.sh
```

### Ubicación

Backups almacenados en: `/var/backups/stvaldivia/`

**Estructura:**
```
/var/backups/stvaldivia/
  └── YYYYMMDD_HHMMSS/
      ├── code.tar.gz
      ├── postgres_*.sql.gz
      ├── mysql_*.sql.gz
      ├── config.tar.gz
      └── backup_info.txt
```

### Restaurar Backup

```bash
# 1. Detener servicio
sudo systemctl stop stvaldivia

# 2. Restaurar código
cd /var/www
sudo tar -xzf /var/backups/stvaldivia/YYYYMMDD_HHMMSS/code.tar.gz

# 3. Restaurar base de datos (si es necesario)
sudo -u postgres psql dbname < backup.sql

# 4. Reiniciar servicio
sudo systemctl start stvaldivia
```

---

## Seguridad

### Variables de Entorno

Ubicación: `/etc/stvaldivia/stvaldivia.env`  
Permisos: `600` (solo root)

**Variables críticas:**
- `FLASK_SECRET_KEY` - Obligatorio
- `DATABASE_URL` - Obligatorio
- `OPENAI_API_KEY` - Opcional

### Firewall

```bash
# Ver estado
sudo ufw status

# Activar (cuidado!)
sudo ufw enable

# Ver reglas
sudo ufw status verbose
```

### Fail2ban

```bash
# Estado
sudo systemctl status fail2ban

# Ver baneos
sudo fail2ban-client status sshd
```

### Certificados SSL (Futuro)

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d stvaldivia.cl

# Renovación automática
sudo certbot renew --dry-run
```

---

## Contacto y Soporte

**Archivos importantes:**
- Configuración: `/etc/stvaldivia/stvaldivia.env`
- Servicio: `/etc/systemd/system/stvaldivia.service`
- Nginx: `/etc/nginx/sites-available/stvaldivia`
- Logs: `/var/www/stvaldivia/logs/`
- Scripts: `/var/www/stvaldivia/scripts/`

**Última actualización:** 2026-01-03

