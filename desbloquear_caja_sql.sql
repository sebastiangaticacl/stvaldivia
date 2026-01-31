-- Script SQL para desbloquear la caja TEST001 (register_id = '1')
-- Ejecutar en producción: psql -U postgres -d bimba_db -f desbloquear_caja_sql.sql

DELETE FROM register_locks 
WHERE register_id = '1';

-- Verificar que se eliminó
SELECT * FROM register_locks WHERE register_id = '1';






