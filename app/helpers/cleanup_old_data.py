"""
Script para limpiar datos antiguos del sistema
- Resolver todos los cierres pendientes
- Eliminar registros de turnos antiguos
"""
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta
from flask import current_app
from app.models import db
from app.models.pos_models import RegisterClose
from app.models.jornada_models import Jornada
from app.helpers.register_close_db import resolve_register_close, get_pending_closes
import logging
import os
import json

logger = logging.getLogger(__name__)


def resolver_todos_cierres_pendientes(resolved_by: str = 'admin', resolution_notes: str = 'Limpieza automática del sistema') -> Dict[str, Any]:
    """
    Resuelve todos los cierres de caja pendientes.
    
    Args:
        resolved_by: Usuario que resuelve
        resolution_notes: Notas de resolución
        
    Returns:
        dict: Resumen de la operación
    """
    try:
        # Obtener todos los cierres pendientes
        pending_closes = get_pending_closes()
        
        resueltos = 0
        errores = 0
        
        for close in pending_closes:
            close_id = close.get('id')
            if close_id:
                success = resolve_register_close(close_id, resolved_by, resolution_notes)
                if success:
                    resueltos += 1
                    logger.info(f"✅ Cierre {close_id} resuelto: {close.get('register_name')}")
                else:
                    errores += 1
                    logger.error(f"❌ Error al resolver cierre {close_id}")
        
        return {
            'success': True,
            'resueltos': resueltos,
            'errores': errores,
            'total': len(pending_closes),
            'message': f'Se resolvieron {resueltos} de {len(pending_closes)} cierres pendientes'
        }
        
    except Exception as e:
        logger.error(f"Error al resolver cierres pendientes: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'resueltos': 0,
            'errores': 0,
            'total': 0
        }


def eliminar_turnos_anteriores(dias_antiguedad: int = 30, mantener_abiertos: bool = True, eliminar_todo: bool = False) -> Dict[str, Any]:
    """
    Elimina registros de turnos/jornadas anteriores.
    
    Args:
        dias_antiguedad: Días de antigüedad para considerar un turno como "antiguo" (ignorado si eliminar_todo=True)
        mantener_abiertos: Si es True, no elimina turnos/jornadas abiertos
        eliminar_todo: Si es True, elimina todos los registros anteriores (excepto abiertos si mantener_abiertos=True)
        
    Returns:
        dict: Resumen de la operación
    """
    try:
        eliminados = 0
        errores = 0
        
        # Eliminar jornadas antiguas
        try:
            jornadas_query = Jornada.query
            
            if mantener_abiertos:
                jornadas_query = jornadas_query.filter(
                    Jornada.estado_apertura != 'abierto'
                )
            
            if not eliminar_todo:
                fecha_limite = datetime.utcnow() - timedelta(days=dias_antiguedad)
                jornadas_query = jornadas_query.filter(
                    Jornada.creado_en < fecha_limite
                )
            
            jornadas_antiguas = jornadas_query.all()
            
            for jornada in jornadas_antiguas:
                try:
                    # Las relaciones (planilla_trabajadores, aperturas_cajas) 
                    # se eliminarán automáticamente por cascade
                    db.session.delete(jornada)
                    eliminados += 1
                    logger.info(f"✅ Jornada {jornada.id} ({jornada.fecha_jornada}) eliminada")
                except Exception as e:
                    errores += 1
                    logger.error(f"❌ Error al eliminar jornada {jornada.id}: {e}")
            
        except Exception as e:
            logger.error(f"Error al procesar jornadas: {e}", exc_info=True)
        
        # Eliminar cierres de caja antiguos (resueltos o balanceados)
        try:
            cierres_query = RegisterClose.query.filter(
                RegisterClose.status.in_(['resolved', 'balanced'])
            )
            
            if not eliminar_todo:
                fecha_limite = datetime.utcnow() - timedelta(days=dias_antiguedad)
                cierres_query = cierres_query.filter(
                    RegisterClose.created_at < fecha_limite
                )
            
            cierres_antiguos = cierres_query.all()
            
            for cierre in cierres_antiguos:
                try:
                    db.session.delete(cierre)
                    eliminados += 1
                    logger.info(f"✅ Cierre {cierre.id} ({cierre.register_name}) eliminado")
                except Exception as e:
                    errores += 1
                    logger.error(f"❌ Error al eliminar cierre {cierre.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error al procesar cierres: {e}", exc_info=True)
        
        # Limpiar historial de turnos (archivo JSON)
        try:
            # Obtener ruta del archivo de historial
            if current_app:
                from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
                ensure_not_production("La limpieza de datos antiguos desde archivo")
                instance_path = get_safe_instance_path() or current_app.instance_path
            else:
                # Si no hay app context, usar ruta relativa
                base_path = os.path.dirname(os.path.dirname(__file__))
                instance_path = os.path.join(base_path, 'instance')
            
            os.makedirs(instance_path, exist_ok=True)
            history_file = os.path.join(instance_path, 'shift_history.json')
            
            if os.path.exists(history_file):
                if eliminar_todo:
                    # Eliminar todo el historial
                    os.remove(history_file)
                    logger.info("✅ Archivo de historial de turnos eliminado completamente")
                    eliminados += 1
                else:
                    # Mantener solo los últimos N días
                    try:
                        with open(history_file, 'r', encoding='utf-8') as f:
                            history = json.load(f)
                        
                        if isinstance(history, list):
                            fecha_limite = datetime.utcnow() - timedelta(days=dias_antiguedad)
                            history_filtrado = []
                            
                            for shift in history:
                                closed_at = shift.get('closed_at', '')
                                if closed_at:
                                    try:
                                        # Intentar parsear la fecha
                                        if isinstance(closed_at, str):
                                            # Formato ISO
                                            if 'T' in closed_at:
                                                shift_date = datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                                            else:
                                                # Formato solo fecha
                                                shift_date = datetime.strptime(closed_at[:10], '%Y-%m-%d')
                                            
                                            if shift_date.replace(tzinfo=None) > fecha_limite:
                                                history_filtrado.append(shift)
                                        else:
                                            history_filtrado.append(shift)
                                    except:
                                        # Si no se puede parsear, mantenerlo por seguridad
                                        history_filtrado.append(shift)
                                else:
                                    # Si no tiene fecha de cierre, mantenerlo
                                    history_filtrado.append(shift)
                            
                            if len(history_filtrado) < len(history):
                                with open(history_file, 'w', encoding='utf-8') as f:
                                    json.dump(history_filtrado, f, indent=2, ensure_ascii=False)
                                eliminados += len(history) - len(history_filtrado)
                                logger.info(f"✅ {len(history) - len(history_filtrado)} turnos antiguos eliminados del historial")
                    except Exception as e:
                        logger.error(f"Error al procesar historial de turnos: {e}")
                        
        except Exception as e:
            logger.error(f"Error al limpiar historial de turnos: {e}", exc_info=True)
        
        # Hacer commit
        db.session.commit()
        
        return {
            'success': True,
            'eliminados': eliminados,
            'errores': errores,
            'message': f'Se eliminaron {eliminados} registros antiguos'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al eliminar turnos antiguos: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'eliminados': 0,
            'errores': 0
        }


def limpiar_todo(resolved_by: str = 'admin', dias_antiguedad: int = 30, eliminar_todo: bool = False) -> Dict[str, Any]:
    """
    Ejecuta todas las operaciones de limpieza.
    
    Args:
        resolved_by: Usuario que resuelve los cierres
        dias_antiguedad: Días de antigüedad para eliminar registros (ignorado si eliminar_todo=True)
        eliminar_todo: Si es True, elimina todos los registros anteriores
        
    Returns:
        dict: Resumen completo de las operaciones
    """
    logger.info("🧹 Iniciando limpieza del sistema...")
    
    # Resolver cierres pendientes
    resultado_cierres = resolver_todos_cierres_pendientes(resolved_by)
    
    # Eliminar turnos antiguos
    resultado_turnos = eliminar_turnos_anteriores(dias_antiguedad, eliminar_todo=eliminar_todo)
    
    return {
        'success': resultado_cierres['success'] and resultado_turnos['success'],
        'cierres': resultado_cierres,
        'turnos': resultado_turnos,
        'message': f"Cierres resueltos: {resultado_cierres.get('resueltos', 0)}, Registros eliminados: {resultado_turnos.get('eliminados', 0)}"
    }

