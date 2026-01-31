"""
Servicio para sincronizar datos entre ambientes (producción y local)
"""
import os
import subprocess
import threading
import shutil
from datetime import datetime
from flask import current_app
from sqlalchemy import create_engine, text
import sqlite3

# Tablas a sincronizar (en orden de dependencias)
TABLES_TO_SYNC = [
    {
        'name': 'employees',
        'description': 'Empleados',
        'icon': '👥',
        'order_by': 'name',
        'where': 'is_active = true'
    },
    {
        'name': 'cargos',
        'description': 'Cargos',
        'icon': '💼',
        'order_by': 'nombre'
    },
    {
        'name': 'cargo_salary_configs',
        'description': 'Configuración de Salarios',
        'icon': '💰',
        'order_by': 'cargo'
    },
    {
        'name': 'jornadas',
        'description': 'Jornadas',
        'icon': '📅',
        'order_by': 'fecha_jornada DESC',
        'limit': 50
    },
    {
        'name': 'planilla_trabajadores',
        'description': 'Planilla de Trabajadores',
        'icon': '📋',
        'order_by': 'jornada_id DESC, nombre_empleado',
        'limit': 500
    },
    {
        'name': 'guardarropia_items',
        'description': 'Guardarropía',
        'icon': '🧥',
        'order_by': 'deposited_at DESC'
    },
    {
        'name': 'register_closes',
        'description': 'Cierres de Caja',
        'icon': '💵',
        'order_by': 'fecha_cierre DESC',
        'limit': 100
    },
    {
        'name': 'notifications',
        'description': 'Notificaciones',
        'icon': '🔔',
        'order_by': 'created_at DESC',
        'limit': 200
    }
]

# Estado global de sincronización
_sync_status = {
    'running': False,
    'progress': {},
    'current_table': None,
    'start_time': None,
    'end_time': None,
    'error': None,
    'results': {}
}

def get_sync_status():
    """Obtiene el estado actual de la sincronización"""
    return _sync_status.copy()

def is_sync_running():
    """Verifica si hay una sincronización en curso"""
    return _sync_status['running']

def create_backup(local_db_path, instance_path):
    """
    Crea un backup de la base de datos local antes de sincronizar.
    
    Args:
        local_db_path: Ruta completa a la base de datos local
        instance_path: Ruta del directorio instance
    
    Returns:
        dict: {'success': bool, 'backup_path': str, 'error': str}
    """
    try:
        # Crear directorio de backups si no existe
        backups_dir = os.path.join(instance_path, 'backups')
        os.makedirs(backups_dir, exist_ok=True)
        
        # Generar nombre de backup con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'bimba_backup_{timestamp}.db'
        backup_path = os.path.join(backups_dir, backup_filename)
        
        # Copiar la base de datos
        shutil.copy2(local_db_path, backup_path)
        
        # Verificar que el backup se creó correctamente
        if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
            # Limpiar backups antiguos (mantener solo los últimos 10)
            cleanup_old_backups(backups_dir, keep_last=10)
            
            return {
                'success': True,
                'backup_path': backup_path,
                'backup_size': os.path.getsize(backup_path),
                'timestamp': timestamp
            }
        else:
            return {
                'success': False,
                'error': 'El backup se creó pero el archivo está vacío o no existe'
            }
            
    except Exception as e:
        error_msg = f"Error al crear backup: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }

def cleanup_old_backups(backups_dir, keep_last=10):
    """
    Elimina backups antiguos, manteniendo solo los últimos N.
    
    Args:
        backups_dir: Directorio donde están los backups
        keep_last: Número de backups a mantener
    """
    try:
        # Obtener todos los archivos de backup
        backup_files = []
        for filename in os.listdir(backups_dir):
            if filename.startswith('bimba_backup_') and filename.endswith('.db'):
                filepath = os.path.join(backups_dir, filename)
                backup_files.append({
                    'path': filepath,
                    'name': filename,
                    'mtime': os.path.getmtime(filepath)
                })
        
        # Ordenar por fecha de modificación (más recientes primero)
        backup_files.sort(key=lambda x: x['mtime'], reverse=True)
        
        # Eliminar los más antiguos si hay más de keep_last
        if len(backup_files) > keep_last:
            for old_backup in backup_files[keep_last:]:
                try:
                    os.remove(old_backup['path'])
                    print(f"🗑️  Backup antiguo eliminado: {old_backup['name']}")
                except Exception as e:
                    print(f"⚠️  No se pudo eliminar backup {old_backup['name']}: {e}")
                    
    except Exception as e:
        print(f"⚠️  Error al limpiar backups antiguos: {e}")

def sync_table(prod_conn, local_conn, table_config, progress_callback=None):
    """Sincroniza una tabla específica"""
    table_name = table_config['name']
    description = table_config.get('description', table_name)
    icon = table_config.get('icon', '📦')
    order_by = table_config.get('order_by', 'id')
    where_clause = table_config.get('where', '1=1')
    limit = table_config.get('limit')
    
    try:
        # Actualizar estado
        _sync_status['current_table'] = table_name
        if progress_callback:
            progress_callback(table_name, 'iniciando', 0)
        
        # Construir query
        query = f"SELECT * FROM {table_name} WHERE {where_clause} ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        
        # Obtener datos de producción
        result = prod_conn.execute(text(query))
        rows = result.fetchall()
        
        if len(rows) == 0:
            result_data = {'inserted': 0, 'updated': 0, 'total': 0, 'status': 'empty'}
            if progress_callback:
                progress_callback(table_name, 'completado', 0)
            return result_data
        
        # Obtener nombres de columnas
        columns = [desc[0] for desc in result.description]
        columns_str = ','.join(columns)
        placeholders = ','.join(['?' for _ in columns])
        
        local_cursor = local_conn.cursor()
        
        # Contar registros en local antes
        local_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        local_count_before = local_cursor.fetchone()[0]
        
        inserted = 0
        updated = 0
        total_rows = len(rows)
        
        for idx, row in enumerate(rows):
            # Convertir row a tupla
            row_tuple = tuple(row)
            
            # Actualizar progreso
            if progress_callback and idx % 10 == 0:
                progress = int((idx / total_rows) * 100)
                progress_callback(table_name, 'procesando', progress)
            
            # Verificar si existe
            if 'id' in columns:
                id_index = columns.index('id')
                id_value = row_tuple[id_index]
                local_cursor.execute(f'SELECT id FROM {table_name} WHERE id = ?', (id_value,))
                exists = local_cursor.fetchone()
                
                if exists:
                    # Actualizar
                    set_clause = ','.join([f'{col} = ?' for col in columns])
                    update_query = f'UPDATE {table_name} SET {set_clause} WHERE id = ?'
                    local_cursor.execute(update_query, row_tuple + (id_value,))
                    updated += 1
                else:
                    # Insertar
                    insert_query = f'INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})'
                    local_cursor.execute(insert_query, row_tuple)
                    inserted += 1
            else:
                # Si no hay columna 'id', solo insertar
                insert_query = f'INSERT OR REPLACE INTO {table_name} ({columns_str}) VALUES ({placeholders})'
                local_cursor.execute(insert_query, row_tuple)
                inserted += 1
        
        local_conn.commit()
        
        # Contar después
        local_cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        local_count_after = local_cursor.fetchone()[0]
        
        result_data = {
            'inserted': inserted,
            'updated': updated,
            'total': total_rows,
            'local_before': local_count_before,
            'local_after': local_count_after,
            'status': 'success'
        }
        
        if progress_callback:
            progress_callback(table_name, 'completado', 100)
        
        return result_data
        
    except Exception as e:
        error_msg = str(e)
        current_app.logger.error(f"Error al sincronizar {table_name}: {error_msg}")
        if progress_callback:
            progress_callback(table_name, 'error', 0)
        return {'error': error_msg, 'status': 'error'}

def sync_all_data_async():
    """Sincroniza todos los datos de forma asíncrona"""
    # Verificar que NO estamos en producción
    is_cloud_run = bool(os.environ.get('K_SERVICE') or os.environ.get('GAE_ENV') or os.environ.get('CLOUD_RUN_SERVICE'))
    is_production = os.environ.get('FLASK_ENV', '').lower() == 'production' or is_cloud_run
    
    if is_production:
        return {
            'success': False,
            'error': 'La sincronización solo está disponible en el ambiente local. En producción no se usan archivos locales.'
        }
    
    if _sync_status['running']:
        return {'success': False, 'error': 'Ya hay una sincronización en curso'}

    # Obtener instance_path ANTES de crear el thread (cuando tenemos acceso a current_app)
    instance_path = None
    try:
        from flask import has_app_context
        if has_app_context() and current_app:
            instance_path = current_app.config.get('INSTANCE_PATH')
    except:
        pass
    
    # Si no hay contexto o no hay instance_path, usar ruta por defecto
    if not instance_path:
        instance_path = 'instance'
    
    # Verificar que la base de datos local existe antes de iniciar
    local_db = os.path.join(instance_path, "bimba.db")
    if not os.path.exists(local_db):
        return {
            'success': False,
            'error': f'Base de datos local no encontrada: {local_db}'
        }

    def run_sync(instance_path_param):
        try:
            _sync_status['running'] = True
            _sync_status['start_time'] = datetime.now().isoformat()
            _sync_status['error'] = None
            _sync_status['results'] = {}
            _sync_status['progress'] = {}
            _sync_status['backup'] = None

            # Usar instance_path pasado como parámetro
            local_db = os.path.join(instance_path_param, "bimba.db")
            
            if not os.path.exists(local_db):
                error_msg = f"Base de datos local no encontrada: {local_db}"
                _sync_status['error'] = error_msg
                _sync_status['running'] = False
                print(f"❌ {error_msg}")
                return
            
            # Crear backup ANTES de sincronizar
            print("💾 Creando backup de la base de datos local...")
            backup_result = create_backup(local_db, instance_path_param)
            
            if backup_result['success']:
                _sync_status['backup'] = {
                    'path': backup_result['backup_path'],
                    'size': backup_result['backup_size'],
                    'timestamp': backup_result['timestamp']
                }
                print(f"✅ Backup creado: {backup_result['backup_path']} ({backup_result['backup_size']} bytes)")
            else:
                # No bloquear la sincronización si falla el backup, pero registrar el error
                print(f"⚠️  Advertencia: No se pudo crear backup: {backup_result.get('error', 'Error desconocido')}")
                _sync_status['backup'] = {'error': backup_result.get('error', 'Error desconocido')}

            # Eliminar fallback hardcodeado a PostgreSQL - requerir PROD_DATABASE_URL explícito
            prod_url = os.environ.get('PROD_DATABASE_URL', '').strip()
            
            if not prod_url:
                error_msg = "PROD_DATABASE_URL no configurado. Sincronización abortada."
                _sync_status['error'] = error_msg
                _sync_status['running'] = False
                print(f"⚠️  {error_msg}")
                try:
                    from flask import current_app
                    current_app.logger.warning("Sync blocked: PROD_DATABASE_URL missing")
                except:
                    pass
                return
            
            # Warning si local es MySQL y PROD_DATABASE_URL es postgresql (solo warning, no bloquear)
            try:
                from flask import current_app
                local_db_type = current_app.config.get('DB_TYPE', 'unknown')
                database_url = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
                is_local_mysql = (
                    local_db_type == 'mysql' or 
                    database_url.startswith('mysql') or 
                    'mysql+' in database_url
                )
                if is_local_mysql and prod_url.startswith('postgresql'):
                    current_app.logger.warning(
                        "Sync: BD local es MySQL pero PROD_DATABASE_URL apunta a PostgreSQL. "
                        "Verifica la configuración."
                    )
            except:
                pass

            try:
                prod_engine = create_engine(prod_url, connect_args={'connect_timeout': 10})
                prod_conn = prod_engine.connect()
            except Exception as e:
                error_msg = f"Error al conectar a producción: {str(e)}"
                _sync_status['error'] = error_msg
                _sync_status['running'] = False
                print(f"❌ Error al conectar a producción: {error_msg}")
                # Intentar loguear si hay contexto de Flask
                try:
                    from flask import current_app
                    current_app.logger.warning(
                        f"⚠️ Sincronización: Error de conexión a PROD_DATABASE_URL: {error_msg}"
                    )
                except:
                    pass  # Si no hay contexto de Flask, solo usar print
                return
            
            local_conn = sqlite3.connect(local_db)
            
            try:
                total_inserted = 0
                total_updated = 0
                tables_synced = 0
                total_tables = len(TABLES_TO_SYNC)
                
                def progress_callback(table_name, status, progress):
                    _sync_status['progress'][table_name] = {
                        'status': status,
                        'progress': progress
                    }
                
                # Sincronizar cada tabla
                for idx, table_config in enumerate(TABLES_TO_SYNC):
                    table_name = table_config['name']
                    # Log simple sin usar current_app (no disponible en thread)
                    print(f"Sincronizando {table_name} ({idx+1}/{total_tables})...")
                    
                    result = sync_table(prod_conn, local_conn, table_config, progress_callback)
                    
                    if 'error' not in result:
                        total_inserted += result.get('inserted', 0)
                        total_updated += result.get('updated', 0)
                        tables_synced += 1
                        _sync_status['results'][table_name] = result
                    else:
                        _sync_status['results'][table_name] = result
                
                _sync_status['results']['summary'] = {
                    'tables_synced': tables_synced,
                    'total_tables': total_tables,
                    'total_inserted': total_inserted,
                    'total_updated': total_updated,
                    'total_changes': total_inserted + total_updated
                }
                
                _sync_status['end_time'] = datetime.now().isoformat()
                _sync_status['running'] = False
                
                # Log simple sin usar current_app (no disponible en thread)
                print(f"✅ Sincronización completada: {tables_synced} tablas, {total_inserted + total_updated} cambios")
                
            except Exception as e:
                error_msg = f"Error durante la sincronización: {str(e)}"
                _sync_status['error'] = error_msg
                _sync_status['running'] = False
                # Log simple sin usar current_app (no disponible en thread)
                print(f"❌ Error durante la sincronización: {error_msg}")
                import traceback
                traceback.print_exc()
                local_conn.rollback()
            finally:
                local_conn.close()
                prod_conn.close()
                prod_engine.dispose()
        
        except Exception as e:
            error_msg = f"Error crítico en sincronización: {str(e)}"
            _sync_status['error'] = error_msg
            _sync_status['running'] = False
            print(f"❌ Error crítico en sincronización: {error_msg}")
            import traceback
            traceback.print_exc()
    
    # Ejecutar en thread separado, pasando instance_path como parámetro
    thread = threading.Thread(target=run_sync, args=(instance_path,), daemon=True)
    thread.start()
    
    return {'success': True, 'message': 'Sincronización iniciada'}

def get_available_tables():
    """Obtiene la lista de tablas disponibles para sincronizar"""
    return TABLES_TO_SYNC.copy()






