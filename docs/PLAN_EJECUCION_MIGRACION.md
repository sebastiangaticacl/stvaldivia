# Plan de Ejecución: Migración a MySQL

**Fecha:** 2025-12-25  
**Estado:** Listo para ejecutar

---

## 🎯 OBJETIVO

Migrar la base de datos de PostgreSQL a MySQL de forma segura y verificable.

---

## 📋 CHECKLIST PRE-EJECUCIÓN

### Antes de Empezar

- [ ] **Backup completo de PostgreSQL**
  ```bash
  pg_dump -h localhost -U usuario -d bimba_db > backup_postgresql_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **MySQL instalado y configurado**
  ```bash
  mysql --version
  # Debe ser MySQL 8.0+ o MariaDB 10.3+
  ```

- [ ] **Base de datos MySQL creada**
  ```sql
  CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'bimba_user'@'localhost' IDENTIFIED BY 'password_seguro';
  GRANT ALL PRIVILEGES ON bimba_db.* TO 'bimba_user'@'localhost';
  FLUSH PRIVILEGES;
  ```

- [ ] **DATABASE_URL configurado**
  ```bash
  export DATABASE_URL="mysql://bimba_user:password_seguro@localhost:3306/bimba_db"
  # O en .env:
  # DATABASE_URL=mysql://bimba_user:password_seguro@localhost:3306/bimba_db
  ```

- [ ] **Dependencias Python instaladas**
  ```bash
  pip install -r requirements.txt
  # Verificar que mysql-connector-python está instalado
  ```

---

## 🚀 EJECUCIÓN PASO A PASO

### Paso 1: Ejecutar Diagnóstico PostgreSQL (Opcional pero Recomendado)

Si aún tienes acceso a PostgreSQL, ejecutar diagnóstico:

```bash
cd /var/www/stvaldivia
./scripts/diagnostico_db_servidor.sh
```

**Salida esperada:**
- `docs/SCHEMA_REAL.sql`
- `docs/TABLES_ROWCOUNT.md`
- `docs/FKS_REAL.md`
- `docs/INDEXES_REAL.md`

**Propósito:** Tener referencia del esquema original para comparar.

---

### Paso 2: Ejecutar Migración

```bash
cd /Users/sebagatica/stvaldivia  # O ruta del proyecto
export DATABASE_URL="mysql://bimba_user:password_seguro@localhost:3306/bimba_db"
./scripts/migrar_a_mysql.sh
```

**El script:**
1. ✅ Verifica requisitos previos
2. ✅ Crea backup automático
3. ✅ Pide confirmación
4. ✅ Aplica todas las migraciones MySQL
5. ✅ Verifica tablas creadas
6. ✅ Muestra resumen

**Tiempo estimado:** 2-5 minutos

---

### Paso 3: Validar Migración

```bash
export DATABASE_URL="mysql://bimba_user:password_seguro@localhost:3306/bimba_db"
./scripts/validar_migracion_mysql.sh
```

**El script verifica:**
- ✅ Tablas existentes
- ✅ Columnas críticas (UUID → CHAR(36))
- ✅ Índices creados
- ✅ Conectividad desde Python

**Tiempo estimado:** 1-2 minutos

---

### Paso 4: Probar Aplicación

```bash
export DATABASE_URL="mysql://bimba_user:password_seguro@localhost:3306/bimba_db"
python3 run_local.py
```

**Verificar:**
- ✅ Aplicación inicia sin errores
- ✅ Endpoints responden correctamente
- ✅ Queries complejas funcionan
- ✅ Performance aceptable

---

## 🔄 ROLLBACK (Si es Necesario)

### Opción 1: Restaurar desde Backup

```bash
# Restaurar PostgreSQL
psql -h localhost -U usuario -d bimba_db < backup_postgresql_YYYYMMDD_HHMMSS.sql

# O restaurar MySQL
mysql -u bimba_user -p bimba_db < backup_mysql_YYYYMMDD_HHMMSS.sql
```

### Opción 2: Revertir DATABASE_URL

```bash
# Volver a PostgreSQL
export DATABASE_URL="postgresql://usuario:password@localhost:5432/bimba_db"
```

---

## ⚠️ PROBLEMAS COMUNES

### Error: "mysql: command not found"

**Solución:**
```bash
# Ubuntu/Debian
sudo apt-get install mysql-client

# macOS
brew install mysql-client
```

### Error: "Access denied for user"

**Solución:**
- Verificar credenciales en DATABASE_URL
- Verificar permisos del usuario MySQL
- Verificar que el usuario puede conectarse desde localhost

### Error: "Table already exists"

**Solución:**
- Las migraciones usan `CREATE TABLE IF NOT EXISTS`, debería ser seguro
- Si persiste, verificar que la tabla no tiene estructura diferente

### Error: "Unknown column 'X' in 'field list'"

**Solución:**
- Verificar que todas las migraciones se aplicaron en orden
- Revisar logs del script de migración
- Aplicar migraciones faltantes manualmente

---

## 📊 VERIFICACIÓN MANUAL

### Verificar Tablas

```sql
mysql -u bimba_user -p bimba_db
SHOW TABLES;
DESCRIBE payment_intents;
DESCRIBE payment_agents;
```

### Verificar Datos

```sql
SELECT COUNT(*) FROM payment_intents;
SELECT COUNT(*) FROM payment_agents;
```

### Verificar Índices

```sql
SHOW INDEXES FROM payment_intents;
SHOW INDEXES FROM payment_agents;
```

---

## ✅ CRITERIOS DE ÉXITO

La migración es exitosa si:

1. ✅ Todas las tablas existen
2. ✅ Todas las columnas críticas tienen el tipo correcto (CHAR(36) para UUIDs)
3. ✅ Todos los índices están creados
4. ✅ La aplicación inicia sin errores
5. ✅ Los endpoints críticos funcionan
6. ✅ Las queries complejas retornan resultados correctos

---

## 📞 SOPORTE

Si encuentras problemas:

1. Revisar logs del script de migración
2. Verificar `docs/ANALISIS_MIGRACIONES_POSTGRESQL_MYSQL.md`
3. Consultar `docs/GUIA_MIGRACION_MYSQL.md`
4. Revisar errores de MySQL: `SHOW ERRORS;`

---

**Última actualización:** 2025-12-25

