# Análisis de Migración a MySQL

**Fecha:** 2025-12-25  
**Estado:** Análisis inicial  
**Objetivo:** Evaluar y planificar la migración de PostgreSQL/SQLite a MySQL

---

## 📊 ESTADO ACTUAL

### Base de Datos Actual

**Producción:**
- **Motor:** PostgreSQL
- **Driver:** `psycopg2-binary` (requirements.txt línea 24)
- **URL:** Configurado vía `DATABASE_URL` (variable de entorno)
- **Formato:** `postgresql://user:pass@host:port/dbname`

**Desarrollo Local:**
- **Motor:** SQLite
- **Archivo:** `instance/bimba.db`
- **URL:** `sqlite:///path/to/bimba.db`
- **Fallback:** Si no hay `DATABASE_URL`, usa SQLite automáticamente

### ORM y Framework

- **ORM:** SQLAlchemy 2.0.44
- **Flask Extension:** Flask-SQLAlchemy 3.1.1
- **Configuración:** `app/__init__.py` líneas 270-305

---

## 🔍 DEPENDENCIAS ESPECÍFICAS DE POSTGRESQL

### 1. Tipos de Datos Específicos

#### UUID (PostgreSQL)
**Ubicación:** `app/models/pos_models.py` línea 8
```python
from sqlalchemy.dialects.postgresql import UUID
```

**Uso encontrado:**
- `payment_intents.id` (UUID PRIMARY KEY)
- `PaymentIntent` model usa `UUID` type

**Migración MySQL:**
- MySQL 8.0+ soporta `BINARY(16)` o `CHAR(36)`
- Alternativa: Usar `VARCHAR(36)` con UUIDs como strings
- SQLAlchemy: `from sqlalchemy import String` y generar UUIDs en Python

#### JSON/JSONB
**Estado:** El proyecto usa `Text` para JSON (no JSONB)
- `cart_items = db.Column(Text, nullable=True)` (JSON string)
- Compatible con MySQL `TEXT` o `JSON` (MySQL 5.7+)

**No requiere cambios** ✅

### 2. Funciones Específicas de PostgreSQL

#### `gen_random_uuid()`
**Ubicación:** `migrations/2025_01_15_payment_intents.sql` línea 18
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Migración MySQL:**
- MySQL: `UUID()` o generar en Python con `uuid.uuid4()`
- Cambiar a: `id VARCHAR(36) PRIMARY KEY DEFAULT (UUID())` (MySQL 8.0+)
- O mejor: Generar UUIDs en Python antes de insertar

#### `ILIKE` (Case-insensitive LIKE)
**Ubicación:** 55 matches encontrados en 14 archivos
- `app/helpers/puesto_validator.py` (10 matches)
- `app/routes.py` (7 matches)
- Otros archivos

**Migración MySQL:**
- MySQL: Usar `LIKE` con `LOWER()` o `UPPER()`
- Ejemplo: `WHERE LOWER(column) LIKE LOWER('%pattern%')`
- O usar `COLLATE utf8mb4_unicode_ci` para case-insensitive

#### `pg_stat_file()` y `pg_indexes`
**Ubicación:** `app/helpers/db_monitor.py` líneas 137-170
```python
version_query = text("SELECT version()")
created_query = text("""
    SELECT pg_stat_file('base/' || oid || '/PG_VERSION').modification
    FROM pg_database
    WHERE datname = current_database()
""")
```

**Migración MySQL:**
- `SELECT version()` → `SELECT VERSION()` (compatible)
- `pg_stat_file()` → No existe en MySQL, usar `SHOW TABLE STATUS` o información del schema
- `pg_indexes` → `SHOW INDEXES FROM table_name` o `information_schema.STATISTICS`

#### `information_schema` queries
**Ubicación:** Múltiples archivos
- Compatible entre PostgreSQL y MySQL ✅
- Solo verificar sintaxis de columnas específicas

### 3. Sintaxis SQL Específica

#### Índices Parciales (Partial Indexes)
**Ubicación:** `migrations/2025_01_15_payment_intents.sql` línea 68-69
```sql
CREATE INDEX IF NOT EXISTS idx_payment_intents_pending 
ON payment_intents(register_id, status, created_at) 
WHERE status IN ('READY', 'IN_PROGRESS');
```

**Migración MySQL:**
- MySQL no soporta índices parciales con `WHERE`
- Alternativas:
  1. Crear índice completo (menos eficiente)
  2. Usar índices virtuales o vistas
  3. Aceptar que el índice será más grande

#### `COMMENT ON TABLE/COLUMN`
**Ubicación:** `migrations/2025_01_15_payment_intents.sql` líneas 72-76
```sql
COMMENT ON TABLE payment_intents IS '...';
COMMENT ON COLUMN payment_intents.cart_hash IS '...';
```

**Migración MySQL:**
- MySQL: `ALTER TABLE table_name COMMENT = '...'`
- Columnas: `ALTER TABLE table_name MODIFY COLUMN column_name TYPE COMMENT '...'`
- O usar documentación externa

---

## 📋 MODELOS Y TABLAS

### Modelos Identificados (30+ modelos)

**Principales:**
- `PosSession`, `PosSale`, `PosSaleItem`, `PosRegister`
- `PaymentIntent`, `PaymentAgent`
- `Jornada`, `PlanillaTrabajador`, `AperturaCaja`
- `Employee`, `EmployeeShift`, `EmployeePayment`
- `InventoryItem`, `Product`, `Recipe`
- `Delivery`, `TicketEntrega`
- Y muchos más...

**Total:** ~30 modelos en `app/models/`

### Tipos de Datos Usados

- `Integer`, `String`, `Text` ✅ Compatible
- `Numeric(10, 2)` ✅ Compatible (DECIMAL en MySQL)
- `Boolean` ✅ Compatible (TINYINT(1) en MySQL)
- `DateTime` ✅ Compatible
- `UUID` ⚠️ Requiere cambio (ver arriba)

---

## 🔧 CAMBIOS NECESARIOS

### 1. Requirements.txt

**Actual:**
```txt
psycopg2-binary
```

**Nuevo:**
```txt
# MySQL driver (elegir uno):
mysql-connector-python>=8.0.33
# O alternativamente:
# PyMySQL>=1.1.0
```

### 2. Configuración de Base de Datos

**Archivo:** `app/__init__.py` líneas 270-305

**Cambios:**
1. Actualizar detección de motor de BD
2. Cambiar formato de URL de PostgreSQL a MySQL
3. Actualizar opciones de conexión

**Formato MySQL:**
```python
# MySQL con mysql-connector-python
database_url = 'mysql+mysqlconnector://user:pass@host:port/dbname'

# MySQL con PyMySQL
database_url = 'mysql+pymysql://user:pass@host:port/dbname'
```

**Opciones de conexión:**
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 3600,
    'connect_args': {
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        # MySQL no tiene connect_timeout en connect_args
        # Usar timeout en la URL o en el pool
    }
}
```

### 3. Modelos con UUID

**Archivo:** `app/models/pos_models.py`

**Cambio:**
```python
# Antes (PostgreSQL)
from sqlalchemy.dialects.postgresql import UUID
id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# Después (MySQL)
from sqlalchemy import String
import uuid
id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
```

### 4. Queries con ILIKE

**Archivos afectados:** 14 archivos con 55 matches

**Estrategia:**
1. Buscar y reemplazar `ILIKE` por `LIKE` con `LOWER()`
2. O configurar collation case-insensitive en MySQL

**Ejemplo:**
```python
# Antes
.filter(column.ilike('%pattern%'))

# Después
.filter(func.lower(column).like('%pattern%'))
```

### 5. Funciones de Monitoreo

**Archivo:** `app/helpers/db_monitor.py`

**Cambios:**
- `pg_stat_file()` → Eliminar o usar alternativa MySQL
- `pg_indexes` → `SHOW INDEXES` o `information_schema.STATISTICS`
- `SELECT version()` → `SELECT VERSION()` (compatible)

### 6. Migraciones SQL

**Directorio:** `migrations/`

**Archivos a actualizar:**
- `2025_01_15_payment_intents.sql` (UUID, índices parciales, comentarios)
- Otros archivos con sintaxis PostgreSQL específica

**Estrategia:**
1. Crear versiones MySQL de las migraciones
2. O usar Alembic/Flask-Migrate para migraciones agnósticas

---

## 📝 PLAN DE MIGRACIÓN

### Fase 1: Preparación (1-2 días)

1. **Backup completo de PostgreSQL**
   ```bash
   pg_dump -U user -d database > backup_postgresql_$(date +%Y%m%d).sql
   ```

2. **Instalar MySQL y crear base de datos**
   ```sql
   CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **Actualizar requirements.txt**
   - Agregar `mysql-connector-python` o `PyMySQL`
   - Comentar/eliminar `psycopg2-binary`

### Fase 2: Cambios en Código (2-3 días)

1. **Actualizar configuración de BD** (`app/__init__.py`)
   - Cambiar detección de motor
   - Actualizar formato de URL
   - Ajustar opciones de conexión

2. **Actualizar modelos con UUID**
   - Cambiar `UUID` a `String(36)`
   - Actualizar generación de UUIDs

3. **Reemplazar ILIKE**
   - Buscar y reemplazar en 14 archivos
   - Usar `func.lower()` con `like()`

4. **Actualizar funciones de monitoreo**
   - Reemplazar queries específicas de PostgreSQL
   - Usar sintaxis MySQL compatible

### Fase 3: Migración de Datos (1-2 días)

1. **Exportar datos de PostgreSQL**
   ```bash
   pg_dump --data-only --column-inserts database > data_export.sql
   ```

2. **Convertir formato SQL**
   - Adaptar sintaxis PostgreSQL a MySQL
   - Convertir UUIDs si es necesario

3. **Importar a MySQL**
   ```bash
   mysql -u user -p database < data_import.sql
   ```

### Fase 4: Migraciones SQL (1 día)

1. **Actualizar migraciones existentes**
   - Convertir sintaxis PostgreSQL a MySQL
   - Adaptar tipos de datos

2. **Crear nuevas migraciones si es necesario**
   - Para cambios específicos de MySQL

### Fase 5: Pruebas (2-3 días)

1. **Pruebas unitarias**
   - Verificar todos los modelos
   - Probar queries complejas

2. **Pruebas de integración**
   - Flujos completos de la aplicación
   - Verificar rendimiento

3. **Pruebas de migración**
   - Verificar integridad de datos
   - Comparar resultados

---

## ⚠️ RIESGOS Y CONSIDERACIONES

### 1. Rendimiento

- **Índices parciales:** MySQL no los soporta, puede afectar rendimiento
- **UUIDs como strings:** Más espacio que binary, pero más fácil de debuggear

### 2. Compatibilidad

- **Case sensitivity:** MySQL puede ser case-sensitive según configuración
- **Charset:** Asegurar `utf8mb4` para emojis y caracteres especiales

### 3. Funcionalidades Perdidas

- **Índices parciales:** No disponibles en MySQL
- **JSONB:** MySQL tiene JSON pero diferente implementación
- **Funciones específicas:** `pg_stat_file()`, etc.

### 4. Migración de Datos

- **UUIDs:** Convertir de formato PostgreSQL a string
- **Timestamps:** Verificar zona horaria
- **JSON:** Compatible pero verificar parsing

---

## ✅ CHECKLIST DE MIGRACIÓN

### Pre-migración
- [ ] Backup completo de PostgreSQL
- [ ] Documentar todas las queries específicas de PostgreSQL
- [ ] Listar todos los modelos y sus relaciones
- [ ] Identificar todas las funciones específicas de PostgreSQL

### Cambios en Código
- [ ] Actualizar `requirements.txt`
- [ ] Cambiar configuración de BD en `app/__init__.py`
- [ ] Actualizar modelos con UUID
- [ ] Reemplazar todas las instancias de `ILIKE`
- [ ] Actualizar funciones de monitoreo
- [ ] Actualizar migraciones SQL

### Migración de Datos
- [ ] Exportar datos de PostgreSQL
- [ ] Convertir formato SQL
- [ ] Importar a MySQL
- [ ] Verificar integridad de datos

### Post-migración
- [ ] Pruebas unitarias
- [ ] Pruebas de integración
- [ ] Verificar rendimiento
- [ ] Actualizar documentación
- [ ] Actualizar scripts de deploy

---

## 📚 RECURSOS

### Drivers MySQL para Python

1. **mysql-connector-python** (Oficial de Oracle)
   - Pros: Oficial, completo
   - Contras: Más pesado

2. **PyMySQL** (Pure Python)
   - Pros: Ligero, fácil de instalar
   - Contras: Menos features

### Documentación

- [SQLAlchemy MySQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/mysql.html)
- [MySQL 8.0 Reference Manual](https://dev.mysql.com/doc/refman/8.0/en/)
- [Migrating from PostgreSQL to MySQL](https://dev.mysql.com/doc/refman/8.0/en/migrating-from-postgresql.html)

---

## 🎯 SIGUIENTE PASO

**Recomendación:** Empezar con Fase 1 (Preparación) y crear un entorno de prueba MySQL local para validar los cambios antes de migrar producción.

