# Resumen de Migración SQLite -> Cloud SQL PostgreSQL

## Estado Actual

✅ **Completado:**
- Instancia Cloud SQL PostgreSQL creada (`stvaldivia-db`)
- Base de datos `stvaldivia` creada
- Usuario `stvaldivia_user` creado
- Cloud SQL Auth Proxy instalado y configurado
- PostgreSQL local detenido

❌ **Pendiente:**
- Permisos del service account de la VM para Cloud SQL
- Migración de datos con pgloader
- Actualización de DATABASE_URL
- Reinicio de la aplicación

## Problema Actual

El proxy no puede conectarse porque el service account de la VM (`632963240948-compute@developer.gserviceaccount.com`) no tiene los scopes necesarios para acceder a Cloud SQL.

**Error:** `ACCESS_TOKEN_SCOPE_INSUFFICIENT`

## Soluciones Posibles

### Opción 1: Usar credenciales de aplicación (Recomendado)
Configurar el proxy para usar credenciales de aplicación en lugar del service account de la VM.

### Opción 2: Modificar scopes de la VM
Recrear la VM con los scopes necesarios (requiere downtime).

### Opción 3: Usar clave de service account
Crear una clave de service account y configurar el proxy para usarla.

## Próximos Pasos

1. Configurar credenciales de aplicación en la VM
2. Reiniciar el proxy
3. Ejecutar migración con pgloader
4. Actualizar DATABASE_URL
5. Reiniciar aplicación
