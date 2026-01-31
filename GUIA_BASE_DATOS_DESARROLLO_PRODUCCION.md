# Guía: Usar Base de Datos de Producción en Desarrollo Local

## ⚠️ ADVERTENCIAS IMPORTANTES

**NO es recomendable usar la base de datos de producción directamente en desarrollo** porque:
- Puedes corromper datos reales
- Puedes afectar usuarios en producción
- Puedes causar problemas de rendimiento
- Puedes borrar datos accidentalmente

**MEJOR PRÁCTICA:** Usar una copia de la base de datos de producción para desarrollo.

---

## 📋 Opciones Recomendadas

### Opción 1: Base de Datos de Desarrollo Separada (RECOMENDADO)

Crear una base de datos MySQL separada para desarrollo local.

**Ventajas:**
- ✅ No afecta producción
- ✅ Puedes experimentar sin miedo
- ✅ Puedes resetear cuando quieras

**Configuración:**

1. Crear base de datos de desarrollo:
```bash
mysql -u root -p
CREATE DATABASE bimba_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

2. Configurar en `.env`:
```bash
# Desarrollo local
DATABASE_URL=mysql://usuario:password@localhost:3306/bimba_dev
FLASK_ENV=development
```

3. Sincronizar datos desde producción (opcional):
```bash
# Exportar desde producción
mysqldump -h [host_produccion] -u [usuario] -p bimba_prod > backup_prod.sql

# Importar a desarrollo
mysql -u root -p bimba_dev < backup_prod.sql
```

---

### Opción 2: Usar Base de Datos de Producción (CON PRECAUCIÓN)

Si realmente necesitas usar la base de datos de producción:

**⚠️ REQUISITOS:**
1. Solo lectura (recomendado)
2. Conexión segura (VPN/SSH tunnel)
3. Backup antes de cualquier cambio
4. Usar con mucho cuidado

**Configuración:**

1. Crear archivo `.env.production` (NO commitear):
```bash
# Base de datos de PRODUCCIÓN (solo lectura recomendado)
DATABASE_URL=mysql://usuario:password@[host_produccion]:3306/bimba_prod
FLASK_ENV=development
FLASK_DEBUG=True
```

2. Usar script para cambiar entre bases de datos:
```bash
# Activar base de datos de producción
source scripts/use_prod_db.sh

# Volver a desarrollo
source scripts/use_dev_db.sh
```

---

### Opción 3: Base de Datos de Staging/Testing

Crear una base de datos intermedia para pruebas antes de producción.

**Configuración:**
```bash
# Base de datos de staging
DATABASE_URL=mysql://usuario:password@[host_staging]:3306/bimba_staging
FLASK_ENV=development
```

---

## 🔧 Scripts de Utilidad

### Script 1: Cambiar entre Bases de Datos

Crear `scripts/switch_database.sh`:

```bash
#!/bin/bash
# Script para cambiar entre bases de datos

case "$1" in
  prod)
    echo "⚠️  ADVERTENCIA: Conectando a PRODUCCIÓN"
    export DATABASE_URL="mysql://usuario:password@[host_prod]:3306/bimba_prod"
    echo "✅ Base de datos: PRODUCCIÓN"
    ;;
  dev)
    export DATABASE_URL="mysql://usuario:password@localhost:3306/bimba_dev"
    echo "✅ Base de datos: DESARROLLO"
    ;;
  local)
    unset DATABASE_URL
    echo "✅ Base de datos: SQLite (local)"
    ;;
  *)
    echo "Uso: $0 {prod|dev|local}"
    exit 1
    ;;
esac
```

### Script 2: Backup de Base de Datos

Crear `scripts/backup_database.sh`:

```bash
#!/bin/bash
# Script para hacer backup de la base de datos actual

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups"
mkdir -p $BACKUP_DIR

# Detectar tipo de base de datos desde .env
source .env 2>/dev/null || true

if [[ $DATABASE_URL == mysql* ]]; then
    # Extraer credenciales de DATABASE_URL
    # mysql://usuario:password@host:port/database
    DB_URL=${DATABASE_URL#mysql://}
    DB_CREDS=${DB_URL%@*}
    DB_HOST_PORT=${DB_URL#*@}
    DB_HOST=${DB_HOST_PORT%:*}
    DB_PORT=${DB_HOST_PORT#*:}
    DB_NAME=${DB_PORT#*/}
    
    echo "📦 Haciendo backup de MySQL..."
    mysqldump -h $DB_HOST -P ${DB_PORT%%/*} -u ${DB_CREDS%:*} -p${DB_CREDS#*:} $DB_NAME > "$BACKUP_DIR/backup_${TIMESTAMP}.sql"
    echo "✅ Backup guardado en: $BACKUP_DIR/backup_${TIMESTAMP}.sql"
else
    echo "⚠️  Solo MySQL soportado para backup automático"
fi
```

---

## 📝 Configuración Recomendada

### Archivo `.env` (Desarrollo Local)

```bash
# Base de datos de DESARROLLO
DATABASE_URL=mysql://bimba_user:password@localhost:3306/bimba_dev

# Entorno
FLASK_ENV=development
FLASK_DEBUG=True

# Secret Key (diferente a producción)
SECRET_KEY=tu_secret_key_desarrollo
```

### Archivo `.env.production` (NO commitear)

```bash
# Base de datos de PRODUCCIÓN (solo para emergencias)
DATABASE_URL=mysql://usuario:password@[host_prod]:3306/bimba_prod

# Entorno
FLASK_ENV=development
FLASK_DEBUG=True

# ⚠️ ADVERTENCIA: Estás conectado a PRODUCCIÓN
```

---

## 🚀 Uso Rápido

### Desarrollo Normal (Base de Datos Local)
```bash
# .env ya configurado para desarrollo
python3 run_local.py
```

### Conectar a Producción (Solo Lectura)
```bash
# 1. Hacer backup primero
./scripts/backup_database.sh

# 2. Cambiar a producción
export DATABASE_URL="mysql://usuario:password@[host]:3306/bimba_prod"

# 3. Ejecutar en modo solo lectura (recomendado)
FLASK_ENV=development python3 run_local.py
```

### Volver a Desarrollo
```bash
# Restaurar .env original
export DATABASE_URL="mysql://usuario:password@localhost:3306/bimba_dev"
```

---

## ✅ Checklist Antes de Usar Producción

- [ ] Backup completo de la base de datos
- [ ] Conexión segura (VPN/SSH tunnel)
- [ ] Modo solo lectura (si es posible)
- [ ] Notificar al equipo
- [ ] Tener plan de rollback
- [ ] Documentar cambios realizados

---

## 🔒 Seguridad

1. **Nunca commitear** archivos `.env` con credenciales de producción
2. **Usar variables de entorno** del sistema cuando sea posible
3. **Rotar credenciales** regularmente
4. **Auditar accesos** a la base de datos de producción
5. **Usar permisos limitados** (solo lectura si es posible)

---

## 📞 Soporte

Si necesitas ayuda configurando las bases de datos, consulta:
- `INSTRUCCIONES_CONFIGURAR_MYSQL.md`
- `DEPLOY_CLOUD_RUN_COMPLETO.md`



