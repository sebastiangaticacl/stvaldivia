"""
Servicio de Aplicación: Gestión de Turnos (Shifts)
Contiene la lógica de casos de uso para abrir, cerrar y consultar turnos.
"""
from typing import Optional, Tuple
from datetime import datetime
from flask import current_app
import pytz

from app.domain.shift import Shift, ShiftStatus
from app.helpers.timezone_utils import CHILE_TZ
from app.domain.exceptions import ShiftNotOpenError, ShiftAlreadyOpenError
from app.application.dto.shift_dto import OpenShiftRequest, CloseShiftRequest
from app.infrastructure.repositories.shift_repository import ShiftRepository, JsonShiftRepository


class ShiftService:
    """
    Servicio de gestión de turnos.
    Encapsula la lógica de negocio de turnos.
    """
    
    def __init__(
        self,
        shift_repository: Optional[ShiftRepository] = None,
        event_publisher: Optional = None
    ):
        """
        Inicializa el servicio con repositorio y publisher opcionales.
        
        Args:
            shift_repository: Repositorio de turnos (por defecto JsonShiftRepository)
            event_publisher: Publisher de eventos (opcional)
        """
        self.shift_repository = shift_repository or JsonShiftRepository()
        self.event_publisher = event_publisher
    
    def open_shift(self, request: OpenShiftRequest) -> Tuple[bool, str]:
        """
        Abre un nuevo turno.
        
        Args:
            request: DTO con información para abrir turno
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
            
        Raises:
            ShiftAlreadyOpenError: Si ya hay un turno abierto
            ValueError: Si los datos del request son inválidos
        """
        # Validar request
        request.validate()
        
        # Verificar que no hay turno abierto
        current_status = self.shift_repository.get_current_shift_status()
        if current_status.is_open:
            raise ShiftAlreadyOpenError("Ya hay un turno abierto. Cierra el turno actual antes de abrir uno nuevo.")
        
        # Crear nueva entidad Shift usando hora de Chile
        now = datetime.now(CHILE_TZ)
        today = now.strftime('%Y-%m-%d')
        
        shift = Shift(
            shift_date=today,
            fiesta_nombre=request.fiesta_nombre,
            opened_at=now.isoformat(),
            opened_by=request.opened_by,
            djs=request.djs or '',
            barras_disponibles=request.barras_disponibles or [
                'Barra Principal',
                'Barra Terraza',
                'Barra VIP',
                'Barra Exterior'
            ],
            bartenders=request.bartenders or [],
            cashiers=request.cashiers or []
        )
        
        # Guardar estado del turno
        status = ShiftStatus(
            is_open=True,
            shift_date=today,
            opened_at=now.isoformat(),
            opened_by=request.opened_by,
            fiesta_nombre=request.fiesta_nombre,
            djs=request.djs or '',
            barras_disponibles=shift.barras_disponibles,
            bartenders=shift.bartenders,
            cashiers=shift.cashiers
        )
        
        if not self.shift_repository.save_shift_status(status):
            return False, "Error al guardar el estado del turno"
        
        current_app.logger.info(
            f"Turno abierto el {today} a las {now.isoformat()} por {request.opened_by} - "
            f"Fiesta: {request.fiesta_nombre}"
        )
        
        return True, f"Turno abierto correctamente para el día {today}"
    
    def close_shift(self, request: CloseShiftRequest) -> Tuple[bool, str]:
        """
        Cierra el turno actual.
        
        Args:
            request: DTO con información para cerrar turno
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
            
        Raises:
            ShiftNotOpenError: Si no hay un turno abierto
        """
        # Validar request
        request.validate()
        
        # Obtener turno actual
        current_status = self.shift_repository.get_current_shift_status()
        if not current_status.is_open:
            raise ShiftNotOpenError("No hay un turno abierto para cerrar.")
        
        # Crear entidad Shift con todos los datos
        shift = Shift(
            shift_date=current_status.shift_date or datetime.now().strftime('%Y-%m-%d'),
            fiesta_nombre=current_status.fiesta_nombre or '',
            opened_at=current_status.opened_at or '',
            opened_by=current_status.opened_by or 'admin',
            djs=current_status.djs or '',
            barras_disponibles=current_status.barras_disponibles or [],
            bartenders=current_status.bartenders or []
        )
        
        # Sincronizar ventas pendientes con PHP POS antes de cerrar el turno
        shift_date = shift.shift_date
        sync_message = ""
        try:
            from app.helpers.phppos_sync import sync_pending_sales_to_phppos
            sync_result = sync_pending_sales_to_phppos(shift_date=shift_date)
            
            if sync_result['synced_count'] > 0:
                sync_message = f" {sync_result['synced_count']} venta(s) sincronizada(s) con PHP POS."
            
            if sync_result['failed_count'] > 0:
                sync_message += f" {sync_result['failed_count']} venta(s) no se pudieron sincronizar."
                current_app.logger.warning(
                    f"⚠️  Algunas ventas no se pudieron sincronizar al cerrar turno {shift_date}: "
                    f"{', '.join(sync_result['errors'][:3])}"
                )
        except Exception as e:
            # No bloquear el cierre del turno si falla la sincronización
            current_app.logger.error(
                f"Error al sincronizar ventas al cerrar turno (no se bloquea el cierre): {e}",
                exc_info=True
            )
            sync_message = " (Error al sincronizar ventas, pero el turno se cerró correctamente)"
        
        # Cerrar turno
        closed_at = datetime.now()
        shift.close(closed_by=request.closed_by, closed_at=closed_at.isoformat())
        
        # Guardar en historial
        if not self.shift_repository.save_to_history(shift):
            return False, "Error al guardar el turno en el historial"
        
        # Marcar como cerrado
        current_status.is_open = False
        current_status.closed_at = closed_at.isoformat()
        current_status.closed_by = request.closed_by
        
        if not self.shift_repository.save_shift_status(current_status):
            return False, "Error al guardar el estado del turno"
        
        current_app.logger.info(
            f"Turno cerrado el {shift.shift_date} a las {closed_at.isoformat()} por {request.closed_by}"
        )
        
        message = f"Turno cerrado correctamente. Turno del día {shift.shift_date}.{sync_message}"
        return True, message
    
    def get_current_shift(self) -> Optional[ShiftStatus]:
        """
        Obtiene el turno actual.
        
        Returns:
            ShiftStatus: Estado del turno actual o None si no hay turno
        """
        status = self.shift_repository.get_current_shift_status()
        return status if status.is_open else None
    
    def is_shift_open(self) -> bool:
        """
        Verifica si hay un turno abierto.
        Usa el sistema de Jornadas (nuevo) primero, luego fallback al sistema legacy.
        Busca jornadas abiertas de cualquier fecha (no solo de hoy).
        
        Returns:
            bool: True si hay turno abierto, False en caso contrario
        """
        # Intentar usar el sistema de Jornadas primero (nuevo sistema)
        try:
            from app.models.jornada_models import Jornada
            from app.models import db
            from datetime import datetime
            
            # Buscar cualquier jornada abierta (no solo de hoy)
            # Esto permite reconocer turnos que se abrieron en días anteriores
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto'
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            if jornada_abierta:
                return True
        except Exception as e:
            current_app.logger.debug(f"Error verificando Jornada, usando fallback: {e}")
        
        # Fallback al sistema legacy (JSON)
        try:
            status = self.shift_repository.get_current_shift_status()
            return status.is_open
        except Exception as e:
            current_app.logger.error(f"Error verificando turno en repositorio legacy: {e}")
            return False
    
    def get_shift_history(self, limit: int = 30) -> list:
        """
        Obtiene el historial de turnos cerrados.
        
        Args:
            limit: Número máximo de turnos a retornar
            
        Returns:
            list: Lista de turnos cerrados (diccionarios)
        """
        return self.shift_repository.get_shift_history(limit=limit)
    
    def get_current_shift_status(self) -> ShiftStatus:
        """
        Obtiene el estado completo del turno actual (abierto o cerrado).
        Usa el sistema de Jornadas (nuevo) primero, luego fallback al sistema legacy.
        Busca jornadas abiertas de cualquier fecha (no solo de hoy).
        
        Returns:
            ShiftStatus: Estado del turno
        """
        # Intentar usar el sistema de Jornadas primero (nuevo sistema)
        try:
            from app.models.jornada_models import Jornada
            from app.models import db
            from datetime import datetime
            
            # Buscar cualquier jornada abierta (no solo de hoy)
            # Esto permite reconocer turnos que se abrieron en días anteriores
            jornada_abierta = Jornada.query.filter_by(
                estado_apertura='abierto'
            ).order_by(Jornada.fecha_jornada.desc()).first()
            
            if jornada_abierta:
                # Convertir Jornada a ShiftStatus
                import json
                barras = []
                if jornada_abierta.barras_disponibles:
                    try:
                        barras = json.loads(jornada_abierta.barras_disponibles) if isinstance(jornada_abierta.barras_disponibles, str) else jornada_abierta.barras_disponibles
                    except:
                        barras = []
                
                shift_status = ShiftStatus(
                    is_open=True,
                    shift_date=jornada_abierta.fecha_jornada,
                    opened_at=jornada_abierta.abierto_en.isoformat() if jornada_abierta.abierto_en else jornada_abierta.horario_apertura_programado,
                    opened_by=jornada_abierta.abierto_por or 'admin',
                    fiesta_nombre=jornada_abierta.nombre_fiesta or '',
                    djs=jornada_abierta.djs or '',
                    barras_disponibles=barras,
                    bartenders=[]
                )
                # Asignar cashiers si el campo existe
                if hasattr(shift_status, 'cashiers'):
                    shift_status.cashiers = []
                return shift_status
        except Exception as e:
            current_app.logger.debug(f"Error obteniendo Jornada, usando fallback: {e}")
        
        # Fallback al sistema legacy (JSON)
        try:
            return self.shift_repository.get_current_shift_status()
        except Exception as e:
            current_app.logger.error(f"Error obteniendo turno en repositorio legacy: {e}")
            # Retornar estado cerrado por defecto
            return ShiftStatus(is_open=False)
    
    def update_shift(self, request: OpenShiftRequest) -> Tuple[bool, str]:
        """
        Actualiza la información de un turno abierto.
        
        Args:
            request: DTO con información actualizada para el turno
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
            
        Raises:
            ShiftNotOpenError: Si no hay un turno abierto
            ValueError: Si los datos del request son inválidos
        """
        # Validar request
        request.validate()
        
        # Verificar que hay turno abierto
        current_status = self.shift_repository.get_current_shift_status()
        if not current_status.is_open:
            raise ShiftNotOpenError("No hay un turno abierto para modificar.")
        
        # Actualizar información del turno (mantener fecha y hora de apertura)
        current_status.fiesta_nombre = request.fiesta_nombre
        current_status.djs = request.djs or ''
        current_status.barras_disponibles = request.barras_disponibles or [
            'Barra Principal',
            'Barra Terraza',
            'Barra VIP',
            'Barra Exterior'
        ]
        current_status.bartenders = request.bartenders or []
        
        # Guardar estado actualizado
        if not self.shift_repository.save_shift_status(current_status):
            return False, "Error al guardar los cambios del turno"
        
        current_app.logger.info(
            f"Turno actualizado el {current_status.shift_date} - "
            f"Fiesta: {request.fiesta_nombre}"
        )
        
        return True, f"Información del turno actualizada correctamente"









