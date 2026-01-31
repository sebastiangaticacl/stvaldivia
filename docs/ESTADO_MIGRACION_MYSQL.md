# Estado de Migración a MySQL

**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')  
**Estado:** Preparación avanzada, pendiente ejecución

---

## ✅ CAMBIOS YA APLICADOS

### 1. Dependencias
- ✅ `mysql-connector-python>=8.0.33` agregado a `requirements.txt`
- ✅ `psycopg2-binary` comentado (legacy PostgreSQL)

### 2. Configuración de Base de Datos
- ✅ `app/__init__.py`: Soporte multi-DB (MySQL, PostgreSQL, SQLite)
- ✅ Detección automática de tipo de BD desde `DATABASE_URL`
- ✅ Configuración de engine options específicos para MySQL

### 3. Modelos ORM
- ✅ `app/models/pos_models.py`: UUID migrado a `String(36)`
  - `PaymentIntent.id`: String(36) en lugar de UUID
  - `PaymentAgent.id`: String(36) en lugar de UUID

### 4. Consultas SQL
- ✅ `app/services/pos_service.py`: ILIKE → `func.lower().like()`
- ✅ `app/routes/product_routes.py`: ILIKE → `func.lower().like()`
- ✅ `app/routes/inventory_admin_routes.py`: ILIKE → `func.lower().like()`
- ✅ `app/routes.py`: ILIKE → `func.lower().like()`
- ✅ `app/blueprints/equipo/routes.py`: ILIKE → `func.lower().like()`
- ✅ `app/helpers/puesto_validator.py`: ILIKE → `func.lower().like()`

### 5. Monitoreo
- ✅ `app/helpers/db_monitor.py`: Adaptado para MySQL/PostgreSQL

---

## ⚠️ PENDIENTE

### 1. Diagnóstico de PostgreSQL
- ⚠️ **CRÍTICO**: Ejecutar script de diagnóstico en servidor
- ⚠️ Necesario para obtener esquema real antes de migrar
- **Comando:** `cd /var/www/stvaldivia && ./scripts/diagnostico_db_servidor.sh`

### 2. Migraciones SQL
- ⚠️ Adaptar migraciones existentes para MySQL
- ⚠️ Verificar sintaxis específica de MySQL
- ⚠️ Archivos en `migrations/` necesitan revisión

### 3. Pruebas
- ⚠️ Probar conexión a MySQL
- ⚠️ Verificar que todas las queries funcionen
- ⚠️ Validar integridad de datos

---

## 📋 CHECKLIST PRE-MIGRACIÓN

- [ ] Ejecutar diagnóstico de PostgreSQL en servidor
- [ ] Revisar esquema real vs modelos ORM
- [ ] Adaptar migraciones SQL para MySQL
- [ ] Configurar DATABASE_URL para MySQL
- [ ] Probar conexión local a MySQL
- [ ] Validar queries críticas
- [ ] Backup completo de PostgreSQL
- [ ] Plan de rollback

---

## 🚀 PRÓXIMOS PASOS

1. **Ejecutar diagnóstico** en servidor para obtener esquema real
2. **Revisar migraciones** y adaptarlas a MySQL
3. **Configurar MySQL** de prueba
4. **Probar migración** en entorno de desarrollo
5. **Validar** funcionamiento completo
6. **Planificar** migración de producción

---

**Última actualización:** $(date '+%Y-%m-%d %H:%M:%S')
