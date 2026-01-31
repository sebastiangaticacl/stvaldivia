"""
Helper para monitoreo de base de datos (SQLite, MySQL, PostgreSQL)
Proporciona estadísticas detalladas de la base de datos
"""
from typing import Dict, Any, List
from flask import current_app
from app.models import db
from sqlalchemy import text


def get_database_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas completas de la base de datos PostgreSQL
    
    Returns:
        Dict con estadísticas de tamaño, conexiones, tablas, etc.
    """
    stats = {}
    
    # Obtener cada estadística de forma independiente para que un error no rompa todo
    try:
        stats['database_size'] = get_database_size()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo tamaño de DB: {e}")
        stats['database_size'] = {'size_pretty': 'N/A', 'size_bytes': 0, 'error': str(e)}
    
    try:
        stats['connection_stats'] = get_connection_stats()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo estadísticas de conexiones: {e}")
        stats['connection_stats'] = {
            'total': 0, 'active': 0, 'idle': 0, 'idle_in_transaction': 0,
            'max_connections': 0, 'usage_percent': 0, 'error': str(e)
        }
    
    try:
        stats['table_sizes'] = get_table_sizes()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo tamaños de tablas: {e}")
        stats['table_sizes'] = []
    
    try:
        stats['database_info'] = get_database_info()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo info de DB: {e}")
        stats['database_info'] = {'error': str(e)}
    
    try:
        stats['index_stats'] = get_index_stats()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo estadísticas de índices: {e}")
        stats['index_stats'] = {'error': str(e)}
    
    try:
        stats['connection_pool_stats'] = get_connection_pool_stats()
    except Exception as e:
        current_app.logger.warning(f"Error obteniendo estadísticas del pool: {e}")
        stats['connection_pool_stats'] = {'error': str(e)}
    
    return stats


def get_database_size() -> Dict[str, Any]:
    """Obtiene el tamaño total de la base de datos"""
    try:
        # Detectar tipo de BD
        db_url = str(db.engine.url)
        if 'sqlite' in db_url.lower():
            # Para SQLite, obtener tamaño del archivo
            try:
                import os
                db_path = db_url.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    size_pretty = f"{size_bytes / 1024 / 1024:.2f} MB"
                    return {'size_pretty': size_pretty, 'size_bytes': size_bytes}
                else:
                    return {'size_pretty': 'N/A', 'size_bytes': 0}
            except Exception as e:
                current_app.logger.warning(f"Error obteniendo tamaño SQLite: {e}")
                return {'size_pretty': 'N/A', 'size_bytes': 0}
        else:
            # PostgreSQL
            query = text("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size_pretty,
                    pg_database_size(current_database()) as size_bytes
            """)
            result = db.session.execute(query).fetchone()
            db.session.commit()  # Cerrar la transacción
            
            return {
                'size_pretty': result[0] if result else 'N/A',
                'size_bytes': result[1] if result else 0
            }
    except Exception as e:
        current_app.logger.warning(f"Error al obtener tamaño de DB: {e}")
        db.session.rollback()  # Asegurar rollback en caso de error
        return {'size_pretty': 'N/A', 'size_bytes': 0}


def get_connection_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de conexiones activas"""
    try:
        # Detectar tipo de BD
        db_url = str(db.engine.url)
        if 'sqlite' in db_url.lower():
            # SQLite no tiene estadísticas de conexiones como PostgreSQL
            return {
                'total': 1,
                'active': 1,
                'idle': 0,
                'idle_in_transaction': 0,
                'max_connections': 1,
                'usage_percent': 100
            }
        
        # PostgreSQL - Estadísticas generales de conexiones
        query = text("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
                max_conn as max_connections
            FROM pg_stat_activity, 
                 (SELECT setting::int as max_conn FROM pg_settings WHERE name = 'max_connections') mc
            WHERE datname = current_database()
            GROUP BY max_conn
        """)
        result = db.session.execute(query).fetchone()
        db.session.commit()  # Cerrar la transacción
        
        if result:
            return {
                'total': result[0],
                'active': result[1],
                'idle': result[2],
                'idle_in_transaction': result[3],
                'max_connections': result[4],
                'usage_percent': round((result[0] / result[4] * 100), 2) if result[4] > 0 else 0
            }
        else:
            return {
                'total': 0,
                'active': 0,
                'idle': 0,
                'idle_in_transaction': 0,
                'max_connections': 0,
                'usage_percent': 0
            }
    except Exception as e:
        current_app.logger.warning(f"Error al obtener estadísticas de conexiones: {e}")
        db.session.rollback()  # Asegurar rollback en caso de error
        # Retornar estructura completa con valores por defecto para evitar errores en el template
        return {
            'total': 0,
            'active': 0,
            'idle': 0,
            'idle_in_transaction': 0,
            'max_connections': 0,
            'usage_percent': 0,
            'error': str(e)
        }


def get_table_sizes(limit: int = 20) -> List[Dict[str, Any]]:
    """Obtiene las tablas más grandes ordenadas por tamaño"""
    try:
        # Detectar tipo de BD
        db_url = str(db.engine.url)
        if 'sqlite' in db_url.lower():
            # Para SQLite, obtener lista de tablas
            query = text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            result = db.session.execute(query).fetchall()
            db.session.commit()
            
            tables = []
            for row in result:
                table_name = row[0]
                # Obtener count de filas
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = db.session.execute(count_query).fetchone()
                    row_count = count_result[0] if count_result else 0
                    db.session.commit()
                except:
                    db.session.rollback()
                    row_count = 0
                
                tables.append({
                    'schema': 'main',
                    'table_name': table_name,
                    'total_size_pretty': 'N/A',
                    'total_size_bytes': 0,
                    'table_size_pretty': 'N/A',
                    'indexes_size_pretty': 'N/A',
                    'row_count': row_count
                })
            
            return tables[:limit]
        else:
            # PostgreSQL
            query = text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size_pretty,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size_pretty,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size_pretty,
                    (SELECT n_live_tup FROM pg_stat_user_tables WHERE schemaname = t.schemaname AND relname = t.tablename) as row_count
                FROM pg_tables t
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT :limit
            """)
            result = db.session.execute(query, {'limit': limit}).fetchall()
            db.session.commit()  # Cerrar la transacción
            
            tables = []
            for row in result:
                tables.append({
                    'schema': row[0],
                    'table_name': row[1],
                    'total_size_pretty': row[2],
                    'total_size_bytes': row[3],
                    'table_size_pretty': row[4],
                    'indexes_size_pretty': row[5] if row[5] else '0 bytes',
                    'row_count': row[6] if row[6] is not None else 0
                })
            
            return tables
    except Exception as e:
        current_app.logger.warning(f"Error al obtener tamaños de tablas: {e}")
        db.session.rollback()  # Asegurar rollback en caso de error
        return []


def get_database_info() -> Dict[str, Any]:
    """Obtiene información general de la base de datos (compatible MySQL y PostgreSQL)"""
    try:
        from flask import current_app
        db_type = current_app.config.get('DB_TYPE', 'unknown')
        
        # Versión de la base de datos (compatible MySQL y PostgreSQL)
        version_query = text("SELECT VERSION()")
        version_result = db.session.execute(version_query).fetchone()
        version = version_result[0] if version_result else 'N/A'
        
        # Extraer número de versión según tipo de BD
        import re
        if db_type == 'mysql':
            version_match = re.search(r'(\d+\.\d+\.\d+)', version)
            version_number = version_match.group(1) if version_match else 'N/A'
        else:
            # PostgreSQL o desconocido
            version_match = re.search(r'PostgreSQL (\d+\.\d+)', version)
            version_number = version_match.group(1) if version_match else 'N/A'
        
        # Nombre de la base de datos
        if db_type == 'mysql':
            db_name_query = text("SELECT DATABASE()")
        else:
            db_name_query = text("SELECT current_database()")
        db_name_result = db.session.execute(db_name_query).fetchone()
        db_name = db_name_result[0] if db_name_result else 'N/A'
        
        # Fecha de creación (solo PostgreSQL tiene pg_stat_file)
        created_date = None
        if db_type == 'postgresql':
            try:
                created_query = text("""
                    SELECT pg_stat_file('base/' || oid || '/PG_VERSION').modification
                    FROM pg_database
                    WHERE datname = current_database()
                """)
                created_result = db.session.execute(created_query).fetchone()
                created_date = created_result[0] if created_result else None
            except:
                created_date = None
        # MySQL no tiene equivalente directo, usar información del schema
        
        # Número de tablas
        if db_type == 'mysql':
            tables_count_query = text("""
                SELECT count(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
            """)
        else:
            tables_count_query = text("""
                SELECT count(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
        tables_count_result = db.session.execute(tables_count_query).fetchone()
        tables_count = tables_count_result[0] if tables_count_result else 0
        
        return {
            'version': version,
            'version_number': version_number,
            'database_name': db_name,
            'database_type': db_type,
            'created_date': created_date.isoformat() if created_date else None,
            'tables_count': tables_count
        }
    except Exception as e:
        current_app.logger.warning(f"Error al obtener info de DB: {e}")
        return {'error': str(e)}


def get_index_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de índices"""
    try:
        # Detectar tipo de BD
        db_url = str(db.engine.url)
        if 'sqlite' in db_url.lower():
            # SQLite no tiene estadísticas detalladas de índices como PostgreSQL
            try:
                query = text("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                result = db.session.execute(query).fetchone()
                db.session.commit()
                total_indexes = result[0] if result else 0
                return {
                    'total_indexes': total_indexes,
                    'total_size_pretty': 'N/A',
                    'total_size_bytes': 0
                }
            except:
                db.session.rollback()
                return {
                    'total_indexes': 0,
                    'total_size_pretty': 'N/A',
                    'total_size_bytes': 0
                }
        else:
            # PostgreSQL
            query = text("""
                SELECT 
                    count(*) as total_indexes,
                    pg_size_pretty(sum(pg_relation_size(indexrelid))) as total_size_pretty,
                    sum(pg_relation_size(indexrelid)) as total_size_bytes
                FROM pg_stat_user_indexes
            """)
            result = db.session.execute(query).fetchone()
            db.session.commit()  # Cerrar la transacción
            
            if result:
                return {
                    'total_indexes': result[0],
                    'total_size_pretty': result[1] if result[1] else '0 bytes',
                    'total_size_bytes': result[2] if result[2] else 0
                }
            else:
                return {
                    'total_indexes': 0,
                    'total_size_pretty': '0 bytes',
                    'total_size_bytes': 0
                }
    except Exception as e:
        current_app.logger.warning(f"Error al obtener estadísticas de índices: {e}")
        db.session.rollback()  # Asegurar rollback en caso de error
        return {'error': str(e)}


def get_connection_pool_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del pool de conexiones de SQLAlchemy"""
    try:
        engine = db.engine
        pool = engine.pool
        
        return {
            'size': pool.size() if hasattr(pool, 'size') else 0,
            'checked_in': pool.checkedin() if hasattr(pool, 'checkedin') else 0,
            'checked_out': pool.checkedout() if hasattr(pool, 'checkedout') else 0,
            'overflow': pool.overflow() if hasattr(pool, 'overflow') else 0,
            'invalid': pool.invalid() if hasattr(pool, 'invalid') else 0
        }
    except Exception as e:
        current_app.logger.warning(f"Error al obtener estadísticas del pool: {e}")
        return {'error': str(e)}









