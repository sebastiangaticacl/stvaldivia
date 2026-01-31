# Configuración de Bases de Datos en Servidor VM de Google

## 📋 Resumen

Este sistema permite cambiar entre base de datos de **desarrollo** y **producción** desde el panel de control, tipo "debug mode". Ambas bases de datos se guardan en el servidor VM de Google.

## 🔧 Configuración Inicial

### Paso 1: Configurar Variables de Entorno en el Servidor VM

En el servidor VM de Google, edita el archivo de configuración del servicio (systemd, gunicorn, etc.) o el archivo `.env`:

```bash
# Base de datos de PRODUCCIÓN
DATABASE_PROD_URL=mysql://usuario:password@[host_prod]:3306/bimba_prod

# Base de datos de DESARROLLO  
DATABASE_DEV_URL=mysql://usuario:password@[host_dev]:3306/bimba_dev

# Modo inicial (prod o dev)
DATABASE_MODE=prod
```

**Ejemplo concreto:**
```bash
DATABASE_PROD_URL=mysql://bimba_user:password123@10.0.0.5:3306/bimba_prod
DATABASE_DEV_URL=mysql://bimba_user:password123@10.0.0.5:3306/bimba_dev
DATABASE_MODE=prod
```

### Paso 2: Ejecutar Migración

Ejecuta el script de migración para crear la tabla de configuración:

```bash
python3 migrate_system_config.py
```

Esto creará la tabla `system_config` y guardará las URLs desde las variables de entorno.

### Paso 3: Reiniciar la Aplicación

Después de configurar las variables de entorno, reinicia la aplicación:

```bash
# Si usas systemd
sudo systemctl restart bimba

# Si usas gunicorn directamente
pkill -f gunicorn
# Luego inicia nuevamente
```

## 🎮 Uso del Toggle en el Panel de Control

1. **Acceder al Panel de Control:**
   - Ve a `/admin/panel_control`
   - Solo visible para superadmin (sebagatica)

2. **Ver Estado Actual:**
   - La tarjeta "Base de Datos" muestra el modo actual (DESARROLLO o PRODUCCIÓN)
   - Muestra la URL de la base de datos (con password oculto)

3. **Cambiar Modo:**
   - Click en "🧪 Desarrollo" para cambiar a base de datos de desarrollo
   - Click en "🚀 Producción" para cambiar a base de datos de producción
   - Se pedirá confirmación (especialmente al cambiar a producción)

4. **Reiniciar Aplicación:**
   - ⚠️ **IMPORTANTE:** Después de cambiar el modo, debes reiniciar la aplicación
   - El sistema mostrará un mensaje indicando que se requiere reinicio
   - Reinicia el servicio para que el cambio tome efecto

## 🔄 Flujo de Cambio

```
1. Usuario cambia modo en panel de control
   ↓
2. Sistema guarda preferencia en tabla system_config
   ↓
3. Sistema muestra mensaje: "Se requiere reiniciar"
   ↓
4. Administrador reinicia aplicación
   ↓
5. Al iniciar, la app lee DATABASE_MODE desde variables de entorno
   ↓
6. Si hay modo guardado diferente, usa el guardado (prioridad)
   ↓
7. Conecta a la base de datos correspondiente
```

## 📝 Notas Importantes

### Seguridad

- ⚠️ Solo el superadmin puede cambiar la base de datos
- ⚠️ Todos los cambios se registran en logs de auditoría
- ⚠️ Al cambiar a producción, se muestra advertencia de confirmación

### Reinicio Requerido

- **El cambio NO es inmediato** - requiere reinicio de la aplicación
- Esto es por seguridad y para evitar problemas de conexión
- El sistema mostrará claramente cuando se requiere reinicio

### Variables de Entorno vs Configuración Guardada

- **Variables de entorno** tienen prioridad al iniciar la aplicación
- **Configuración guardada** en la BD se usa si no hay variable de entorno
- Si cambias el modo desde el panel, se guarda en la BD
- Al reiniciar, la app lee desde variables de entorno primero

## 🛠️ Comandos Útiles

### Ver configuración actual
```bash
# En el servidor VM
python3 -c "from app import create_app; from app.helpers.database_config_helper import get_current_database_info; app = create_app(); app.app_context().push(); print(get_current_database_info())"
```

### Cambiar modo manualmente (sin panel)
```bash
# Editar variable de entorno
export DATABASE_MODE=dev  # o prod
# Reiniciar aplicación
```

### Ver logs de cambios
```sql
-- En la base de datos
SELECT * FROM audit_logs WHERE action = 'change_database_mode' ORDER BY timestamp DESC;
```

## 🔍 Troubleshooting

### El toggle no aparece
- Verifica que estés logueado como superadmin (sebagatica)
- Verifica que la tabla `system_config` existe

### El cambio no funciona
- Verifica que las variables `DATABASE_DEV_URL` y `DATABASE_PROD_URL` estén configuradas
- Verifica que reiniciaste la aplicación después del cambio
- Revisa los logs de la aplicación

### Error de conexión
- Verifica que ambas bases de datos existan y sean accesibles
- Verifica credenciales en las URLs
- Verifica firewall/red en el servidor VM

## 📊 Estructura de la Configuración

La configuración se guarda en la tabla `system_config`:

```sql
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description VARCHAR(500),
    updated_at DATETIME NOT NULL,
    updated_by VARCHAR(200)
);
```

**Claves usadas:**
- `database_mode`: 'dev' o 'prod'
- `database_dev_url`: URL de base de datos de desarrollo
- `database_prod_url`: URL de base de datos de producción



