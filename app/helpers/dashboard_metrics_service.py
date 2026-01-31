"""
Servicio de Métricas del Dashboard
Calcula todas las métricas, indicadores y reportes para el dashboard administrativo
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_, or_, distinct, extract
from app.helpers.timezone_utils import CHILE_TZ
from app.models import db
from app.helpers.thread_safe_cache import get_cached_shift_info, set_cached_shift_info
import logging

logger = logging.getLogger(__name__)


class DashboardMetricsService:
    """Servicio para calcular métricas del dashboard"""
    
    def __init__(self):
        self.cache_ttl = 30  # Cache de 30 segundos para métricas
    
    def get_all_metrics(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Obtiene todas las métricas del dashboard
        
        Args:
            use_cache: Si usar caché o forzar recálculo
            
        Returns:
            Dict con todas las métricas organizadas
        """
        cache_key = 'dashboard_metrics'
        
        if use_cache:
            cached_metrics = get_cached_shift_info(cache_key)
            if cached_metrics:
                return cached_metrics
        
        try:
            metrics = {
                'system_status': self._get_system_status(),
                'turno_actual': self._get_turno_actual_metrics(),
                'ventas': self._get_ventas_metrics(),
                'entregas': self._get_entregas_metrics(),
                'cajas': self._get_cajas_metrics(),
                'kioskos': self._get_kioskos_metrics(),
                'equipo': self._get_equipo_metrics(),
                'inventario': self._get_inventario_metrics(),
                'guardarropia': self._get_guardarropia_metrics(),
                'encuestas': self._get_encuestas_metrics(),
                'comparativas': self._get_comparativas(),
                'graficos': self._get_graficos_data(),
                'alertas': self._get_alertas_proactivas(),
                'timestamp': datetime.now(CHILE_TZ).isoformat()
            }
            
            # Guardar en caché
            set_cached_shift_info(metrics, cache_key, self.cache_ttl)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculando métricas del dashboard: {e}", exc_info=True)
            return self._get_empty_metrics()
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Obtiene el estado del sistema"""
        try:
            from app.models.jornada_models import Jornada
            from sqlalchemy.exc import OperationalError, DisconnectionError
            
            try:
                jornada_abierta = Jornada.query.filter_by(
                    estado_apertura='abierto',
                    eliminado_en=None
                ).order_by(Jornada.fecha_jornada.desc()).first()
            except (OperationalError, DisconnectionError) as db_error:
                # BD no disponible - retornar estado sin BD
                logger.warning(f"BD no disponible al obtener estado del sistema: {db_error}")
                return {
                    'estado': 'indeterminado',
                    'icon': '⚠️',
                    'color': 'warning',
                    'mensaje': 'Sistema operativo (BD no disponible)',
                    'fecha': None,
                    'tipo': None,
                    'horas_abierto': None
                }
            
            if jornada_abierta:
                horas_abierto = None
                if jornada_abierta.abierto_en:
                    ahora = datetime.now(CHILE_TZ)
                    # Convertir abierto_en a timezone-aware si es naive
                    abierto_en = jornada_abierta.abierto_en
                    if abierto_en.tzinfo is None:
                        # Si es naive, asumir que está en CHILE_TZ
                        abierto_en = CHILE_TZ.localize(abierto_en)
                    diferencia = ahora - abierto_en
                    horas_abierto = round(diferencia.total_seconds() / 3600, 1)
                
                return {
                    'estado': 'abierto',
                    'icon': '🟢',
                    'color': 'success',
                    'mensaje': f'Turno Abierto: {jornada_abierta.nombre_fiesta or "Sin nombre"}',
                    'fecha': jornada_abierta.fecha_jornada,
                    'tipo': jornada_abierta.tipo_turno,
                    'horas_abierto': horas_abierto,
                    'abierto_por': jornada_abierta.abierto_por,
                    'abierto_en': jornada_abierta.abierto_en.isoformat() if jornada_abierta.abierto_en else None
                }
            else:
                return {
                    'estado': 'cerrado',
                    'icon': '⏰',
                    'color': 'warning',
                    'mensaje': 'No hay turno abierto',
                    'fecha': None,
                    'tipo': None,
                    'horas_abierto': None
                }
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}", exc_info=True)
            return {
                'estado': 'error',
                'icon': '❌',
                'color': 'danger',
                'mensaje': 'Error al obtener estado',
                'fecha': None,
                'tipo': None,
                'horas_abierto': None
            }
    
    def _get_turno_actual_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del turno actual"""
        try:
            from app.models.jornada_models import Jornada, PlanillaTrabajador
            
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            if not jornada_abierta:
                return {
                    'existe': False,
                    'costo_total': 0,
                    'planilla_count': 0
                }
            
            planilla = PlanillaTrabajador.query.filter_by(jornada_id=jornada_abierta.id).all()
            costo_total = sum(float(t.costo_total) if t.costo_total else 0 for t in planilla)
            
            # Calcular tiempo transcurrido
            tiempo_transcurrido = None
            if jornada_abierta.abierto_en:
                ahora = datetime.now(CHILE_TZ)
                abierto_en = jornada_abierta.abierto_en
                if abierto_en.tzinfo is None:
                    abierto_en = CHILE_TZ.localize(abierto_en)
                diferencia = ahora - abierto_en
                horas = int(diferencia.total_seconds() // 3600)
                minutos = int((diferencia.total_seconds() % 3600) // 60)
                tiempo_transcurrido = f"{horas}h {minutos}m"
            
            return {
                'existe': True,
                'id': jornada_abierta.id,
                'nombre': jornada_abierta.nombre_fiesta,
                'fecha': jornada_abierta.fecha_jornada,
                'tipo': jornada_abierta.tipo_turno,
                'costo_total': costo_total,
                'planilla_count': len(planilla),
                'abierto_en': jornada_abierta.abierto_en.isoformat() if jornada_abierta.abierto_en else None,
                'tiempo_transcurrido': tiempo_transcurrido
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas del turno: {e}", exc_info=True)
            return {'existe': False, 'costo_total': 0, 'planilla_count': 0}
    
    def _get_ventas_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de ventas"""
        try:
            from app.models.pos_models import PosSale
            from app.models.jornada_models import Jornada
            from app.models import db
            
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            fecha_ayer = (datetime.now(CHILE_TZ) - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Obtener jornada abierta
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Ventas del turno actual
            ventas_turno = {
                'total': 0,
                'monto': 0.0,
                'cash': 0.0,
                'debit': 0.0,
                'credit': 0.0
            }
            
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                # Filtrar ventas válidas: excluir canceladas, pruebas, no revenue y cortesías
                ventas_query = PosSale.query.filter(
                    PosSale.created_at >= opened_dt,
                    PosSale.is_cancelled == False,  # Excluir canceladas
                    PosSale.is_test == False,  # Excluir pruebas
                    PosSale.no_revenue == False,  # Excluir no revenue
                    PosSale.is_courtesy == False  # Excluir cortesías
                )
                
                ventas_turno['total'] = ventas_query.count()
                
                totals = db.session.query(
                    func.sum(PosSale.total_amount).label('total'),
                    func.sum(PosSale.payment_cash).label('cash'),
                    func.sum(PosSale.payment_debit).label('debit'),
                    func.sum(PosSale.payment_credit).label('credit')
                ).filter(
                    PosSale.created_at >= opened_dt,
                    PosSale.is_cancelled == False,
                    PosSale.is_test == False,
                    PosSale.no_revenue == False,
                    PosSale.is_courtesy == False
                ).first()
                
                if totals:
                    ventas_turno['monto'] = float(totals.total or 0)
                    ventas_turno['cash'] = float(totals.cash or 0)
                    ventas_turno['debit'] = float(totals.debit or 0)
                    ventas_turno['credit'] = float(totals.credit or 0)
            
            # Ventas de hoy
            ventas_hoy = {
                'total': PosSale.query.filter(PosSale.shift_date == fecha_hoy).count(),
                'monto': 0.0
            }
            
            total_hoy = db.session.query(func.sum(PosSale.total_amount)).filter(
                PosSale.shift_date == fecha_hoy
            ).scalar() or 0
            ventas_hoy['monto'] = float(total_hoy)
            
            # Ventas de ayer
            ventas_ayer = {
                'total': PosSale.query.filter(PosSale.shift_date == fecha_ayer).count(),
                'monto': 0.0
            }
            
            total_ayer = db.session.query(func.sum(PosSale.total_amount)).filter(
                PosSale.shift_date == fecha_ayer
            ).scalar() or 0
            ventas_ayer['monto'] = float(total_ayer)
            
            return {
                'turno': ventas_turno,
                'hoy': ventas_hoy,
                'ayer': ventas_ayer
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de ventas: {e}", exc_info=True)
            return {
                'turno': {'total': 0, 'monto': 0.0},
                'hoy': {'total': 0, 'monto': 0.0},
                'ayer': {'total': 0, 'monto': 0.0}
            }
    
    def _get_entregas_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de entregas"""
        try:
            from app.models.delivery_models import Delivery
            from app.models.jornada_models import Jornada
            
            fecha_hoy = datetime.now(CHILE_TZ).date()
            fecha_ayer = (datetime.now(CHILE_TZ) - timedelta(days=1)).date()
            
            # Obtener jornada abierta
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Entregas del turno
            entregas_turno = 0
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                entregas_turno = Delivery.query.filter(
                    Delivery.timestamp >= opened_dt
                ).count()
            
            # Entregas de hoy (usando fecha del timestamp)
            entregas_hoy = Delivery.query.filter(
                func.date(Delivery.timestamp) == fecha_hoy
            ).count()
            
            # Entregas de ayer
            entregas_ayer = Delivery.query.filter(
                func.date(Delivery.timestamp) == fecha_ayer
            ).count()
            
            return {
                'turno': entregas_turno,
                'hoy': entregas_hoy,
                'ayer': entregas_ayer
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de entregas: {e}", exc_info=True)
            return {'turno': 0, 'hoy': 0, 'ayer': 0}
    
    def _get_cajas_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de cajas"""
        try:
            from app.models.pos_models import RegisterLock, RegisterClose, PosSale
            from app.helpers.register_lock_db import get_all_register_locks
            
            # Cajas abiertas (bloqueadas)
            locks = get_all_register_locks()
            cajas_abiertas = len([l for l in locks if l])
            
            # Cierres pendientes (cajas que tienen ventas pero no se han cerrado)
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            
            # Obtener cajas con ventas de hoy
            cajas_con_ventas = db.session.query(distinct(PosSale.register_id)).filter(
                PosSale.shift_date == fecha_hoy
            ).all()
            
            cajas_cerradas_hoy = db.session.query(distinct(RegisterClose.register_id)).filter(
                RegisterClose.shift_date == fecha_hoy
            ).all()
            
            cierres_pendientes = len(cajas_con_ventas) - len(cajas_cerradas_hoy)
            if cierres_pendientes < 0:
                cierres_pendientes = 0
            
            return {
                'abiertas': cajas_abiertas,
                'cierres_pendientes': cierres_pendientes,
                'total_bloqueadas': cajas_abiertas
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de cajas: {e}", exc_info=True)
            return {'abiertas': 0, 'cierres_pendientes': 0}
    
    def _get_kioskos_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de kioskos"""
        try:
            from app.models.kiosk_models import Pago
            from app.models.jornada_models import Jornada
            
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Pagos del turno
            pagos_turno = 0
            monto_turno = 0.0
            
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                pagos_query = Pago.query.filter(
                    Pago.created_at >= opened_dt,
                    Pago.estado == 'PAID'
                )
                
                pagos_turno = pagos_query.count()
                
                monto = db.session.query(func.sum(Pago.monto)).filter(
                    Pago.created_at >= opened_dt,
                    Pago.estado == 'PAID'
                ).scalar() or 0
                
                monto_turno = float(monto)
            
            # Pagos pendientes
            pagos_pendientes = Pago.query.filter(
                Pago.estado == 'PENDING'
            ).count()
            
            return {
                'pagos_turno': pagos_turno,
                'monto_turno': monto_turno,
                'pagos_pendientes': pagos_pendientes
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de kioskos: {e}", exc_info=True)
            return {'pagos_turno': 0, 'monto_turno': 0.0, 'pagos_pendientes': 0}
    
    def _get_equipo_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del equipo"""
        try:
            from app.models.jornada_models import Jornada, PlanillaTrabajador
            from app.models.pos_models import Employee
            
            # Trabajadores en turno actual
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            total_trabajadores = 0
            if jornada_abierta:
                planilla = PlanillaTrabajador.query.filter_by(jornada_id=jornada_abierta.id).all()
                total_trabajadores = len(planilla)
            
            # Total de empleados activos
            empleados_activos = Employee.query.filter_by(is_active=True).count()
            
            return {
                'total_trabajadores': total_trabajadores,
                'empleados_activos': empleados_activos
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de equipo: {e}", exc_info=True)
            return {'total_trabajadores': 0, 'empleados_activos': 0}
    
    def _get_comparativas(self) -> Dict[str, Any]:
        """Obtiene comparativas (hoy vs ayer)"""
        try:
            ventas = self._get_ventas_metrics()
            entregas = self._get_entregas_metrics()
            
            # Comparativa de ventas
            ventas_hoy = ventas.get('hoy', {}).get('monto', 0)
            ventas_ayer = ventas.get('ayer', {}).get('monto', 0)
            
            variacion_ventas = 0
            tendencia_ventas = 'equal'
            if ventas_ayer > 0:
                variacion_ventas = ((ventas_hoy - ventas_ayer) / ventas_ayer) * 100
                tendencia_ventas = 'up' if variacion_ventas > 0 else 'down' if variacion_ventas < 0 else 'equal'
            
            # Comparativa de entregas
            entregas_hoy = entregas.get('hoy', 0)
            entregas_ayer = entregas.get('ayer', 0)
            
            variacion_entregas = 0
            tendencia_entregas = 'equal'
            if entregas_ayer > 0:
                variacion_entregas = ((entregas_hoy - entregas_ayer) / entregas_ayer) * 100
                tendencia_entregas = 'up' if variacion_entregas > 0 else 'down' if variacion_entregas < 0 else 'equal'
            
            return {
                'ventas': {
                    'hoy': ventas_hoy,
                    'ayer': ventas_ayer,
                    'variacion': round(variacion_ventas, 1),
                    'tendencia': tendencia_ventas
                },
                'entregas': {
                    'hoy': entregas_hoy,
                    'ayer': entregas_ayer,
                    'variacion': round(variacion_entregas, 1),
                    'tendencia': tendencia_entregas
                }
            }
        except Exception as e:
            logger.error(f"Error obteniendo comparativas: {e}", exc_info=True)
            return {
                'ventas': {'hoy': 0, 'ayer': 0, 'variacion': 0, 'tendencia': 'equal'},
                'entregas': {'hoy': 0, 'ayer': 0, 'variacion': 0, 'tendencia': 'equal'}
            }
    
    def _get_graficos_data(self) -> Dict[str, Any]:
        """Obtiene datos para los gráficos"""
        try:
            from app.models.pos_models import PosSale
            from app.models.jornada_models import Jornada
            
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            
            # Obtener jornada abierta
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Ventas por hora (del turno actual)
            ventas_por_hora = {}
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                # Agrupar por hora
                ventas_hora = db.session.query(
                    extract('hour', PosSale.created_at).label('hora'),
                    func.sum(PosSale.total_amount).label('total')
                ).filter(
                    PosSale.created_at >= opened_dt
                ).group_by(
                    extract('hour', PosSale.created_at)
                ).all()
                
                for hora, total in ventas_hora:
                    ventas_por_hora[str(int(hora))] = float(total or 0)
            
            # Métodos de pago (del turno actual)
            metodos_pago = {'cash': 0.0, 'debit': 0.0, 'credit': 0.0}
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                totals = db.session.query(
                    func.sum(PosSale.payment_cash).label('cash'),
                    func.sum(PosSale.payment_debit).label('debit'),
                    func.sum(PosSale.payment_credit).label('credit')
                ).filter(PosSale.created_at >= opened_dt).first()
                
                if totals:
                    metodos_pago['cash'] = float(totals.cash or 0)
                    metodos_pago['debit'] = float(totals.debit or 0)
                    metodos_pago['credit'] = float(totals.credit or 0)
            
            # Ventas por caja (del turno actual)
            ventas_por_caja = {}
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                ventas_caja = db.session.query(
                    PosSale.register_id,
                    PosSale.register_name,
                    func.sum(PosSale.total_amount).label('monto'),
                    func.count(PosSale.id).label('cantidad')
                ).filter(
                    PosSale.created_at >= opened_dt
                ).group_by(
                    PosSale.register_id,
                    PosSale.register_name
                ).all()
                
                for register_id, register_name, monto, cantidad in ventas_caja:
                    ventas_por_caja[register_id] = {
                        'nombre': register_name or f'Caja {register_id}',
                        'monto': float(monto or 0),
                        'cantidad': int(cantidad or 0)
                    }
            
            # Top productos del turno
            top_productos = []
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                from app.models.delivery_models import Delivery
                productos_query = db.session.query(
                    Delivery.item_name,
                    func.count(Delivery.id).label('cantidad')
                ).filter(
                    Delivery.timestamp >= opened_dt
                ).group_by(
                    Delivery.item_name
                ).order_by(
                    func.count(Delivery.id).desc()
                ).limit(5).all()
                
                top_productos = [(p[0], int(p[1])) for p in productos_query if p[0]]
            
            # Top bartenders del turno
            top_bartenders = []
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                bartenders_query = db.session.query(
                    Delivery.bartender,
                    func.count(Delivery.id).label('cantidad')
                ).filter(
                    Delivery.timestamp >= opened_dt,
                    Delivery.bartender.isnot(None)
                ).group_by(
                    Delivery.bartender
                ).order_by(
                    func.count(Delivery.id).desc()
                ).limit(5).all()
                
                top_bartenders = [(b[0], int(b[1])) for b in bartenders_query if b[0]]
            
            # Barra más activa
            barra_mas_activa = None
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                barra_query = db.session.query(
                    Delivery.barra,
                    func.count(Delivery.id).label('cantidad')
                ).filter(
                    Delivery.timestamp >= opened_dt,
                    Delivery.barra.isnot(None)
                ).group_by(
                    Delivery.barra
                ).order_by(
                    func.count(Delivery.id).desc()
                ).first()
                
                if barra_query:
                    barra_mas_activa = {
                        'nombre': barra_query[0],
                        'cantidad': int(barra_query[1])
                    }
            
            return {
                'ventas_por_hora': ventas_por_hora,
                'metodos_pago': metodos_pago,
                'ventas_por_caja': ventas_por_caja,
                'top_productos': top_productos,
                'top_bartenders': top_bartenders,
                'barra_mas_activa': barra_mas_activa
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos de gráficos: {e}", exc_info=True)
            return {
                'ventas_por_hora': {},
                'metodos_pago': {'cash': 0, 'debit': 0, 'credit': 0},
                'ventas_por_caja': {}
            }
    
    def _get_alertas_proactivas(self) -> List[Dict[str, Any]]:
        """Obtiene alertas proactivas del sistema"""
        alertas = []
        
        try:
            from app.models.jornada_models import Jornada
            from app.models.pos_models import RegisterLock, RegisterClose, PosSale
            from app.helpers.register_lock_db import get_all_register_locks
            
            # Alerta 1: Turno abierto por mucho tiempo
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            if jornada_abierta and jornada_abierta.abierto_en:
                ahora = datetime.now(CHILE_TZ)
                # Convertir abierto_en a timezone-aware si es naive
                abierto_en = jornada_abierta.abierto_en
                if abierto_en.tzinfo is None:
                    # Si es naive, asumir que está en CHILE_TZ
                    abierto_en = CHILE_TZ.localize(abierto_en)
                diferencia = ahora - abierto_en
                horas_abierto = diferencia.total_seconds() / 3600
                
                if horas_abierto > 12:
                    alertas.append({
                        'tipo': 'warning',
                        'icon': '⏰',
                        'titulo': 'Turno abierto por mucho tiempo',
                        'mensaje': f'El turno lleva abierto {round(horas_abierto, 1)} horas. Considera cerrarlo.',
                        'accion': '/admin/turnos'
                    })
            
            # Alerta 2: Cajas bloqueadas por mucho tiempo
            locks = get_all_register_locks()
            for lock in locks:
                if lock and lock.get('locked_at'):
                    try:
                        locked_at = datetime.fromisoformat(lock['locked_at'].replace('Z', '+00:00'))
                        if locked_at.tzinfo:
                            locked_at = locked_at.replace(tzinfo=None)
                        
                        ahora = datetime.utcnow()
                        diferencia = ahora - locked_at
                        minutos_bloqueada = diferencia.total_seconds() / 60
                        
                        if minutos_bloqueada > 60:  # Más de 1 hora
                            alertas.append({
                                'tipo': 'warning',
                                'icon': '💰',
                                'titulo': f'Caja {lock.get("register_id", "N/A")} bloqueada',
                                'mensaje': f'La caja lleva bloqueada {round(minutos_bloqueada)} minutos por {lock.get("employee_name", "N/A")}',
                                'accion': '/admin/pos_stats'
                            })
                    except Exception as e:
                        logger.warning(f"Error procesando lock: {e}")
                        continue
            
            # Alerta 3: Cierres de caja pendientes
            fecha_hoy = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            from app.models.pos_models import PosSale
            from sqlalchemy import distinct
            
            cajas_con_ventas = db.session.query(distinct(PosSale.register_id)).filter(
                PosSale.shift_date == fecha_hoy
            ).all()
            
            cajas_cerradas_hoy = db.session.query(distinct(RegisterClose.register_id)).filter(
                RegisterClose.shift_date == fecha_hoy
            ).all()
            
            cierres_pendientes = len(cajas_con_ventas) - len(cajas_cerradas_hoy)
            if cierres_pendientes > 0:
                alertas.append({
                    'tipo': 'info',
                    'icon': '📋',
                    'titulo': 'Cierres de caja pendientes',
                    'mensaje': f'Hay {cierres_pendientes} caja(s) con ventas que aún no se han cerrado',
                    'accion': '/admin/pos_stats'
                })
            
            # Alerta 4: Sin turno abierto
            if not jornada_abierta:
                alertas.append({
                    'tipo': 'warning',
                    'icon': '⏰',
                    'titulo': 'No hay turno abierto',
                    'mensaje': 'El sistema no puede procesar operaciones sin un turno abierto',
                    'accion': '/admin/turnos'
                })
            
            # Alerta 5: Diferencias grandes en cierres de caja
            cierres_con_diferencias = RegisterClose.query.filter(
                RegisterClose.shift_date == fecha_hoy,
                RegisterClose.difference_total > 10000  # Más de $10,000 de diferencia
            ).all()
            
            if cierres_con_diferencias:
                for cierre in cierres_con_diferencias:
                    alertas.append({
                        'tipo': 'danger',
                        'icon': '⚠️',
                        'titulo': f'Gran diferencia en {cierre.register_name}',
                        'mensaje': f'Diferencia de ${float(cierre.difference_total):,.0f} en el cierre de caja',
                        'accion': '/admin/pos_stats'
                    })
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}", exc_info=True)
        
        return alertas
    
    def _get_inventario_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de inventario"""
        try:
            from app.models.product_models import Product
            from app.models.inventory_stock_models import Ingredient, Recipe, IngredientStock
            
            # Productos totales
            total_productos = Product.query.filter_by(is_active=True).count()
            
            # Ingredientes con stock bajo
            # Nota: IngredientStock tiene 'quantity', no 'current_stock' ni 'min_stock'
            # Por ahora, se deja en 0 o se podría definir un umbral fijo
            stock_bajo = 0  # TODO: Implementar lógica de stock mínimo si es necesario
            
            # Ingredientes totales
            total_ingredientes = Ingredient.query.filter_by(is_active=True).count()
            
            # Recetas totales
            total_recetas = Recipe.query.filter_by(is_active=True).count()
            
            # Productos sin receta
            productos_sin_receta = db.session.query(Product).filter(
                Product.is_active == True,
                ~Product.id.in_(
                    db.session.query(Recipe.product_id).filter(Recipe.is_active == True)
                )
            ).count()
            
            return {
                'total_productos': total_productos,
                'total_ingredientes': total_ingredientes,
                'total_recetas': total_recetas,
                'stock_bajo': stock_bajo,
                'productos_sin_receta': productos_sin_receta
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de inventario: {e}", exc_info=True)
            return {
                'total_productos': 0,
                'total_ingredientes': 0,
                'total_recetas': 0,
                'stock_bajo': 0,
                'productos_sin_receta': 0
            }
    
    def _get_guardarropia_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de guardarropía"""
        try:
            from app.models.guardarropia_ticket_models import GuardarropiaTicket
            from app.models.jornada_models import Jornada
            
            fecha_hoy = datetime.now(CHILE_TZ).date()
            
            # Obtener jornada abierta
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Items depositados hoy (tickets creados hoy con status open/paid/checked_in)
            items_depositados_hoy = GuardarropiaTicket.query.filter(
                func.date(GuardarropiaTicket.created_at) == fecha_hoy,
                GuardarropiaTicket.status.in_(['open', 'paid', 'checked_in'])
            ).count()
            
            # Items retirados hoy (tickets con checked_out_at hoy)
            items_retirados_hoy = GuardarropiaTicket.query.filter(
                func.date(GuardarropiaTicket.checked_out_at) == fecha_hoy,
                GuardarropiaTicket.status == 'checked_out'
            ).count()
            
            # Items pendientes (tickets creados pero no retirados)
            items_pendientes = GuardarropiaTicket.query.filter(
                GuardarropiaTicket.status.in_(['open', 'paid', 'checked_in'])
            ).count()
            
            # Recaudación hoy
            tickets_hoy = GuardarropiaTicket.query.filter(
                func.date(GuardarropiaTicket.created_at) == fecha_hoy
            ).all()
            
            revenue_hoy = sum(float(t.price or 0) for t in tickets_hoy if t.price)
            
            # Items del turno
            items_turno = 0
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                items_turno = GuardarropiaTicket.query.filter(
                    GuardarropiaTicket.created_at >= opened_dt
                ).count()
            
            return {
                'items_depositados_hoy': items_depositados_hoy,
                'items_retirados_hoy': items_retirados_hoy,
                'items_pendientes': items_pendientes,
                'revenue_hoy': revenue_hoy,
                'items_turno': items_turno
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de guardarropía: {e}", exc_info=True)
            return {
                'items_depositados_hoy': 0,
                'items_retirados_hoy': 0,
                'items_pendientes': 0,
                'revenue_hoy': 0.0,
                'items_turno': 0
            }
    
    def _get_encuestas_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas de encuestas"""
        try:
            from app.models.survey_models import SurveyResponse
            from app.models.jornada_models import Jornada
            
            fecha_hoy = datetime.now(CHILE_TZ).date()
            
            # Respuestas hoy
            respuestas_hoy = SurveyResponse.query.filter(
                func.date(SurveyResponse.created_at) == fecha_hoy
            ).count()
            
            # Total respuestas
            total_respuestas = SurveyResponse.query.count()
            
            # Obtener jornada abierta
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto',
                eliminado_en=None
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            # Respuestas del turno
            respuestas_turno = 0
            if jornada_abierta and jornada_abierta.abierto_en:
                opened_dt = jornada_abierta.abierto_en
                if opened_dt.tzinfo:
                    opened_dt = opened_dt.replace(tzinfo=None)
                
                respuestas_turno = SurveyResponse.query.filter(
                    SurveyResponse.created_at >= opened_dt
                ).count()
            
            # Promedio de calificación (últimas 24 horas)
            fecha_24h_atras = datetime.now(CHILE_TZ) - timedelta(hours=24)
            respuestas_24h = SurveyResponse.query.filter(
                SurveyResponse.created_at >= fecha_24h_atras
            ).all()
            
            promedio_calificacion = 0.0
            if respuestas_24h:
                calificaciones = [float(r.rating or 0) for r in respuestas_24h if r.rating]
                if calificaciones:
                    promedio_calificacion = sum(calificaciones) / len(calificaciones)
            
            return {
                'respuestas_hoy': respuestas_hoy,
                'respuestas_turno': respuestas_turno,
                'total_respuestas': total_respuestas,
                'promedio_calificacion': round(promedio_calificacion, 1)
            }
        except Exception as e:
            logger.error(f"Error obteniendo métricas de encuestas: {e}", exc_info=True)
            return {
                'respuestas_hoy': 0,
                'respuestas_turno': 0,
                'total_respuestas': 0,
                'promedio_calificacion': 0.0
            }
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Retorna métricas vacías en caso de error"""
        return {
            'system_status': {
                'estado': 'error',
                'icon': '❌',
                'color': 'danger',
                'mensaje': 'Error al cargar métricas'
            },
            'turno_actual': {'existe': False},
            'ventas': {'turno': {'total': 0, 'monto': 0}},
            'entregas': {'turno': 0, 'hoy': 0},
            'cajas': {'abiertas': 0},
            'kioskos': {'pagos_turno': 0},
            'equipo': {'total_trabajadores': 0},
            'inventario': {'total_productos': 0, 'stock_bajo': 0},
            'guardarropia': {'items_pendientes': 0, 'revenue_hoy': 0.0},
            'encuestas': {'respuestas_hoy': 0, 'promedio_calificacion': 0.0},
            'comparativas': {},
            'graficos': {},
            'alertas': []
        }


# Instancia singleton del servicio
_metrics_service_instance = None

def get_metrics_service() -> DashboardMetricsService:
    """Obtiene la instancia del servicio de métricas (singleton)"""
    global _metrics_service_instance
    if _metrics_service_instance is None:
        _metrics_service_instance = DashboardMetricsService()
    return _metrics_service_instance
