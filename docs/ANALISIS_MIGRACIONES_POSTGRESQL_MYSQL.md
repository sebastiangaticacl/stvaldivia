# Análisis de Migraciones: PostgreSQL → MySQL

**Fecha:** 2025-12-25  
**Objetivo:** Identificar cambios necesarios para adaptar migraciones SQL a MySQL

---

## 📋 MIGRACIONES IDENTIFICADAS

### Migraciones Críticas (Crean Tablas)

1. **`2025_01_15_payment_intents.sql`**
   - Crea tabla `payment_intents`
   - Usa UUID, gen_random_uuid()
   - Usa COMMENT ON

2. **`2025_12_18_payment_agents.sql`**
   - Crea tabla `payment_agents`
   - Usa UUID, gen_random_uuid()
   - Usa COMMENT ON

### Migraciones de ALTER TABLE

3. **`2025_01_15_bimba_cajas_mvp1_paymentstack.sql`**
   - ALTER TABLE pos_registers
   - ALTER TABLE register_sessions
   - Usa DO $$ blocks
   - Usa ARRAY en validaciones

4. **`2025_01_15_bimba_pos_payment_provider.sql`**
   - ALTER TABLE pos_sales
   - Usa DO $$ blocks
   - Usa ILIKE

5. **`2025_01_15_add_is_test_to_pos_registers.sql`**
   - ALTER TABLE pos_registers
   - Usa BOOLEAN
   - Usa COMMENT ON

6. **`2025_12_17_add_is_test_to_products.sql`**
   - ALTER TABLE products
   - Usa BOOLEAN
   - Usa COMMENT ON

### Migraciones Legacy (Duplicadas)

7. **`add_cajas_mvp1_fields.sql`** (duplicado de #3)
8. **`add_payment_provider_fields.sql`** (duplicado de #3)

---

## 🔄 DIFERENCIAS POSTGRESQL → MYSQL

### 1. Tipos de Datos

| PostgreSQL | MySQL | Notas |
|------------|-------|-------|
| `UUID` | `CHAR(36)` o `VARCHAR(36)` | MySQL no tiene UUID nativo |
| `gen_random_uuid()` | `UUID()` o generar en Python | MySQL 8.0+ tiene UUID() |
| `BOOLEAN` | `TINYINT(1)` o `BOOLEAN` | MySQL 8.0+ soporta BOOLEAN |
| `TEXT` | `TEXT` o `LONGTEXT` | Compatible |
| `NUMERIC(10,2)` | `DECIMAL(10,2)` | Compatible |
| `TIMESTAMP` | `TIMESTAMP` o `DATETIME` | Compatible |
| `SERIAL` | `AUTO_INCREMENT INT` | PostgreSQL auto-increment |

### 2. Funciones Específicas

| PostgreSQL | MySQL | Solución |
|------------|-------|----------|
| `gen_random_uuid()` | `UUID()` | MySQL 8.0+ o generar en Python |
| `ILIKE` | `LOWER() LIKE` | Ya adaptado en código Python |
| `COMMENT ON TABLE/COLUMN` | `ALTER TABLE ... COMMENT` | Sintaxis diferente |
| `DO $$ ... END $$` | `DELIMITER // ... //` o lógica en Python | Procedimientos almacenados |

### 3. Índices Parciales

| PostgreSQL | MySQL | Solución |
|------------|-------|----------|
| `CREATE INDEX ... WHERE condition` | No soportado | Usar índices completos o lógica en aplicación |

### 4. Verificaciones

| PostgreSQL | MySQL | Solución |
|------------|-------|----------|
| `information_schema.columns` | `information_schema.columns` | Compatible (schema diferente) |
| `pg_indexes` | `information_schema.statistics` | Query diferente |
| `ARRAY` en DO blocks | No soportado | Usar tablas temporales o lógica en Python |

---

## ⚠️ PROBLEMAS IDENTIFICADOS

### 1. UUID como PRIMARY KEY

**PostgreSQL:**
```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**MySQL:**
```sql
id CHAR(36) PRIMARY KEY DEFAULT (UUID())
-- O mejor: generar en Python con str(uuid.uuid4())
```

### 2. Bloques DO $$ (PL/pgSQL)

**PostgreSQL:**
```sql
DO $$
BEGIN
    UPDATE table SET col = 'value' WHERE col IS NULL;
END $$;
```

**MySQL:**
```sql
-- Opción 1: Procedimiento almacenado
DELIMITER //
CREATE PROCEDURE update_defaults()
BEGIN
    UPDATE table SET col = 'value' WHERE col IS NULL;
END //
DELIMITER ;
CALL update_defaults();
DROP PROCEDURE update_defaults;

-- Opción 2: Ejecutar directamente (más simple)
UPDATE table SET col = 'value' WHERE col IS NULL;
```

### 3. COMMENT ON

**PostgreSQL:**
```sql
COMMENT ON TABLE payment_intents IS 'Descripción';
COMMENT ON COLUMN payment_intents.status IS 'Descripción';
```

**MySQL:**
```sql
ALTER TABLE payment_intents COMMENT = 'Descripción';
ALTER TABLE payment_intents MODIFY COLUMN status VARCHAR(20) COMMENT 'Descripción';
```

### 4. Índices Parciales

**PostgreSQL:**
```sql
CREATE INDEX idx_payment_intents_pending 
ON payment_intents(register_id, status, created_at) 
WHERE status IN ('READY', 'IN_PROGRESS');
```

**MySQL:**
```sql
-- No soportado directamente, usar índice completo
CREATE INDEX idx_payment_intents_pending 
ON payment_intents(register_id, status, created_at);
-- La condición WHERE se aplica en queries, no en índice
```

### 5. Validaciones con ARRAY

**PostgreSQL:**
```sql
DO $$
DECLARE
    required_cols TEXT[] := ARRAY['col1', 'col2', 'col3'];
BEGIN
    FOREACH col_name IN ARRAY required_cols
    LOOP
        -- validar
    END LOOP;
END $$;
```

**MySQL:**
```sql
-- No soportado, usar lógica en Python o validar manualmente
-- O crear procedimiento almacenado complejo
```

### 6. ILIKE en Migraciones

**PostgreSQL:**
```sql
WHERE payment_type ILIKE '%efectivo%'
```

**MySQL:**
```sql
WHERE LOWER(payment_type) LIKE '%efectivo%'
```

---

## 📝 PLAN DE ADAPTACIÓN

### Fase 1: Migraciones Críticas (Crean Tablas)

1. ✅ `payment_intents.sql` → `payment_intents_mysql.sql`
2. ✅ `payment_agents.sql` → `payment_agents_mysql.sql`

### Fase 2: Migraciones ALTER TABLE

3. ✅ `bimba_cajas_mvp1_paymentstack.sql` → `bimba_cajas_mvp1_paymentstack_mysql.sql`
4. ✅ `bimba_pos_payment_provider.sql` → `bimba_pos_payment_provider_mysql.sql`
5. ✅ `add_is_test_to_pos_registers.sql` → `add_is_test_to_pos_registers_mysql.sql`
6. ✅ `add_is_test_to_products.sql` → `add_is_test_to_products_mysql.sql`

### Fase 3: Limpieza

7. ⚠️ Identificar y eliminar duplicados:
   - `add_cajas_mvp1_fields.sql` (duplicado)
   - `add_payment_provider_fields.sql` (duplicado)

---

## ✅ CHECKLIST DE CONVERSIÓN

Para cada migración, verificar:

- [ ] UUID → CHAR(36) o VARCHAR(36)
- [ ] gen_random_uuid() → UUID() o eliminar default (generar en Python)
- [ ] BOOLEAN → TINYINT(1) o BOOLEAN (MySQL 8.0+)
- [ ] COMMENT ON → ALTER TABLE ... COMMENT
- [ ] DO $$ blocks → Procedimientos o queries directas
- [ ] ILIKE → LOWER() LIKE
- [ ] Índices parciales → Índices completos
- [ ] ARRAY en validaciones → Lógica en Python o eliminar
- [ ] information_schema queries → Adaptar para MySQL
- [ ] pg_indexes → information_schema.statistics

---

**Próximo paso:** Crear versiones MySQL de las migraciones críticas.

