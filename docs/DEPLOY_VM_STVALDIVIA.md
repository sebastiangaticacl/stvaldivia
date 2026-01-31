# 🚀 RUNBOOK: Despliegue en VM stvaldivia.cl

**Fecha:** 2025-01-15  
**Objetivo:** Desplegar sistema de cajas MVP1 + Payment Stack (GETNET + KLAP) de forma segura

---

## ⚠️ PRE-REQUISITOS

- Acceso SSH a VM stvaldivia.cl
- Acceso a base de datos PostgreSQL
- Permisos para hacer backup y ejecutar migraciones
- Conocimiento de servicios (systemd/gunicorn/nginx)

---

## 📋 CHECKLIST PRE-DEPLOY

- [ ] Código en branch main/stable
- [ ] Migración SQL revisada y probada localmente
- [ ] Backup de BD programado
- [ ] Ventana de mantenimiento coordinada (si aplica)
- [ ] Rollback plan preparado

---

## 🔄 PASO 1: BACKUP DE BASE DE DATOS

```bash
# SSH a la VM
ssh usuario@stvaldivia.cl

# Crear backup completo
pg_dump -U postgres -d bimba_db -F c -f backup_antes_mvp1_$(date +%Y%m%d_%H%M%S).dump

# Verificar que el backup se creó
ls -lh backup_antes_mvp1_*.dump

# (Opcional) Backup en formato SQL legible
pg_dump -U postgres -d bimba_db > backup_antes_mvp1_$(date +%Y%m%d_%H%M%S).sql
```

**Verificación:**
```bash
# Verificar tamaño del backup (debe ser > 0)
du -h backup_antes_mvp1_*.dump

# (Opcional) Verificar contenido
pg_restore -l backup_antes_mvp1_*.dump | head -20
```

---

## 🔄 PASO 2: PULL DEL CÓDIGO

```bash
# Ir al directorio del proyecto
cd /ruta/al/proyecto  # Ajustar según estructura real

# Verificar branch actual
git branch

# Pull del código
git pull origin main

# Verificar cambios
git log --oneline -5
```

**Verificación:**
- [ ] Código actualizado
- [ ] Migración SQL presente: `migrations/2025_01_15_bimba_cajas_mvp1_paymentstack.sql`

---

## 🔄 PASO 3: EJECUTAR MIGRACIÓN SQL

```bash
# Verificar que la migración existe
cat migrations/2025_01_15_bimba_cajas_mvp1_paymentstack.sql | head -20

# Ejecutar migración (idempotente, seguro)
psql -U postgres -d bimba_db -f migrations/2025_01_15_bimba_cajas_mvp1_paymentstack.sql

# Verificar que no hubo errores
echo $?  # Debe ser 0
```

**Verificación:**
```sql
-- Conectar a PostgreSQL
psql -U postgres -d bimba_db

-- Verificar columnas en pos_registers
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'pos_registers'
AND column_name IN (
    'register_type', 'payment_provider_primary', 'payment_provider_backup',
    'operational_status', 'fallback_policy'
)
ORDER BY column_name;

-- Verificar columnas en register_sessions
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'register_sessions'
AND column_name IN (
    'cash_count', 'payment_totals', 'ticket_count', 'cash_difference',
    'payment_provider_used_primary_count', 'payment_provider_used_backup_count'
)
ORDER BY column_name;

-- Salir
\q
```

**Checklist:**
- [ ] Migración ejecutada sin errores
- [ ] Columnas nuevas presentes
- [ ] Defaults aplicados correctamente

---

## 🔄 PASO 4: REINICIAR SERVICIOS

### Opción A: Systemd (Gunicorn/Flask)

```bash
# Verificar servicios
sudo systemctl status gunicorn
# o
sudo systemctl status flask-app

# Reiniciar servicio
sudo systemctl restart gunicorn
# o
sudo systemctl restart flask-app

# Verificar que arrancó correctamente
sudo systemctl status gunicorn
# o
sudo systemctl status flask-app

# Ver logs
sudo journalctl -u gunicorn -n 50 --no-pager
# o
sudo journalctl -u flask-app -n 50 --no-pager
```

### Opción B: Nginx + Gunicorn manual

```bash
# Reiniciar Gunicorn
sudo systemctl restart gunicorn

# Recargar Nginx (sin downtime)
sudo nginx -t  # Verificar configuración
sudo nginx -s reload
```

### Opción C: Docker/Compose

```bash
# Reconstruir y reiniciar
docker-compose down
docker-compose up -d --build

# Ver logs
docker-compose logs -f --tail=50
```

**Checklist:**
- [ ] Servicio reiniciado
- [ ] Sin errores en logs
- [ ] Aplicación responde

---

## 🔄 PASO 5: CHECKLIST POST-DEPLOY

### 5.1 Verificar Admin - Cajas

```bash
# URLs a probar (ajustar dominio según entorno)
```

1. **Listar Cajas:**
   - URL: `https://stvaldivia.cl/admin/cajas/`
   - Verificar: Lista carga sin errores
   - Verificar: Columnas nuevas visibles (si aplica en tabla)

2. **Crear Caja:**
   - URL: `https://stvaldivia.cl/admin/cajas/crear`
   - Verificar: Formulario carga
   - Verificar: Sección "💳 Pagos (Low Friction)" visible
   - Crear caja de prueba:
     - Nombre: "TEST MVP1"
     - Tipo: HUMANA
     - Provider Principal: GETNET
     - Provider Backup: KLAP
     - Guardar
   - Verificar: Caja creada sin errores

3. **Editar Caja:**
   - URL: `https://stvaldivia.cl/admin/cajas/<id>/editar`
   - Verificar: Formulario carga con datos
   - Verificar: Campos de payment providers se muestran
   - Modificar y guardar
   - Verificar: Cambios guardados

4. **Reportes:**
   - URL: `https://stvaldivia.cl/admin/cajas/reportes`
   - Verificar: Página carga
   - Verificar: Tabla muestra cajas y sesiones

### 5.2 Verificar POS - Sesiones

1. **Abrir Sesión:**
   - URL: `https://stvaldivia.cl/caja/session/open`
   - Verificar: Formulario carga
   - Seleccionar caja y abrir sesión
   - Verificar: Sesión creada en BD

2. **Cerrar Sesión:**
   - URL: `https://stvaldivia.cl/caja/session/close`
   - Verificar: Formulario carga con resumen
   - Ingresar conteo de efectivo
   - Cerrar sesión
   - Verificar: Sesión cerrada, totales calculados

### 5.3 Verificar Logs

```bash
# Ver logs de aplicación
sudo journalctl -u gunicorn -n 100 --no-pager | grep -i error

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Ver logs de PostgreSQL (si aplica)
sudo tail -f /var/log/postgresql/postgresql-*.log | grep -i error
```

**Checklist:**
- [ ] Sin errores 500 en logs
- [ ] Sin errores de migración
- [ ] Sin errores de importación de modelos

---

## 🔄 PASO 6: VERIFICACIÓN FUNCIONAL

### 6.1 Crear Caja de Prueba

1. Ir a `/admin/cajas/crear`
2. Crear caja:
   - Nombre: "TEST GETNET+KLAP"
   - Código: "TEST-01"
   - Tipo: HUMANA
   - Provider Principal: GETNET
   - Provider Backup: KLAP
   - Fallback habilitado: ✅
   - Tiempo máximo: 60s
   - Celulares backup: 2
3. Guardar y verificar

### 6.2 Probar Apertura/Cierre

1. Abrir jornada (si no está abierta)
2. Ir a `/caja/session/open`
3. Seleccionar caja TEST-01
4. Fondo inicial: 50000
5. Abrir sesión
6. Verificar en BD:
   ```sql
   SELECT id, register_id, status, initial_cash, opened_at
   FROM register_sessions
   ORDER BY opened_at DESC
   LIMIT 1;
   ```
7. Ir a `/caja/session/close`
8. Ingresar conteo de efectivo
9. Cerrar sesión
10. Verificar en BD:
    ```sql
    SELECT id, status, cash_count, payment_totals, ticket_count, cash_difference
    FROM register_sessions
    ORDER BY closed_at DESC
    LIMIT 1;
    ```

### 6.3 Verificar Reportes

1. Ir a `/admin/cajas/reportes`
2. Verificar que muestra:
   - Cajas con providers
   - Última sesión
   - Totales por método de pago
   - Ticket count
   - Diferencias

---

## 🔄 PASO 7: ROLLBACK (SI ES NECESARIO)

### Si algo falla:

```bash
# 1. Restaurar backup de BD
pg_restore -U postgres -d bimba_db -c backup_antes_mvp1_*.dump

# 2. Revertir código (si es necesario)
cd /ruta/al/proyecto
git checkout <commit_anterior>
git pull

# 3. Reiniciar servicios
sudo systemctl restart gunicorn
```

---

## 📊 VERIFICACIÓN FINAL

### Checklist Completo

- [ ] Backup de BD creado
- [ ] Migración ejecutada sin errores
- [ ] Servicios reiniciados
- [ ] `/admin/cajas/` carga correctamente
- [ ] `/admin/cajas/crear` funciona
- [ ] `/admin/cajas/<id>/editar` funciona
- [ ] `/admin/cajas/reportes` carga
- [ ] `/caja/session/open` funciona
- [ ] `/caja/session/close` funciona
- [ ] Logs sin errores críticos
- [ ] Caja de prueba creada y configurada
- [ ] Sesión de prueba abierta y cerrada
- [ ] Totales calculados correctamente

---

## 🐛 TROUBLESHOOTING

### Error: "Column already exists"

**Causa:** Migración ya ejecutada parcialmente  
**Solución:** La migración es idempotente (IF NOT EXISTS), esto es normal. Continuar.

### Error: "Table does not exist"

**Causa:** Tablas no creadas  
**Solución:** Verificar que las tablas `pos_registers` y `register_sessions` existen:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('pos_registers', 'register_sessions');
```

### Error: "Permission denied"

**Causa:** Usuario de BD sin permisos  
**Solución:** Ejecutar como usuario con permisos:
```bash
sudo -u postgres psql -d bimba_db -f migrations/2025_01_15_bimba_cajas_mvp1_paymentstack.sql
```

### Error: "Template not found"

**Causa:** Templates no desplegados  
**Solución:** Verificar que templates existen:
```bash
ls -la app/templates/admin/registers/form.html
ls -la app/templates/caja/session/open.html
ls -la app/templates/caja/session/close.html
ls -la app/templates/admin/cajas/reportes.html
```

### Error: "AttributeError: 'PosRegister' object has no attribute 'payment_provider_primary'"

**Causa:** Modelo no actualizado o migración no ejecutada  
**Solución:** 
1. Verificar que migración se ejecutó
2. Reiniciar aplicación (reload modelos)
3. Verificar que código actualizado

---

## 📝 NOTAS IMPORTANTES

1. **Migración idempotente:** Puede ejecutarse múltiples veces sin problemas
2. **Defaults automáticos:** Registros existentes se actualizan con defaults
3. **Compatibilidad:** Campos nuevos son nullable (excepto defaults), no rompe código existente
4. **Sin downtime:** Migración es rápida, servicios pueden seguir corriendo

---

## ✅ DEFINITION OF DONE

- [ ] Backup de BD creado y verificado
- [ ] Migración ejecutada sin errores
- [ ] Servicios reiniciados y funcionando
- [ ] Todas las URLs probadas y funcionando
- [ ] Logs sin errores críticos
- [ ] Caja de prueba creada y configurada
- [ ] Sesión de prueba abierta y cerrada correctamente
- [ ] Reportes muestran datos correctos

---

**Runbook completado ✅**


