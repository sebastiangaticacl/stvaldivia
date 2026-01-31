# Instrucciones para Exportar Esquema Real de PostgreSQL

## ⚠️ SITUACIÓN ACTUAL

**Entorno Local detectado:** SQLite (`instance/bimba.db`)  
**PostgreSQL:** No detectado en entorno local  
**Archivo `.env`:** No encontrado en `/var/www/stvaldivia/.env`

## 📋 REQUISITOS

1. **PostgreSQL instalado y corriendo**
2. **Herramientas de línea de comandos:**
   - `psql` (cliente PostgreSQL)
   - `pg_dump` (utilidad de backup)
3. **Acceso a base de datos:**
   - Archivo `.env` con `DATABASE_URL` en `/var/www/stvaldivia/.env`
   - O variables de entorno configuradas

## 🚀 EJECUCIÓN

### Opción 1: Script Automático (Recomendado)

```bash
cd /Users/sebagatica/stvaldivia
./scripts/export_postgres_schema.sh
```

El script:
1. ✅ Detecta `DATABASE_URL` desde `/var/www/stvaldivia/.env`
2. ✅ Verifica conectividad
3. ✅ Genera dump schema-only
4. ✅ Genera 3 reportes (tablas, FKs, índices)

### Opción 2: Comandos Manuales

Si el script no funciona, ejecutar manualmente:

#### 1. Detectar configuración

```bash
# Leer DATABASE_URL
cat /var/www/stvaldivia/.env | grep DATABASE_URL

# O desde variables de entorno
echo $DATABASE_URL
```

#### 2. Parsear DATABASE_URL

Formato esperado: `postgresql://user:password@host:port/dbname`

```bash
# Ejemplo de parsing (ajustar valores)
DB_USER="usuario"
DB_PASS="password"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="bimba_db"
```

#### 3. Generar dump schema-only

```bash
cd /Users/sebagatica/stvaldivia
export PGPASSWORD="${DB_PASS}"

pg_dump -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --schema-only \
        --no-owner \
        --no-privileges \
        --no-tablespaces \
        --no-security-labels \
        --no-comments \
        > docs/SCHEMA_REAL.sql
```

**Ruta de salida:** `docs/SCHEMA_REAL.sql`

#### 4. Reporte de Tablas y Row Count

```bash
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.' || tablename) DESC;
" > docs/TABLES_ROWCOUNT.md
```

**Ruta de salida:** `docs/TABLES_ROWCOUNT.md`

#### 5. Reporte de Foreign Keys

```bash
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -c "
SELECT 
    tc.table_name as tabla_origen,
    kcu.column_name as columna,
    ccu.table_name AS tabla_destino,
    ccu.column_name AS columna_destino,
    tc.constraint_name,
    rc.delete_rule as on_delete,
    rc.update_rule as on_update
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;
" > docs/FKS_REAL.md
```

**Ruta de salida:** `docs/FKS_REAL.md`

#### 6. Reporte de Índices

```bash
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -c "
SELECT 
    tablename,
    indexname,
    indexdef,
    CASE 
        WHEN indexdef LIKE '%UNIQUE%' THEN 'Sí'
        ELSE 'No'
    END as es_unico
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
" > docs/INDEXES_REAL.md
```

**Ruta de salida:** `docs/INDEXES_REAL.md`

## 📁 ARCHIVOS GENERADOS

Todos los archivos se generan en `docs/`:

1. **`SCHEMA_REAL.sql`** - Dump completo schema-only
2. **`TABLES_ROWCOUNT.md`** - Tablas con tamaño y conteo de filas
3. **`FKS_REAL.md`** - Todas las Foreign Keys reales
4. **`INDEXES_REAL.md`** - Índices por tabla (incluyendo únicos)

## 🔍 VERIFICACIÓN

```bash
# Verificar que los archivos se generaron
ls -lh docs/SCHEMA_REAL.sql docs/TABLES_ROWCOUNT.md docs/FKS_REAL.md docs/INDEXES_REAL.md

# Ver tamaño del dump
du -h docs/SCHEMA_REAL.sql

# Ver primeras líneas del schema
head -50 docs/SCHEMA_REAL.sql
```

## ⚠️ TROUBLESHOOTING

### Error: "psql: command not found"

```bash
# Instalar PostgreSQL client (macOS)
brew install postgresql

# O agregar al PATH
export PATH="/usr/local/bin:$PATH"
```

### Error: "connection refused"

- Verificar que PostgreSQL está corriendo
- Verificar host y puerto
- Verificar firewall

### Error: "authentication failed"

- Verificar credenciales en `.env`
- Verificar `pg_hba.conf` si es necesario

### Error: "database does not exist"

- Verificar nombre de base de datos
- Listar bases disponibles: `psql -l`

## 📝 NOTAS

- **Solo lectura:** Todos los comandos son de solo lectura, no modifican la BD
- **Sin datos:** El dump schema-only no incluye datos, solo estructura
- **Sin owner/privileges:** Se excluyen para portabilidad
- **Formato:** Todos los reportes en Markdown para fácil lectura

