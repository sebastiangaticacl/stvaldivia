"""
Servicio para gestionar sesiones de caja (RegisterSession)
P0-001, P0-003, P0-010: Estado explícito de caja
"""
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from flask import current_app, session, request
from app.models import db
from app.models.pos_models import RegisterSession, PosRegister
from app.models.jornada_models import Jornada
from app.helpers.timezone_utils import CHILE_TZ
import hashlib
import logging
import json

logger = logging.getLogger(__name__)


class RegisterSessionService:
    """Servicio para gestionar sesiones de caja"""
    
    @staticmethod
    def get_active_session(register_id: str, jornada_id: Optional[int] = None) -> Optional[RegisterSession]:
        """
        Obtiene la sesión activa (OPEN) de una caja
        
        Args:
            register_id: ID de la caja
            jornada_id: ID de la jornada (opcional, para validación)
            
        Returns:
            RegisterSession activa o None
        """
        try:
            query = RegisterSession.query.filter_by(
                register_id=str(register_id),
                status='OPEN'
            )
            
            if jornada_id:
                query = query.filter_by(jornada_id=jornada_id)
            
            return query.first()
        except Exception as e:
            logger.error(f"Error al obtener sesión activa: {e}", exc_info=True)
            return None
    
    @staticmethod
    def open_session(
        register_id: str,
        employee_id: str,
        employee_name: str,
        jornada_id: int,
        initial_cash: Optional[float] = None
    ) -> Tuple[bool, Optional[RegisterSession], str]:
        """
        Abre una nueva sesión de caja
        
        Args:
            register_id: ID de la caja
            employee_id: ID del empleado
            employee_name: Nombre del empleado
            jornada_id: ID de la jornada (OBLIGATORIO)
            initial_cash: Monto inicial de efectivo (opcional)
            
        Returns:
            Tuple[bool, Optional[RegisterSession], str]: (éxito, sesión, mensaje)
        """
        try:
            # P0-002: Validar que existe jornada activa
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, None, "Jornada no encontrada"
            
            if jornada.estado_apertura != 'abierto':
                return False, None, f"La jornada no está abierta (estado: {jornada.estado_apertura})"
            
            # Verificar que no haya otra sesión OPEN para esta caja
            existing_session = RegisterSessionService.get_active_session(register_id, jornada_id)
            if existing_session:
                # Permitir retomar si la sesión abierta pertenece al mismo empleado
                if str(existing_session.opened_by_employee_id) == str(employee_id):
                    return True, existing_session, "Sesión ya estaba abierta (retomada)"
                return False, None, f"Ya existe una sesión abierta para esta caja (abierta por {existing_session.opened_by_employee_name})"
            
            # Generar idempotency_key
            key_data = f"{register_id}_{jornada_id}_{employee_id}_{datetime.now(CHILE_TZ).strftime('%Y%m%d%H%M')}"
            idempotency_key = hashlib.sha256(key_data.encode()).hexdigest()[:64]
            
            # Verificar que no exista sesión con esta key
            existing_key = RegisterSession.query.filter_by(idempotency_key_open=idempotency_key).first()
            if existing_key:
                return True, existing_key, "Sesión ya existe (idempotencia)"
            
            # Crear nueva sesión
            new_session = RegisterSession(
                register_id=str(register_id),
                opened_by_employee_id=str(employee_id),
                opened_by_employee_name=employee_name,
                opened_at=datetime.now(CHILE_TZ).replace(tzinfo=None),
                status='OPEN',
                shift_date=jornada.fecha_jornada,
                jornada_id=jornada_id,
                initial_cash=initial_cash,
                idempotency_key_open=idempotency_key
            )
            
            db.session.add(new_session)
            db.session.commit()
            
            # Registrar auditoría
            RegisterSessionService._log_audit(
                event_type='REGISTER_SESSION_OPENED',
                register_id=register_id,
                register_session_id=new_session.id,
                jornada_id=jornada_id,
                actor_user_id=employee_id,
                actor_name=employee_name,
                payload={'initial_cash': initial_cash}
            )
            
            # FASE 8: Emitir evento SocketIO para visor de cajas
            try:
                from app import socketio
                socketio.emit('register_activity', {
                    'register_id': register_id,
                    'action': 'opened',
                    'cashier_id': employee_id,
                    'cashier_name': employee_name,
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                }, namespace='/admin')
            except Exception as e:
                logger.warning(f"Error al emitir evento de apertura de caja: {e}")
            
            logger.info(f"✅ Sesión de caja abierta: {register_id} por {employee_name} (Jornada {jornada_id})")
            return True, new_session, "Sesión abierta correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al abrir sesión de caja: {e}", exc_info=True)
            return False, None, f"Error al abrir sesión: {str(e)}"
    
    @staticmethod
    def start_close_session(register_session_id: int, employee_id: str, employee_name: str) -> Tuple[bool, str]:
        """
        Inicia el cierre de una sesión (cambia a PENDING_CLOSE)
        
        Args:
            register_session_id: ID de la sesión
            employee_id: ID del empleado que inicia el cierre
            employee_name: Nombre del empleado
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            register_session = RegisterSession.query.get(register_session_id)
            if not register_session:
                return False, "Sesión no encontrada"
            
            if register_session.status != 'OPEN':
                return False, f"La sesión no está abierta (estado: {register_session.status})"
            
            register_session.status = 'PENDING_CLOSE'
            db.session.commit()
            
            # FASE 8: Emitir evento SocketIO para visor de cajas
            try:
                from app import socketio
                from datetime import datetime
                from app.helpers.timezone_utils import CHILE_TZ
                socketio.emit('register_activity', {
                    'register_id': register_session.register_id,
                    'action': 'pending_close',
                    'cashier_id': employee_id,
                    'cashier_name': employee_name,
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                }, namespace='/admin')
            except Exception as e:
                logger.warning(f"Error al emitir evento de cierre pendiente: {e}")
            
            # Registrar auditoría
            RegisterSessionService._log_audit(
                event_type='REGISTER_SESSION_PENDING_CLOSE',
                register_id=register_session.register_id,
                register_session_id=register_session_id,
                jornada_id=register_session.jornada_id,
                actor_user_id=employee_id,
                actor_name=employee_name
            )
            
            logger.info(f"✅ Sesión {register_session_id} en estado PENDING_CLOSE")
            return True, "Cierre iniciado"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al iniciar cierre de sesión: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def close_session(
        register_session_id: int,
        closed_by: str,
        employee_id: Optional[str] = None,
        cash_count: Optional[Dict[str, Any]] = None,
        close_notes: Optional[str] = None,
        incidents: Optional[list] = None
    ) -> Tuple[bool, str]:
        """
        Cierra una sesión (cambia a CLOSED) con arqueo y totales
        
        Args:
            register_session_id: ID de la sesión
            closed_by: Nombre de quien cierra
            employee_id: ID del empleado (opcional)
            cash_count: Dict con conteo de efectivo por denominación (opcional)
            close_notes: Notas del cierre (opcional)
            incidents: Lista de incidentes durante la sesión (opcional)
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            register_session = RegisterSession.query.get(register_session_id)
            if not register_session:
                return False, "Sesión no encontrada"
            
            if register_session.status not in ['OPEN', 'PENDING_CLOSE']:
                return False, f"La sesión no puede cerrarse (estado: {register_session.status})"
            
            # MVP1: Calcular totales y diferencias antes de cerrar
            from app.models.pos_models import PosSale
            from sqlalchemy import func
            
            # NOTA: PosSale NO tiene register_session_id FK
            # Asociación por register_id + shift_date + ventana temporal (opened_at..closed_at)
            # Esto permite calcular totales de la sesión específica incluso si hay múltiples sesiones del mismo día
            
            # Construir query base con filtros
            base_filter = db.session.query(PosSale).filter(
                PosSale.register_id == register_session.register_id,
                PosSale.shift_date == register_session.shift_date,
                PosSale.is_cancelled == False,
                PosSale.no_revenue == False
            )
            
            # Filtrar por ventana temporal de la sesión (opened_at hasta ahora)
            # Esto asegura que solo contamos ventas de ESTA sesión específica
            if register_session.opened_at:
                opened_at_naive = register_session.opened_at
                if opened_at_naive.tzinfo:
                    opened_at_naive = opened_at_naive.replace(tzinfo=None)
                base_filter = base_filter.filter(PosSale.created_at >= opened_at_naive)
            
            # Obtener ventas de esta sesión
            sales_query = base_filter
            
            # BIMBA: Calcular totales por método de pago (cash/debit/credit)
            payment_totals_result = db.session.query(
                func.sum(PosSale.payment_cash).label('cash'),
                func.sum(PosSale.payment_debit).label('debit'),
                func.sum(PosSale.payment_credit).label('credit')
            ).filter(
                PosSale.register_id == register_session.register_id,
                PosSale.shift_date == register_session.shift_date,
                PosSale.is_cancelled == False,
                PosSale.no_revenue == False
            )
            
            # Aplicar ventana temporal también en agregación
            if register_session.opened_at:
                opened_at_naive = register_session.opened_at
                if opened_at_naive.tzinfo:
                    opened_at_naive = opened_at_naive.replace(tzinfo=None)
                payment_totals_result = payment_totals_result.filter(PosSale.created_at >= opened_at_naive)
            
            payment_totals_result = payment_totals_result.first()
            
            payment_totals = {
                'cash': float(payment_totals_result.cash or 0) if payment_totals_result else 0.0,
                'debit': float(payment_totals_result.debit or 0) if payment_totals_result else 0.0,
                'credit': float(payment_totals_result.credit or 0) if payment_totals_result else 0.0
            }
            
            # BIMBA: Calcular totales por provider (GETNET/KLAP/NONE) para conciliación
            provider_totals_result = db.session.query(
                PosSale.payment_provider,
                func.sum(PosSale.total_amount).label('total')
            ).filter(
                PosSale.register_id == register_session.register_id,
                PosSale.shift_date == register_session.shift_date,
                PosSale.is_cancelled == False,
                PosSale.no_revenue == False
            )
            
            # Aplicar ventana temporal
            if register_session.opened_at:
                opened_at_naive = register_session.opened_at
                if opened_at_naive.tzinfo:
                    opened_at_naive = opened_at_naive.replace(tzinfo=None)
                provider_totals_result = provider_totals_result.filter(PosSale.created_at >= opened_at_naive)
            
            provider_totals_result = provider_totals_result.group_by(PosSale.payment_provider).all()
            
            # Construir dict de totales por provider
            provider_totals = {}
            payment_provider_used_primary_count = 0
            payment_provider_used_backup_count = 0
            
            for row in provider_totals_result:
                provider = row.payment_provider or 'NONE'
                total = float(row.total or 0)
                provider_totals[provider] = total
                
                # Contar transacciones por provider
                if provider == 'GETNET':
                    payment_provider_used_primary_count = db.session.query(func.count(PosSale.id)).filter(
                        PosSale.register_id == register_session.register_id,
                        PosSale.shift_date == register_session.shift_date,
                        PosSale.payment_provider == 'GETNET',
                        PosSale.is_cancelled == False,
                        PosSale.no_revenue == False
                    )
                    if register_session.opened_at:
                        opened_at_naive = register_session.opened_at
                        if opened_at_naive.tzinfo:
                            opened_at_naive = opened_at_naive.replace(tzinfo=None)
                        payment_provider_used_primary_count = payment_provider_used_primary_count.filter(
                            PosSale.created_at >= opened_at_naive
                        )
                    payment_provider_used_primary_count = payment_provider_used_primary_count.scalar() or 0
                elif provider == 'KLAP':
                    payment_provider_used_backup_count = db.session.query(func.count(PosSale.id)).filter(
                        PosSale.register_id == register_session.register_id,
                        PosSale.shift_date == register_session.shift_date,
                        PosSale.payment_provider == 'KLAP',
                        PosSale.is_cancelled == False,
                        PosSale.no_revenue == False
                    )
                    if register_session.opened_at:
                        opened_at_naive = register_session.opened_at
                        if opened_at_naive.tzinfo:
                            opened_at_naive = opened_at_naive.replace(tzinfo=None)
                        payment_provider_used_backup_count = payment_provider_used_backup_count.filter(
                            PosSale.created_at >= opened_at_naive
                        )
                    payment_provider_used_backup_count = payment_provider_used_backup_count.scalar() or 0
            
            # Agregar provider_totals al payment_totals para reportes
            payment_totals['by_provider'] = provider_totals
            
            # Contar tickets (número de ventas)
            ticket_count = sales_query.count()
            
            # Calcular diferencia de efectivo
            cash_difference = None
            if cash_count:
                # Obtener total de efectivo contado
                total_cash_counted = cash_count.get('total', 0.0)
                if isinstance(total_cash_counted, (int, float)):
                    # Calcular efectivo esperado: initial_cash + ventas en efectivo
                    initial_cash_amount = float(register_session.initial_cash or 0)
                    cash_from_sales = payment_totals['cash']
                    expected_cash = initial_cash_amount + cash_from_sales
                    
                    # Diferencia = contado - esperado
                    cash_difference = total_cash_counted - expected_cash
            
            # Guardar datos en la sesión
            register_session.status = 'CLOSED'
            register_session.closed_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
            register_session.closed_by = closed_by
            
            # MVP1: Guardar campos nuevos
            if cash_count:
                register_session.cash_count = json.dumps(cash_count)
            register_session.payment_totals = json.dumps(payment_totals)
            register_session.ticket_count = ticket_count
            if cash_difference is not None:
                register_session.cash_difference = cash_difference
            if incidents:
                register_session.incidents = json.dumps(incidents)
            if close_notes:
                register_session.close_notes = close_notes
            
            # BIMBA: Guardar contadores de providers para conciliación
            register_session.payment_provider_used_primary_count = payment_provider_used_primary_count
            register_session.payment_provider_used_backup_count = payment_provider_used_backup_count
            
            db.session.commit()
            
            # FASE 8: Emitir evento SocketIO para visor de cajas
            try:
                from app import socketio
                socketio.emit('register_activity', {
                    'register_id': register_session.register_id,
                    'action': 'closed',
                    'cashier_id': employee_id or closed_by,
                    'cashier_name': closed_by,
                    'timestamp': datetime.now(CHILE_TZ).isoformat()
                }, namespace='/admin')
            except Exception as e:
                logger.warning(f"Error al emitir evento de cierre: {e}")
            
            # Registrar auditoría
            RegisterSessionService._log_audit(
                event_type='REGISTER_SESSION_CLOSED',
                register_id=register_session.register_id,
                register_session_id=register_session_id,
                jornada_id=register_session.jornada_id,
                actor_user_id=employee_id or closed_by,
                actor_name=closed_by
            )
            
            logger.info(f"✅ Sesión {register_session_id} cerrada por {closed_by}")
            return True, "Sesión cerrada correctamente"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error al cerrar sesión: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    @staticmethod
    def can_sell_in_register(register_id: str, jornada_id: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """
        Verifica si se pueden hacer ventas en una caja (P0-005)
        
        Args:
            register_id: ID de la caja
            jornada_id: ID de la jornada (opcional)
            
        Returns:
            Tuple[bool, Optional[str]]: (puede_vender, mensaje_error)
        """
        try:
            # Buscar sesión activa
            active_session = RegisterSessionService.get_active_session(register_id, jornada_id)
            
            if not active_session:
                return False, "No hay sesión abierta para esta caja. Debe abrir la caja antes de vender."
            
            if not active_session.can_sell():
                return False, f"La caja está en estado {active_session.status}. No se pueden hacer ventas."
            
            # Validar jornada activa
            jornada = Jornada.query.get(active_session.jornada_id)
            if not jornada:
                return False, "Jornada asociada no encontrada"
            
            if jornada.estado_apertura != 'abierto':
                return False, f"La jornada no está abierta (estado: {jornada.estado_apertura})"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error al verificar si se puede vender: {e}", exc_info=True)
            return False, f"Error al verificar estado de caja: {str(e)}"
    
    @staticmethod
    def _log_audit(
        event_type: str,
        register_id: Optional[str] = None,
        register_session_id: Optional[int] = None,
        jornada_id: Optional[int] = None,
        actor_user_id: Optional[str] = None,
        actor_name: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = 'info'
    ):
        """Registra evento de auditoría (P0-013, P0-014)"""
        try:
            from app.models.pos_models import SaleAuditLog
            import json
            
            audit_log = SaleAuditLog(
                event_type=event_type,
                severity=severity,
                actor_user_id=actor_user_id or session.get('pos_employee_id') or session.get('admin_username'),
                actor_name=actor_name or session.get('pos_employee_name') or session.get('admin_username', 'Sistema'),
                register_id=register_id,
                register_session_id=register_session_id,
                jornada_id=jornada_id,
                payload_json=json.dumps(payload) if payload else None,
                ip_address=request.remote_addr if request else None,
                session_id=session.get('session_id')
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error al registrar auditoría: {e}", exc_info=True)
            # No fallar la operación principal si falla la auditoría

