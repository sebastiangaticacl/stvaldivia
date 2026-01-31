# Instrucciones para Ejecutar Diagnóstico en Servidor Linux

## 📍 CONTEXTO

**Ubicación:** Servidor Linux en `/var/www/stvaldivia`  
**Objetivo:** Verificar estado real de PostgreSQL sin modificar nada

## 🚀 EJECUCIÓN

### Opción 1: Script Automático (Recomendado)

```bash
# En el servidor Linux
cd /var/www/stvaldivia
./scripts/diagnostico_db_servidor.sh
```

El script generará automáticamente: `docs/ESTADO_DB_REAL.md`

### Opción 2: Comandos Manuales

Si prefieres ejecutar comandos manualmente, copia y pega estos comandos en el servidor:

```bash
cd /var/www/stvaldivia
mkdir -p docs

# 1. Verificar .env
echo "=== 1. ARCHIVO .env ==="
ls -la .env
cat .env | grep "^DATABASE_URL="

# 2. Verificar psql
echo "=== 2. POSTGRESQL INSTALADO ==="
psql --version
which psql

# 3. Verificar servicio
echo "=== 3. SERVICIO POSTGRESQL ==="
systemctl status postgresql

# 4. Verificar puerto
echo "=== 4. PUERTO 5432 ==="
ss -lntp | grep 5432

# 5. Probar conexión
echo "=== 5. PRUEBA DE CONEXIÓN ==="
export $(grep "^DATABASE_URL=" .env | xargs)
psql "$DATABASE_URL" -c "SELECT 1;"

# 6. Verificar pg_dump
echo "=== 6. pg_dump ==="
which pg_dump
pg_dump --version
```

## 📄 SALIDA

Todos los resultados se guardarán en: **`docs/ESTADO_DB_REAL.md`**

El reporte incluirá:
- Estado del archivo `.env`
- Versión de PostgreSQL
- Estado del servicio
- Puerto escuchando
- Resultado de conexión
- Estado de `pg_dump`
- Información del sistema

## ⚠️ NOTAS

- **Solo lectura:** Todos los comandos son de solo lectura
- **No modifica:** No se cambia ninguna configuración
- **Requiere permisos:** Algunos comandos pueden requerir `sudo`

