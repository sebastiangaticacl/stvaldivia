# 🖥️ Comandos Útiles para el Servidor

## ✅ Conexión SSH

```bash
ssh stvaldivia
```

## 📍 Información del Servidor

- **Ubicación del proyecto:** `/var/www/stvaldivia`
- **Usuario que ejecuta gunicorn:** `deploy`
- **Logs:** `/var/www/stvaldivia/logs/error.log` y `access.log`
- **Servicio:** Gunicorn corriendo en `127.0.0.1:5001`

## 🔍 Comandos Útiles

### Ver estado del proyecto
```bash
ssh stvaldivia "cd /var/www/stvaldivia && ls -la"
```

### Ver logs de errores
```bash
ssh stvaldivia "tail -50 /var/www/stvaldivia/logs/error.log"
```

### Ver logs de acceso
```bash
ssh stvaldivia "tail -50 /var/www/stvaldivia/logs/access.log"
```

### Ver procesos de gunicorn
```bash
ssh stvaldivia "ps aux | grep gunicorn | grep -v grep"
```

### Reiniciar gunicorn (si hay systemd service)
```bash
ssh stvaldivia "sudo systemctl restart gunicorn"
```

### O matar y reiniciar manualmente
```bash
ssh stvaldivia "sudo pkill -f gunicorn && cd /var/www/stvaldivia && sudo -u deploy /var/www/stvaldivia/venv/bin/gunicorn --pythonpath /var/www/stvaldivia --bind 127.0.0.1:5001 --workers 4 --worker-class eventlet --timeout 30 --access-logfile /var/www/stvaldivia/logs/access.log --error-logfile /var/www/stvaldivia/logs/error.log app:create_app() &"
```

### Verificar que la app funciona
```bash
ssh stvaldivia "cd /var/www/stvaldivia && python3 -c 'from app import create_app; app = create_app(); print(\"✅ App OK\")'"
```

### Comparar BD (si el script existe)
```bash
ssh stvaldivia "cd /var/www/stvaldivia && python3 scripts/compare_db_simple.py"
```

### Verificar servicios
```bash
ssh stvaldivia "systemctl status nginx"
ssh stvaldivia "systemctl status gunicorn"
```

## 📝 Notas

- El proyecto **NO es un repositorio git** en el servidor (fue desplegado de otra forma)
- Para actualizar código, necesitas usar el script de deploy o copiar archivos manualmente
- Los logs están en `/var/www/stvaldivia/logs/`
- Gunicorn corre como usuario `deploy`

