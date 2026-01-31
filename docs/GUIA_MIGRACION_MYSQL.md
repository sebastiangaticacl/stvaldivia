# Guía de Migración: PostgreSQL → MySQL

**Fecha:** 2025-12-25  
**Versión:** 1.0  
**Estado:** Preparación completa

---

## 📋 RESUMEN EJECUTIVO

### Estado Actual
- ✅ **Código Python:** Adaptado para MySQL (UUID → String, ILIKE → func.lower().like())
- ✅ **Migraciones SQL:** Versiones MySQL creadas
- ⚠️ **Diagnóstico PostgreSQL:** Pendiente ejecutar en servidor
- ⚠️ **Pruebas:** Pendiente validar en entorno de desarrollo

### Archivos Preparados

#### Migraciones MySQL Creadas:
1. `migrations/2025_01_15_payment_intents_mysql.sql`
2. `migrations/2025_12_18_payment_agents_mysql.sql`
3. `migrations/2025_01_15_bimba_cajas_mvp1_paymentstack_mysql.sql`
4. `migrations/2025_01_15_bimba_pos_payment_provider_mysql.sql`
5. `migrations/2025_01_15_add_is_test_to_pos_registers_mysql.sql`
6. `migrations/2025_12_17_add_is_test_to_products_mysql.sql`

#### Documentación:
- `docs/ANALISIS_MIGRACIONES_POSTGRESQL_MYSQL.md` - Análisis detallado
- `docs/ESTADO_MIGRACION_MYSQL.md` - Estado actual
- `docs/GUIA_MIGRACION_MYSQL.md` - Esta guía

---

## 🚀 PLAN DE MIGRACIÓN

### Fase 1: Preparación (ANTES de migrar)

#### 1.1 Ejecutar Diagnóstico PostgreSQL
```bash
cd /var/www/stvaldivia
./scripts/diagnostico_db_servidor.sh
```

**Salida esperada:**
- `docs/SCHEMA_REAL.sql` - Esquema completo
- `docs/TABLES_ROWCOUNT.md` - Conteo de filas
- `docs/FKS_REAL.md` - Foreign Keys
- `docs/INDEXES_REAL.md` - Índices

#### 1.2 Backup Completo
```bash
# Backup de PostgreSQL
pg_dump -h localhost -U usuario -d bimba_db > backup_postgresql_$(date +%Y%m%d_%H%M%S).sql

# O usando mysqldump si ya está en MySQL
mysqldump -u usuario -p bimba_db > backup_mysql_$(date +%Y%m%d_%H%M%S).sql
```

#### 1.3 Configurar MySQL
```bash
# Crear base de datos
mysql -u root -p
CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'bimba_user'@'localhost' IDENTIFIED BY 'password_seguro';
GRANT ALL PRIVILEGES ON bimba_db.* TO 'bimba_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 1.4 Actualizar DATABASE_URL
```bash
# En .env o variables de entorno
DATABASE_URL=mysql://bimba_user:password_seguro@localhost:3306/bimba_db
```

---

### Fase 2: Migración de Datos

#### 2.1 Opción A: Migración Directa (Recomendada para desarrollo)

**Paso 1:** Exportar datos desde PostgreSQL
```bash
# Exportar solo datos (sin schema)
pg_dump -h localhost -U usuario -d bimba_db --data-only --inserts > datos_postgresql.sql
```

**Paso 2:** Adaptar datos para MySQL
- Reemplazar `UUID` por `CHAR(36)` con valores UUID como strings
- Reemplazar `TRUE/FALSE` por `1/0` si es necesario
- Verificar encoding UTF-8

**Paso 3:** Importar schema MySQL
```bash
mysql -u bimba_user -p bimba_db < migrations/2025_01_15_payment_intents_mysql.sql
mysql -u bimba_user -p bimba_db < migrations/2025_12_18_payment_agents_mysql.sql
# ... resto de migraciones
```

**Paso 4:** Importar datos
```bash
mysql -u bimba_user -p bimba_db < datos_postgresql_adaptados.sql
```

#### 2.2 Opción B: Migración con Herramientas

**Usar herramientas como:**
- `pgloader` (recomendado)
- `mysqldump` + `pg_dump` + conversión manual
- Scripts Python personalizados

---

### Fase 3: Validación

#### 3.1 Verificar Schema
```sql
-- En MySQL
SHOW TABLES;
DESCRIBE payment_intents;
DESCRIBE payment_agents;
-- ... resto de tablas
```

#### 3.2 Verificar Datos
```sql
-- Comparar conteos
SELECT COUNT(*) FROM payment_intents;
SELECT COUNT(*) FROM payment_agents;
-- ... resto de tablas
```

#### 3.3 Verificar Índices
```sql
SHOW INDEXES FROM payment_intents;
SHOW INDEXES FROM payment_agents;
```

#### 3.4 Probar Aplicación
```bash
# Iniciar aplicación local
python3 run_local.py

# Probar endpoints críticos
curl http://localhost:5001/api/health
curl http://localhost:5001/api/payment-intents
```

---

### Fase 4: Rollback (si es necesario)

#### 4.1 Restaurar desde Backup
```bash
# Restaurar PostgreSQL
psql -h localhost -U usuario -d bimba_db < backup_postgresql_YYYYMMDD_HHMMSS.sql

# O restaurar MySQL
mysql -u bimba_user -p bimba_db < backup_mysql_YYYYMMDD_HHMMSS.sql
```

#### 4.2 Revertir DATABASE_URL
```bash
# Volver a PostgreSQL
DATABASE_URL=postgresql://usuario:password@localhost:5432/bimba_db
```

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### 1. UUIDs
- **PostgreSQL:** `UUID` tipo nativo con `gen_random_uuid()`
- **MySQL:** `CHAR(36)` o `VARCHAR(36)` con UUIDs como strings
- **Solución:** Generar UUIDs en Python: `str(uuid.uuid4())`

### 2. Índices Parciales
- **PostgreSQL:** Soporta `CREATE INDEX ... WHERE condition`
- **MySQL:** No soportado, usar índices completos
- **Impacto:** Índices más grandes, pero funcionalidad equivalente

### 3. DO Blocks
- **PostgreSQL:** `DO $$ ... END $$` para lógica procedural
- **MySQL:** Usar procedimientos almacenados o queries directas
- **Solución:** Migraciones MySQL usan queries directas

### 4. Comentarios
- **PostgreSQL:** `COMMENT ON TABLE/COLUMN`
- **MySQL:** `ALTER TABLE ... COMMENT` o `MODIFY COLUMN ... COMMENT`
- **Solución:** Adaptado en migraciones MySQL

### 5. ILIKE
- **PostgreSQL:** `ILIKE` (case-insensitive)
- **MySQL:** `LOWER() LIKE` o `LIKE` con collation
- **Solución:** Ya adaptado en código Python

---

## 📊 CHECKLIST FINAL

### Pre-Migración
- [ ] Diagnóstico PostgreSQL ejecutado
- [ ] Backup completo realizado
- [ ] MySQL configurado y accesible
- [ ] DATABASE_URL actualizado
- [ ] Migraciones MySQL revisadas

### Durante Migración
- [ ] Schema MySQL importado
- [ ] Datos migrados y validados
- [ ] Índices creados correctamente
- [ ] Foreign Keys verificadas

### Post-Migración
- [ ] Aplicación inicia correctamente
- [ ] Endpoints críticos funcionan
- [ ] Queries complejas validadas
- [ ] Performance aceptable
- [ ] Rollback plan documentado

---

## 🔗 REFERENCIAS

- **Análisis de Migraciones:** `docs/ANALISIS_MIGRACIONES_POSTGRESQL_MYSQL.md`
- **Estado Actual:** `docs/ESTADO_MIGRACION_MYSQL.md`
- **Script de Diagnóstico:** `scripts/diagnostico_db_servidor.sh`

---

**Última actualización:** 2025-12-25

