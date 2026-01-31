"""
Funciones de compatibilidad para shift_manager.py
Migra gradualmente del sistema legacy (JSON) al nuevo sistema (Jornada en BD)

Este módulo proporciona funciones compatibles que usan JornadaService
en lugar del sistema legacy basado en JSON.
"""
from datetime import datetime
from flask import current_app
from app.models.jornada_models import Jornada
from app.application.services.jornada_service import JornadaService
from app.helpers.timezone_utils import CHILE_TZ
import pytz


def get_shift_status():
    """
    Obtiene el estado actual del turno usando Jornada (nuevo sistema)
    Mantiene compatibilidad con el formato del sistema legacy
    
    Busca jornadas abiertas de cualquier fecha (no solo de hoy)
    para reconocer turnos que se abrieron en días anteriores.
    """
    try:
        # Usar zona horaria de Chile para obtener la fecha correcta
        fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        # Primero buscar jornada abierta para hoy
        jornada_service = JornadaService()
        jornada = jornada_service.obtener_jornada_actual(fecha_hoy)
        
        # Si no hay jornada abierta para hoy, buscar cualquier jornada abierta
        # (puede ser de días anteriores que aún no se cerró)
        if not jornada or jornada.estado_apertura != 'abierto':
            jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').order_by(
                Jornada.fecha_jornada.desc()
            ).first()
            
            if jornada_abierta:
                jornada = jornada_abierta
                current_app.logger.info(
                    f"✅ Jornada abierta encontrada (fecha: {jornada.fecha_jornada}, "
                    f"buscando para: {fecha_hoy})"
                )
        
        if jornada and jornada.estado_apertura == 'abierto':
            # Parsear barras_disponibles si es string JSON
            import json
            barras = []
            if jornada.barras_disponibles:
                try:
                    if isinstance(jornada.barras_disponibles, str):
                        barras = json.loads(jornada.barras_disponibles)
                    else:
                        barras = jornada.barras_disponibles
                except:
                    barras = []
            
            return {
                'is_open': True,
                'shift_date': jornada.fecha_jornada,
                'opened_at': jornada.abierto_en.isoformat() if jornada.abierto_en else jornada.horario_apertura_programado,
                'closed_at': None,
                'opened_by': jornada.abierto_por or 'admin',
                'fiesta_nombre': jornada.nombre_fiesta,
                'djs': jornada.djs,
                'barras_disponibles': barras
            }
        else:
            return {
                'is_open': False,
                'shift_date': fecha_hoy,
                'opened_at': None,
                'closed_at': None,
                'opened_by': None
            }
    except Exception as e:
        current_app.logger.error(f"Error al obtener estado del turno desde Jornada: {e}")
        # Fallback al sistema legacy si hay error
        try:
            from .shift_manager import get_shift_status as legacy_get_shift_status
            return legacy_get_shift_status()
        except:
            return {
                'is_open': False,
                'shift_date': None,
                'opened_at': None,
                'closed_at': None,
                'opened_by': None
            }


def is_shift_open():
    """Verifica si hay un turno abierto usando Jornada"""
    status = get_shift_status()
    return status.get('is_open', False)


def open_shift(fiesta_nombre='', djs='', barras_disponibles=None, bartenders=None, opened_by='admin'):
    """
    Abre un nuevo turno usando Jornada (nuevo sistema)
    Mantiene compatibilidad con la firma del sistema legacy
    """
    try:
        jornada_service = JornadaService()
        # Usar zona horaria de Chile para obtener la fecha correcta
        fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
        
        # Verificar si ya hay una jornada abierta (de cualquier fecha)
        jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').first()
        if jornada_abierta:
            return False, f"Ya hay un turno abierto (fecha: {jornada_abierta.fecha_jornada}). Debe cerrar el turno actual antes de abrir uno nuevo."
        
        # Validar datos requeridos
        if not fiesta_nombre:
            return False, "El nombre de la fiesta es requerido"
        
        # Preparar listas si no son listas
        if barras_disponibles is None:
            barras_disponibles = []
        if bartenders is None:
            bartenders = []
        
        # Crear jornada usando el servicio
        from app.application.dto.jornada_dto import CrearJornadaRequest
        
        request = CrearJornadaRequest(
            fecha_jornada=fecha_hoy,
            tipo_turno='Noche',  # Default
            nombre_fiesta=fiesta_nombre,
            horario_apertura_programado=datetime.now().strftime('%H:%M'),
            horario_cierre_programado='04:00',  # Default
            djs=djs or '',
            barras_disponibles=barras_disponibles if isinstance(barras_disponibles, list) else list(barras_disponibles)
        )
        
        success, message, jornada = jornada_service.crear_jornada(request, opened_by)
        
        if success and jornada:
            # Intentar abrir la jornada inmediatamente
            from app.application.dto.jornada_dto import AbrirLocalRequest
            
            abrir_request = AbrirLocalRequest(abierto_por=opened_by)
            success_open, message_open = jornada_service.abrir_local(
                jornada.id,
                abrir_request
            )
            
            if success_open:
                return True, f"Turno abierto correctamente para el día {fecha_hoy}"
            else:
                # Si no se puede abrir porque falta planilla, abrir directamente sin validación
                # Esto permite abrir turnos rápidamente sin necesidad de configurar todo primero
                try:
                    from app.models import db
                    from datetime import datetime as dt
                    from app.utils.timezone import CHILE_TZ as TZ_CHILE
                    
                    jornada_db = Jornada.query.get(jornada.id)
                    if jornada_db and jornada_db.estado_apertura != 'abierto':
                        now_chile = dt.now(TZ_CHILE)
                        now_local = now_chile.replace(tzinfo=None)
                        jornada_db.estado_apertura = 'abierto'
                        jornada_db.horario_apertura_real = now_local
                        jornada_db.abierto_por = opened_by
                        jornada_db.abierto_en = now_local
                        
                        # Actualizar checklist de apertura
                        checklist_apertura = {
                            'jornada_abierta': True,
                            'fecha_apertura': now_chile.isoformat(),
                            'abierto_por': opened_by
                        }
                        jornada_db.set_checklist_apertura(checklist_apertura)
                        db.session.commit()
                        
                        return True, f"Turno abierto correctamente para el día {fecha_hoy} (sin validación de planilla)"
                    else:
                        return False, f"Jornada creada pero error al abrir: {message_open}"
                except Exception as e:
                    current_app.logger.error(f"Error al abrir jornada directamente: {e}", exc_info=True)
                    return False, f"Jornada creada pero error al abrir: {message_open}"
        else:
            return False, message or "Error al crear jornada"
            
    except Exception as e:
        current_app.logger.error(f"Error al abrir turno usando Jornada: {e}", exc_info=True)
        # Fallback al sistema legacy si hay error
        try:
            from .shift_manager import open_shift as legacy_open_shift
            return legacy_open_shift(fiesta_nombre, djs, barras_disponibles, bartenders, opened_by)
        except:
            return False, f"Error al abrir turno: {str(e)}"


def close_shift(closed_by='admin'):
    """
    Cierra el turno actual usando Jornada (nuevo sistema)
    Mantiene compatibilidad con la firma del sistema legacy
    """
    try:
        # Buscar cualquier jornada abierta (no solo de hoy)
        jornada = Jornada.query.filter_by(estado_apertura='abierto').order_by(
            Jornada.fecha_jornada.desc()
        ).first()
        
        if not jornada:
            return False, "No hay un turno abierto para cerrar."
        
        # Cerrar jornada directamente en el modelo
        from app.models import db
        from datetime import datetime
        
        try:
            jornada.estado_apertura = 'cerrado'
            # Agregar campo cerrado_en si no existe (puede requerir migración)
            if hasattr(jornada, 'cerrado_en'):
                # Guardar en UTC para consistencia en BD, pero calcular desde hora de Chile
                now_chile = datetime.now(CHILE_TZ)
                now_utc = now_chile.astimezone(pytz.UTC).replace(tzinfo=None)
                jornada.cerrado_en = now_utc
            if hasattr(jornada, 'cerrado_por'):
                jornada.cerrado_por = closed_by
            
            db.session.commit()
            
            # Enviar evento a n8n (después de commit exitoso)
            try:
                from app.helpers.n8n_client import send_shift_closed
                from app.models.delivery_models import Delivery
                from app.models.pos_models import PosSale
                from datetime import datetime as dt
                
                # Calcular totales del turno
                shift_date = jornada.fecha_jornada.strftime('%Y-%m-%d') if hasattr(jornada.fecha_jornada, 'strftime') else str(jornada.fecha_jornada)
                
                # Contar entregas del día
                total_deliveries = Delivery.query.filter(
                    db.func.date(Delivery.timestamp) == jornada.fecha_jornada
                ).count() if hasattr(jornada, 'fecha_jornada') else 0
                
                # Calcular total de ventas del día
                total_sales = 0.0
                try:
                    sales = PosSale.query.filter(
                        db.func.date(PosSale.created_at) == jornada.fecha_jornada
                    ).all() if hasattr(jornada, 'fecha_jornada') else []
                    total_sales = sum(float(sale.total_amount or 0) for sale in sales)
                except:
                    pass
                
                send_shift_closed(
                    shift_date=shift_date,
                    total_sales=total_sales,
                    total_deliveries=total_deliveries
                )
            except Exception as e:
                current_app.logger.warning(f"Error enviando evento de cierre de turno a n8n: {e}")
            
            current_app.logger.info(f"✅ Turno cerrado: {jornada.fecha_jornada} por {closed_by}")
            return True, f"Turno cerrado correctamente. Turno del día {jornada.fecha_jornada}"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al cerrar jornada: {e}")
            return False, f"Error al cerrar turno: {str(e)}"
            
    except Exception as e:
        current_app.logger.error(f"Error al cerrar turno usando Jornada: {e}", exc_info=True)
        # Fallback al sistema legacy si hay error
        try:
            from .shift_manager import close_shift as legacy_close_shift
            return legacy_close_shift(closed_by)
        except:
            return False, f"Error al cerrar turno: {str(e)}"


def get_shift_history():
    """
    Obtiene el historial de turnos usando Jornada (nuevo sistema)
    Mantiene compatibilidad con el formato del sistema legacy
    """
    try:
        from app.models import db
        from app.models.jornada_models import Jornada
        
        # Obtener jornadas cerradas ordenadas por fecha
        jornadas = Jornada.query.filter(
            Jornada.estado_apertura == 'cerrado'
        ).order_by(Jornada.fecha_jornada.desc()).limit(365).all()
        
        history = []
        for jornada in jornadas:
            import json
            barras = []
            if jornada.barras_disponibles:
                try:
                    barras = json.loads(jornada.barras_disponibles) if isinstance(jornada.barras_disponibles, str) else jornada.barras_disponibles
                except:
                    barras = []
            
            history.append({
                'shift_date': jornada.fecha_jornada,
                'opened_at': jornada.abierto_en.isoformat() if jornada.abierto_en else jornada.horario_apertura_programado,
                'closed_at': jornada.cerrado_en.isoformat() if hasattr(jornada, 'cerrado_en') and jornada.cerrado_en else None,
                'opened_by': jornada.abierto_por or 'admin',
                'closed_by': getattr(jornada, 'cerrado_por', 'admin'),
                'fiesta_nombre': jornada.nombre_fiesta,
                'djs': jornada.djs,
                'barras_disponibles': barras,
                'bartenders': []  # No disponible en Jornada directamente
            })
        
        return history
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener historial de turnos desde Jornada: {e}")
        # Fallback al sistema legacy si hay error
        try:
            from .shift_manager import get_shift_history as legacy_get_shift_history
            return legacy_get_shift_history()
        except:
            return []

