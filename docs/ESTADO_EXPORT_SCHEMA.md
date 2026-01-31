# Estado de Exportación de Esquema PostgreSQL

**Fecha:** 2025-12-25  
**Estado:** ⚠️ Preparado pero no ejecutado

## Situación Actual

- **Entorno local:** SQLite (`instance/bimba.db`)
- **PostgreSQL:** No detectado en entorno local
- **Archivo `.env`:** No encontrado en `/var/www/stvaldivia/.env`
- **Herramientas:** `psql` y `pg_dump` no encontradas en PATH

## Archivos Preparados

✅ **Script automático:** `scripts/export_postgres_schema.sh`
✅ **Documentación:** `docs/INSTRUCCIONES_EXPORT_SCHEMA.md`
✅ **Comandos exactos:** `docs/COMANDOS_EXPORT_SCHEMA.md`

## Para Ejecutar

Cuando tengas acceso a PostgreSQL:

```bash
cd /Users/sebagatica/stvaldivia
./scripts/export_postgres_schema.sh
```

O seguir comandos manuales en `docs/COMANDOS_EXPORT_SCHEMA.md`

## Archivos que se Generarán

1. `docs/SCHEMA_REAL.sql` - Dump schema-only
2. `docs/TABLES_ROWCOUNT.md` - Tablas con conteo
3. `docs/FKS_REAL.md` - Foreign Keys reales
4. `docs/INDEXES_REAL.md` - Índices por tabla

