# 🚀 Guía: Ejecutar Migración SumUp

## 📋 Resumen

Migración para agregar campos SumUp a la tabla `pagos`:
- `sumup_checkout_id` VARCHAR(100)
- `sumup_checkout_url` TEXT
- `sumup_merchant_code` VARCHAR(50)
- Índice: `idx_pagos_sumup_checkout_id`

---

## 🎯 Opción 1: Script Python (Recomendado)

### En Desarrollo Local (SQLite)
```bash
python3 migrate_sumup_fields.py
```

### En Producción (MySQL)
```bash
# Asegurarse de tener DATABASE_URL configurado
export DATABASE_URL="mysql+mysqlconnector://bimba_user:password@localhost:3306/bimba_db"
python3 migrate_sumup_fields.py
```

**Ventajas:**
- ✅ Verificación automática de campos existentes
- ✅ Idempotente (se puede ejecutar múltiples veces)
- ✅ Detección automática de tipo de BD
- ✅ Verificación final de campos

---

## 🎯 Opción 2: SQL Directo Simple

### En Producción (MySQL)
```bash
mysql -u bimba_user -p bimba_db < migrations/2025_01_15_add_sumup_fields_to_pagos_simple.sql
```

**Nota:** Esta versión simple puede mostrar errores si los campos ya existen, pero es seguro ignorarlos.

---

## 🎯 Opción 3: SQL con Verificación (MySQL)

### En Producción (MySQL)
```bash
mysql -u bimba_user -p bimba_db < migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql
```

**Ventajas:**
- ✅ Verifica si los campos existen antes de agregarlos
- ✅ Idempotente
- ✅ Sin errores si se ejecuta múltiples veces

---

## ✅ Verificación Post-Migración

### Verificar campos agregados:
```sql
DESCRIBE pagos;
```

Debes ver:
- `sumup_checkout_id`
- `sumup_checkout_url`
- `sumup_merchant_code`

### Verificar índice:
```sql
SHOW INDEX FROM pagos WHERE Key_name = 'idx_pagos_sumup_checkout_id';
```

### Usando Python:
```python
from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    inspector = db.inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('pagos')]
    print('Campos SumUp:', [c for c in columns if 'sumup' in c])
```

---

## 🔧 Troubleshooting

### Error: "Duplicate column name"
- ✅ Es seguro ignorar si el campo ya existe
- La migración está diseñada para ser idempotente

### Error: "Table 'pagos' doesn't exist"
- Verificar que la tabla existe: `SHOW TABLES;`
- Verificar que estás en la BD correcta: `SELECT DATABASE();`

### Error: "Access denied"
- Verificar credenciales de base de datos
- Verificar permisos del usuario: `GRANT ALTER ON bimba_db.pagos TO 'bimba_user'@'localhost';`

### SQLite no soporta COMMENT
- ✅ Normal en desarrollo local
- Los campos se agregan sin comentarios, pero funcionan correctamente

---

## 📝 Archivos Disponibles

1. **migrate_sumup_fields.py** - Script Python (recomendado)
   - Detecta tipo de BD automáticamente
   - Verificación completa
   - Idempotente

2. **migrations/2025_01_15_add_sumup_fields_to_pagos_simple.sql**
   - Versión SQL simple
   - Sin verificaciones
   - Más rápida pero puede mostrar errores si campos existen

3. **migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql**
   - Versión SQL con verificaciones
   - Idempotente usando procedimientos almacenados
   - Solo MySQL

---

## ✅ Recomendación

**Para desarrollo local:**
```bash
python3 migrate_sumup_fields.py
```

**Para producción (MySQL):**
```bash
# Opción A: Script Python (mejor)
export DATABASE_URL="mysql+mysqlconnector://bimba_user:password@localhost:3306/bimba_db"
python3 migrate_sumup_fields.py

# Opción B: SQL directo
mysql -u bimba_user -p bimba_db < migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql
```

---

**Última actualización:** 2025-01-15

