# Comandos Exactos para Exportar Esquema PostgreSQL

## ⚠️ SITUACIÓN DETECTADA

**Entorno Local Actual:**
- Base de datos: SQLite (`instance/bimba.db`)
- PostgreSQL: No detectado
- Archivo `.env`: No encontrado en `/var/www/stvaldivia/.env`

**Para ejecutar estos comandos, necesitas:**
1. Acceso a servidor PostgreSQL (local o remoto)
2. Archivo `.env` con `DATABASE_URL` o credenciales manuales
3. Herramientas `psql` y `pg_dump` instaladas

---

## 📋 COMANDOS EXACTOS

### PASO 1: Detectar Configuración

```bash
# Leer DATABASE_URL desde .env
cat /var/www/stvaldivia/.env | grep "^DATABASE_URL="

# O desde variables de entorno
echo $DATABASE_URL
```

**Formato esperado:** `postgresql://user:password@host:port/dbname`

### PASO 2: Extraer Credenciales (Manual)

Si `DATABASE_URL` está en formato: `postgresql://usuario:password@localhost:5432/bimba_db`

```bash
# Parsear manualmente (ajustar según tu DATABASE_URL)
DB_USER="usuario"
DB_PASS="password"
DB_HOST="localhost"  # o IP remota
DB_PORT="5432"
DB_NAME="bimba_db"
```

### PASO 3: Generar Dump Schema-Only

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

### PASO 4: Reporte de Tablas y Row Count

```bash
psql -h "${DB_HOST}" \
     -p "${DB_PORT}" \
     -U "${DB_USER}" \
     -d "${DB_NAME}" \
     -t -A -F'|' \
     -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) as size,
    (SELECT COUNT(*) FROM information_schema.tables t2 
     WHERE t2.table_schema = 'public' 
     AND t2.table_name = t.tablename) as exists_flag
FROM pg_tables t
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.' || tablename) DESC;
" | while IFS='|' read -r table size exists; do
    if [ -n "$table" ]; then
        ROW_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -A -c "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null || echo "N/A")
        echo "| \`$table\` | $size | $ROW_COUNT |"
    fi
done > docs/TABLES_ROWCOUNT.md
```

**Ruta de salida:** `docs/TABLES_ROWCOUNT.md`

### PASO 5: Reporte de Foreign Keys

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
    tc.constraint_name as constraint_name,
    rc.delete_rule as on_delete,
    rc.update_rule as on_update
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
  AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
  AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;
" > docs/FKS_REAL.md
```

**Ruta de salida:** `docs/FKS_REAL.md`

### PASO 6: Reporte de Índices

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

---

## 🚀 EJECUCIÓN AUTOMÁTICA (Script)

Si prefieres usar el script automático:

```bash
cd /Users/sebagatica/stvaldivia
./scripts/export_postgres_schema.sh
```

El script ejecuta todos los pasos automáticamente.

---

## 📊 VERIFICACIÓN

```bash
# Verificar archivos generados
ls -lh docs/SCHEMA_REAL.sql \
       docs/TABLES_ROWCOUNT.md \
       docs/FKS_REAL.md \
       docs/INDEXES_REAL.md

# Ver tamaño del dump
du -h docs/SCHEMA_REAL.sql

# Ver primeras líneas
head -30 docs/SCHEMA_REAL.sql
head -20 docs/TABLES_ROWCOUNT.md
```

---

## 🔧 INSTALACIÓN DE HERRAMIENTAS (si faltan)

### macOS

```bash
# Instalar PostgreSQL client
brew install postgresql

# Verificar instalación
psql --version
pg_dump --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install postgresql-client
```

---

## 📝 NOTAS IMPORTANTES

1. **Solo lectura:** Todos los comandos son de solo lectura
2. **Sin datos:** El dump no incluye datos, solo estructura
3. **Sin owner:** Se excluyen owners para portabilidad
4. **Variables de entorno:** `PGPASSWORD` se usa para evitar prompts

---

## ⚠️ SI NO TIENES ACCESO A POSTGRESQL

Si estás en entorno local con SQLite y necesitas el esquema de PostgreSQL:

1. **Opción A:** Conectarte a servidor remoto de producción (con VPN/SSH)
2. **Opción B:** Configurar PostgreSQL localmente
3. **Opción C:** Solicitar dump a equipo de infraestructura

