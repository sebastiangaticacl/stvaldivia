"""
Helper para verificar el estado de los servicios del sistema
"""
import subprocess
import requests
import os
from flask import current_app
from app.helpers.logger import get_logger

logger = get_logger(__name__)


def check_systemd_service(service_name):
    """
    Verifica el estado de un servicio systemd
    
    Returns:
        dict: {
            'status': 'active' | 'inactive' | 'failed' | 'unknown',
            'running': bool,
            'enabled': bool,
            'message': str
        }
    """
    try:
        # Usar sudo para ejecutar systemctl (necesario en producción)
        result = subprocess.run(
            ['/usr/bin/sudo', 'systemctl', 'is-active', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.returncode == 0
        
        # Verificar si está habilitado
        result_enabled = subprocess.run(
            ['/usr/bin/sudo', 'systemctl', 'is-enabled', service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_enabled = result_enabled.returncode == 0
        
        if is_active:
            status = 'active'
            message = 'Servicio activo y funcionando'
        else:
            status = 'inactive'
            message = 'Servicio inactivo'
            
        return {
            'status': status,
            'running': is_active,
            'enabled': is_enabled,
            'message': message
        }
    except subprocess.TimeoutExpired:
        return {
            'status': 'unknown',
            'running': False,
            'enabled': False,
            'message': 'Timeout al verificar servicio'
        }
    except FileNotFoundError:
        # systemctl no disponible - intentar verificación alternativa
        return check_service_alternative(service_name)
    except PermissionError:
        # Sin permisos para sudo - intentar verificación alternativa
        return check_service_alternative(service_name)
    except Exception as e:
        logger.error(f"Error al verificar servicio {service_name}: {e}")
        # Intentar método alternativo
        return check_service_alternative(service_name)


def check_service_alternative(service_name):
    """
    Verificación alternativa de servicios sin systemctl
    Verifica si el proceso está corriendo
    """
    try:
        # En desarrollo (macOS), retornar estado desconocido rápidamente
        # para evitar demoras en el dashboard
        if os.environ.get('FLASK_ENV') == 'development' or os.uname().sysname == 'Darwin':
            return {
                'status': 'unknown',
                'running': None,
                'enabled': None,
                'message': 'Verificación de servicios deshabilitada en desarrollo'
            }
        
        # Mapeo de nombres de servicios a patrones de proceso
        process_patterns = {
            'postfix': ['postfix', 'qmgr', 'pickup', 'master'],
            'gunicorn-flask-app': ['gunicorn.*wsgi', 'gunicorn.*application', 'gunicorn.*stvaldivia'],
            'gunicorn': ['gunicorn.*wsgi', 'gunicorn.*application', 'gunicorn.*stvaldivia', 'gunicorn.*127.0.0.1:5001'],
            'nginx': ['nginx']
        }
        
        # Obtener patrones para este servicio
        patterns = process_patterns.get(service_name, [service_name])
        
        # Primero intentar con ps (más confiable)
        # Buscar ps en ubicaciones comunes (varía según OS)
        ps_paths = ['/bin/ps', '/usr/bin/ps']
        ps_cmd = None
        for path in ps_paths:
            if os.path.exists(path):
                ps_cmd = path
                break
        
        if ps_cmd:
            try:
                result = subprocess.run(
                    [ps_cmd, 'aux'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    output = result.stdout.lower()
                    # Verificar si el servicio está en la salida de ps
                    service_keywords = {
                        'postfix': ['/usr/lib/postfix/sbin/master', 'postfix', 'qmgr', 'pickup'],
                        'gunicorn-flask-app': ['gunicorn', 'wsgi:application', 'wsgi'],
                        'gunicorn': ['gunicorn', 'wsgi:application', 'wsgi'],
                        'nginx': ['nginx: master', 'nginx: worker', 'nginx']
                    }
                    keywords = service_keywords.get(service_name, [service_name])
                    for keyword in keywords:
                        if keyword in output:
                            logger.debug(f"Servicio {service_name} encontrado con keyword: {keyword}")
                            return {
                                'status': 'active',
                                'running': True,
                                'enabled': None,
                                'message': f'Servicio activo (verificado con ps)'
                            }
                    logger.debug(f"Servicio {service_name} NO encontrado en ps. Output sample: {output[:200]}")
            except Exception as e:
                logger.error(f"Error con ps para {service_name}: {e}")
        
        # Si ps no funcionó, intentar con pgrep
        for pattern in patterns:
            try:
                result = subprocess.run(
                    ['/usr/bin/pgrep', '-f', pattern],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    stderr=subprocess.DEVNULL
                )
                # Si pgrep encuentra procesos, returncode es 0
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        'status': 'active',
                        'running': True,
                        'enabled': None,  # No podemos verificar sin systemctl
                        'message': f'Servicio activo (proceso encontrado)'
                    }
            except Exception as e:
                logger.debug(f"Error con patrón {pattern}: {e}")
                continue
        
        # Si no se encontró ningún proceso
        return {
            'status': 'inactive',
            'running': False,
            'enabled': None,
            'message': 'Servicio inactivo (proceso no encontrado)'
        }
    except Exception as e:
        logger.error(f"Error en verificación alternativa para {service_name}: {e}")
        return {
            'status': 'unknown',
            'running': False,
            'enabled': None,
            'message': f'Error al verificar: {str(e)[:50]}'
        }


def check_postfix_status():
    """Verifica el estado del servicio de correo Postfix (opcional)"""
    # Postfix es opcional - no es crítico si no está corriendo
    try:
        status = check_systemd_service('postfix.service')
        if status['status'] == 'active':
            return {
                **status,
                'critical': False,
                'optional': True
            }
    except:
        pass
    
    # Método alternativo
    alt_status = check_service_alternative('postfix')
    
    if alt_status.get('running'):
        return {
            **alt_status,
            'critical': False,
            'optional': True
        }
    
    # Si no está corriendo, marcar como no configurado (opcional)
    return {
        'status': 'not_configured',
        'running': False,
        'enabled': None,
        'message': 'Postfix no configurado (opcional - solo necesario para envío de correos)',
        'critical': False,
        'optional': True
    }


def check_gunicorn_status():
    """Verifica el estado del servicio Gunicorn/Flask"""
    # Verificar primero el servicio real (stvaldivia)
    try:
        status = check_systemd_service('stvaldivia.service')
        if status['status'] == 'active':
            return {
                'status': 'active',
                'running': True,
                'enabled': status.get('enabled', None),
                'message': 'Servicio Flask (stvaldivia) activo',
                'critical': True
            }
    except:
        pass
    
    # Método alternativo: buscar proceso gunicorn
    alt_status = check_service_alternative('gunicorn')
    
    # Si el método alternativo encontró el servicio, usarlo
    if alt_status.get('running'):
        return {
            **alt_status,
            'critical': True
        }
    
    # Intentar verificar otros nombres comunes
    service_names = ['gunicorn-flask-app', 'flask-app', 'gunicorn']
    for service_name in service_names:
        try:
            status = check_systemd_service(service_name)
            if status['status'] == 'active':
                return {
                    **status,
                    'critical': True
                }
        except:
            continue
    
    # Si no se encontró, retornar inactivo pero crítico
    return {
        'status': 'inactive',
        'running': False,
        'enabled': None,
        'message': 'Servicio Flask/Gunicorn no encontrado',
        'critical': True
    }


def check_nginx_status():
    """Verifica el estado del servicio Nginx"""
    # Nginx es crítico
    try:
        status = check_systemd_service('nginx.service')
        if status['status'] == 'active':
            return {
                **status,
                'critical': True
            }
    except:
        pass
    
    # Método alternativo
    alt_status = check_service_alternative('nginx')
    
    if alt_status.get('running'):
        return {
            **alt_status,
            'critical': True
        }
    
    # Si no está corriendo, retornar inactivo pero crítico
    return {
        'status': 'inactive',
        'running': False,
        'enabled': None,
        'message': 'Servicio Nginx no encontrado',
        'critical': True
    }


# Cache simple para estado de API
_api_status_cache = {
    'last_check': 0,
    'status': None,
    'ttl': 30  # 30 segundos de caché
}

def check_api_status(checked_by='system', log_connection=True):
    """
    Verifica el estado de la API de PHP POS
    
    Args:
        checked_by: Quién realiza la verificación ('system', 'admin', 'manual')
        log_connection: Si se debe registrar en el log (default: True)
    
    Returns:
        dict: {
            'status': 'online' | 'offline' | 'error',
            'online': bool,
            'response_time_ms': float,
            'message': str
        }
    """
    import time
    global _api_status_cache
    
    current_time = time.time()
    
    # Usar caché si es válido (solo para verificaciones automáticas del sistema)
    if checked_by == 'system' and _api_status_cache['status'] and (current_time - _api_status_cache['last_check'] < _api_status_cache['ttl']):
        return _api_status_cache['status']
        
    try:
        api_key = current_app.config.get('API_KEY')
        base_url = current_app.config.get('BASE_API_URL')
        
        if not api_key or not base_url:
            result = {
                'status': 'error',
                'online': False,
                'response_time_ms': 0,
                'message': 'API no configurada'
            }
            _api_status_cache['status'] = result
            _api_status_cache['last_check'] = current_time
            
            # Registrar en log si está habilitado
            if log_connection:
                _log_api_connection(result, base_url, checked_by)
            
            return result
        
        # Intentar una llamada simple a la API
        # Timeout reducido a 2 segundos para no bloquear la UI
        url = f"{base_url}/employees"
        headers = {
            "x-api-key": api_key,
            "accept": "application/json"
        }
        
        start_time = time.time()
        resp = requests.get(url, headers=headers, timeout=2)
        resp.raise_for_status()
        elapsed_ms = (time.time() - start_time) * 1000
        
        result = {
            'status': 'online',
            'online': True,
            'response_time_ms': elapsed_ms,
            'message': 'API conectada y respondiendo'
        }
        
        _api_status_cache['status'] = result
        _api_status_cache['last_check'] = current_time
        
        # Registrar en log si está habilitado
        if log_connection:
            _log_api_connection(result, base_url, checked_by)
        
        return result
        
    except requests.exceptions.Timeout:
        result = {
            'status': 'offline',
            'online': False,
            'response_time_ms': 0,
            'message': 'La API no responde (timeout)'
        }
        # Cachear error también para no reintentar inmediatamente
        _api_status_cache['status'] = result
        _api_status_cache['last_check'] = current_time
        
        # Registrar en log si está habilitado
        if log_connection:
            _log_api_connection(result, base_url, checked_by)
        
        return result
        
    except requests.exceptions.RequestException as e:
        result = {
            'status': 'offline',
            'online': False,
            'response_time_ms': 0,
            'message': f'Error de conexión: {str(e)[:50]}'
        }
        _api_status_cache['status'] = result
        _api_status_cache['last_check'] = current_time
        
        # Registrar en log si está habilitado
        if log_connection:
            _log_api_connection(result, base_url, checked_by)
        
        return result
        
    except Exception as e:
        logger.error(f"Error al verificar API: {e}")
        result = {
            'status': 'error',
            'online': False,
            'response_time_ms': 0,
            'message': f'Error: {str(e)[:50]}'
        }
        _api_status_cache['status'] = result
        _api_status_cache['last_check'] = current_time
        
        # Registrar en log si está habilitado
        if log_connection:
            _log_api_connection(result, base_url, checked_by)
        
        return result


def _log_api_connection(result, api_url, checked_by='system'):
    """
    Registra una conexión API en el log
    
    Args:
        result: Resultado de la verificación
        api_url: URL de la API
        checked_by: Quién realizó la verificación
    """
    try:
        from app.models.api_log_models import ApiConnectionLog
        from app.models import db
        
        log_entry = ApiConnectionLog(
            status=result.get('status', 'error'),
            response_time_ms=result.get('response_time_ms'),
            message=result.get('message'),
            api_url=api_url,
            checked_by=checked_by
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        # Limpiar logs antiguos (mantener solo los últimos 1000)
        try:
            old_logs = ApiConnectionLog.query.order_by(ApiConnectionLog.timestamp.desc()).offset(1000).all()
            for old_log in old_logs:
                db.session.delete(old_log)
            db.session.commit()
        except:
            db.session.rollback()
            
    except Exception as e:
        # No fallar si hay error al registrar el log
        logger.warning(f"Error al registrar log de conexión API: {e}")


def get_all_services_status():
    """
    Obtiene el estado de todos los servicios
    
    Returns:
        dict: Estado de todos los servicios con timestamp
    """
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    
    try:
        postfix_status = check_postfix_status()
        gunicorn_status = check_gunicorn_status()
        nginx_status = check_nginx_status()
        api_status = check_api_status()
        
        # Agregar timestamp a cada servicio
        postfix_status['last_updated'] = timestamp
        gunicorn_status['last_updated'] = timestamp
        nginx_status['last_updated'] = timestamp
        api_status['last_updated'] = timestamp
        
        logger.debug(f"Postfix: {postfix_status}")
        logger.debug(f"Gunicorn: {gunicorn_status}")
        logger.debug(f"Nginx: {nginx_status}")
        logger.debug(f"API: {api_status}")
        
        return {
            'postfix': postfix_status,
            'gunicorn': gunicorn_status,
            'nginx': nginx_status,
            'api': api_status
        }
    except Exception as e:
        logger.error(f"Error en get_all_services_status: {e}", exc_info=True)
        # Retornar estado por defecto en caso de error
        return {
            'postfix': {'status': 'unknown', 'running': False, 'enabled': None, 'message': f'Error: {str(e)[:50]}'},
            'gunicorn': {'status': 'unknown', 'running': False, 'enabled': None, 'message': f'Error: {str(e)[:50]}'},
            'nginx': {'status': 'unknown', 'running': False, 'enabled': None, 'message': f'Error: {str(e)[:50]}'},
            'api': {'status': 'error', 'online': False, 'response_time_ms': 0, 'message': f'Error: {str(e)[:50]}'}
        }


def restart_service(service_name):
    """
    Reinicia un servicio del sistema
    
    Args:
        service_name: Nombre del servicio a reiniciar
            - 'postfix': Servidor de correo
            - 'gunicorn': Aplicación Flask
            - 'nginx': Servidor web
    
    Returns:
        dict: {
            'success': bool,
            'message': str
        }
    """
    # Mapeo de nombres de servicios a nombres de systemd
    service_map = {
        'postfix': 'postfix.service',
        'gunicorn': 'gunicorn-flask-app.service',
        'nginx': 'nginx.service'
    }
    
    systemd_name = service_map.get(service_name)
    if not systemd_name:
        return {
            'success': False,
            'message': f'Servicio desconocido: {service_name}'
        }
    
    try:
        # Intentar reiniciar con systemctl (requiere sudo)
        # Primero intentar con sudo directamente
        result = subprocess.run(
            ['/usr/bin/sudo', 'systemctl', 'restart', systemd_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"Servicio {service_name} reiniciado exitosamente")
            return {
                'success': True,
                'message': f'Servicio {service_name} reiniciado exitosamente'
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"Error al reiniciar {service_name}: {error_msg}")
            
            # Si falla con sudo, intentar método alternativo
            # Para Gunicorn, podemos usar kill -HUP en el proceso maestro
            if service_name == 'gunicorn':
                return restart_gunicorn_alternative()
            
            return {
                'success': False,
                'message': f'Error al reiniciar: {error_msg}'
            }
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout al reiniciar servicio {service_name}")
        return {
            'success': False,
            'message': 'Timeout: El reinicio tardó demasiado'
        }
    except Exception as e:
        logger.error(f"Excepción al reiniciar {service_name}: {e}", exc_info=True)
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def restart_gunicorn_alternative():
    """
    Método alternativo para reiniciar Gunicorn usando kill -HUP
    """
    try:
        # Buscar el proceso maestro de Gunicorn
        result = subprocess.run(
            ['/usr/bin/pgrep', '-f', 'gunicorn.*wsgi:application'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            # El primer PID suele ser el proceso maestro
            master_pid = pids[0].strip()
            
            # Enviar señal HUP para recargar workers
            subprocess.run(
                ['kill', '-HUP', master_pid],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            
            logger.info(f"Gunicorn recargado usando kill -HUP en PID {master_pid}")
            return {
                'success': True,
                'message': 'Gunicorn recargado exitosamente'
            }
        else:
            return {
                'success': False,
                'message': 'No se encontró el proceso de Gunicorn'
            }
    except Exception as e:
        logger.error(f"Error en método alternativo de reinicio de Gunicorn: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def get_postfix_queue():
    """
    Obtiene la cola de correo de Postfix
    
    Returns:
        dict: {
            'success': bool,
            'queue': list,  # Lista de correos en cola
            'total': int,   # Total de correos en cola
            'message': str
        }
    """
    try:
        # Usar postqueue -p para obtener la cola (requiere sudo)
        result = subprocess.run(
            ['/usr/bin/sudo', 'postqueue', '-p'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Si falla con sudo, intentar sin sudo (puede funcionar si el usuario tiene permisos)
            # Buscar postqueue en ubicaciones comunes
            postqueue_paths = ['/usr/sbin/postqueue', '/usr/bin/postqueue']
            result = None
            for path in postqueue_paths:
                try:
                    result = subprocess.run(
                        [path, '-p'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        break
                except FileNotFoundError:
                    continue
            
            # Si aún no funciona, intentar sin ruta (puede estar en PATH)
            if not result or result.returncode != 0:
                try:
                    result = subprocess.run(
                        ['postqueue', '-p'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                except FileNotFoundError:
                    pass
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            # Si la cola está vacía, postqueue muestra "Mail queue is empty"
            if 'Mail queue is empty' in output or 'is empty' in output:
                return {
                    'success': True,
                    'queue': [],
                    'total': 0,
                    'message': 'La cola de correo está vacía'
                }
            
            # Parsear la salida de postqueue
            # Formato típico:
            # -Queue ID- --Size-- ----Arrival Time---- -Sender/Recipient-------
            # 1A2B3C4D5E    1234  Mon Nov 26 21:00:00  sender@example.com
            #                                          recipient@example.com
            lines = output.split('\n')
            queue_items = []
            
            # Saltar la línea de encabezado
            start_parsing = False
            for line in lines:
                if 'Queue ID' in line or '----' in line:
                    start_parsing = True
                    continue
                
                if not start_parsing or not line.strip():
                    continue
                
                # Intentar parsear cada línea
                parts = line.split()
                if len(parts) >= 4:
                    queue_id = parts[0]
                    size = parts[1] if len(parts) > 1 else 'N/A'
                    arrival_time = ' '.join(parts[2:5]) if len(parts) > 4 else 'N/A'
                    sender = parts[5] if len(parts) > 5 else 'N/A'
                    
                    queue_items.append({
                        'queue_id': queue_id,
                        'size': size,
                        'arrival_time': arrival_time,
                        'sender': sender
                    })
                elif len(parts) > 0 and parts[0].startswith('-'):
                    # Línea de continuación (recipient)
                    if queue_items:
                        queue_items[-1]['recipient'] = parts[0].replace('-', '').strip()
            
            return {
                'success': True,
                'queue': queue_items,
                'total': len(queue_items),
                'message': f'{len(queue_items)} correo(s) en cola',
                'raw_output': output  # Incluir salida raw para debugging
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"Error al obtener cola de Postfix: {error_msg}")
            return {
                'success': False,
                'queue': [],
                'total': 0,
                'message': f'Error al obtener la cola: {error_msg}'
            }
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout al obtener cola de Postfix")
        return {
            'success': False,
            'queue': [],
            'total': 0,
            'message': 'Timeout: La operación tardó demasiado'
        }
    except Exception as e:
        logger.error(f"Excepción al obtener cola de Postfix: {e}", exc_info=True)
        return {
            'success': False,
            'queue': [],
            'total': 0,
            'message': f'Error: {str(e)}'
        }

