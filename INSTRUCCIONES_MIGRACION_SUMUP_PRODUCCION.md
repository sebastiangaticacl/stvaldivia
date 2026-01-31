# 📋 Instrucciones: Ejecutar Migración SumUp en Producción

## 🎯 Objetivo

Ejecutar la migración para agregar campos SumUp a la tabla `pagos` en la base de datos de producción.

---

## 📊 Información de Base de Datos

```
DATABASE_URL: mysql+mysqlconnector://bimba_user:a0LVWyEuWwZ0WDg2CL3bGmGY4@localhost:3306/bimba_db
Base de datos: bimba_db
Tabla: pagos
```

---

## 🚀 Método 1: Ejecutar desde el Servidor de Producción (RECOMENDADO)

### Paso 1: Conectarse al Servidor

```bash
ssh usuario@servidor
cd /ruta/al/proyecto
```

### Paso 2: Ejecutar Migración SQL Directa

```bash
mysql -u bimba_user -p bimba_db < migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql
# Cuando pida password, ingresar: a0LVWyEuWwZ0WDg2CL3bGmGY4
```

### Paso 3: Verificar Migración

```bash
mysql -u bimba_user -p bimba_db -e "DESCRIBE pagos" | grep sumup
```

Debes ver:
- `sumup_checkout_id`
- `sumup_checkout_url`
- `sumup_merchant_code`

---

## 🚀 Método 2: Usar Script Python en el Servidor

### Paso 1: Subir archivos al servidor

```bash
# Desde tu máquina local
scp ejecutar_migracion_sumup_produccion.py usuario@servidor:/ruta/al/proyecto/
scp migrations/2025_01_15_add_sumup_fields_to_pagos_mysql.sql usuario@servidor:/ruta/al/proyecto/migrations/
```

### Paso 2: Ejecutar en el servidor

```bash
ssh usuario@servidor
cd /ruta/al/proyecto
python3 ejecutar_migracion_sumup_produccion.py
```

---

## 🚀 Método 3: Ejecutar SQL Manualmente

Si prefieres ejecutar las sentencias SQL directamente:

```sql
USE bimba_db;

-- Verificar si los campos ya existen
DESCRIBE pagos;

-- Agregar campo sumup_checkout_id (si no existe)
ALTER TABLE pagos 
ADD COLUMN sumup_checkout_id VARCHAR(100) NULL COMMENT 'ID del checkout de SumUp';

-- Agregar campo sumup_checkout_url (si no existe)
ALTER TABLE pagos 
ADD COLUMN sumup_checkout_url TEXT NULL COMMENT 'URL del checkout de SumUp para generar QR';

-- Agregar campo sumup_merchant_code (si no existe)
ALTER TABLE pagos 
ADD COLUMN sumup_merchant_code VARCHAR(50) NULL COMMENT 'Código del comerciante SumUp';

-- Crear índice (si no existe)
CREATE INDEX idx_pagos_sumup_checkout_id ON pagos (sumup_checkout_id);

-- Verificar resultado
DESCRIBE pagos;
```

**Nota:** Si algún campo ya existe, MySQL mostrará un error "Duplicate column name", lo cual es seguro ignorar.

---

## ✅ Verificación Post-Migración

### Verificar campos agregados:

```sql
DESCRIBE pagos;
```

Debes ver las columnas:
- `sumup_checkout_id` VARCHAR(100)
- `sumup_checkout_url` TEXT
- `sumup_merchant_code` VARCHAR(50)

### Verificar índice:

```sql
SHOW INDEX FROM pagos WHERE Key_name = 'idx_pagos_sumup_checkout_id';
```

---

## 🔧 Troubleshooting

### Error: "Access denied"

- Verificar que las credenciales sean correctas
- Verificar que el usuario `bimba_user` tenga permisos ALTER en la tabla `pagos`

### Error: "Duplicate column name"

- Es seguro ignorar si el campo ya existe
- La migración está diseñada para ser idempotente

### Error: "Table 'pagos' doesn't exist"

- Verificar que estés en la base de datos correcta: `USE bimba_db;`
- Verificar que la tabla existe: `SHOW TABLES;`

---

## 📝 Notas Importantes

1. **Backup:** Se recomienda hacer backup antes de ejecutar migraciones:
   ```bash
   mysqldump -u bimba_user -p bimba_db > backup_bimba_db_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Idempotencia:** La migración SQL usa procedimientos que verifican si los campos ya existen antes de agregarlos, por lo que es seguro ejecutarla múltiples veces.

3. **Sin pérdida de datos:** Esta migración solo AGREGA campos nuevos (NULL permitido), no modifica ni elimina datos existentes.

---

## ✅ Checklist

- [ ] Backup de base de datos realizado
- [ ] Conectado al servidor de producción
- [ ] Migración ejecutada
- [ ] Campos verificados en tabla `pagos`
- [ ] Índice verificado
- [ ] Sistema probado con nueva funcionalidad

---

**Última actualización:** 2025-01-15

