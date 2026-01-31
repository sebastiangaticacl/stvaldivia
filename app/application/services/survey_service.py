"""
Servicio de Aplicación: Gestión de Encuestas (Surveys)
Contiene la lógica de casos de uso para encuestas.
"""
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from flask import current_app

from app.domain.survey import SurveyResponse, SurveySession
from app.application.dto.survey_dto import SurveyResponseRequest
from app.infrastructure.repositories.survey_repository import SurveyRepository, CsvSurveyRepository
from app.infrastructure.repositories.shift_repository import ShiftRepository, JsonShiftRepository
from app.application.services.shift_service import ShiftService


class SurveyService:
    """
    Servicio de gestión de encuestas.
    Encapsula la lógica de negocio de encuestas.
    """
    
    def __init__(
        self,
        survey_repository: Optional[SurveyRepository] = None,
        shift_repository: Optional[ShiftRepository] = None,
        shift_service: Optional[ShiftService] = None,
        event_publisher: Optional = None
    ):
        """
        Inicializa el servicio de encuestas.
        
        Args:
            survey_repository: Repositorio de encuestas
            shift_repository: Repositorio de turnos (para obtener info del turno)
            shift_service: Servicio de turnos (para validar turno abierto)
            event_publisher: Publisher de eventos
        """
        self.survey_repository = survey_repository or CsvSurveyRepository()
        self.shift_repository = shift_repository or JsonShiftRepository()
        self.shift_service = shift_service or ShiftService(shift_repository=shift_repository)
        self.event_publisher = event_publisher
    
    def _get_current_session_date(self) -> str:
        """Obtiene la fecha de sesión actual (si es después de 04:30, la sesión es del día anterior)"""
        now = datetime.now()
        # Si es antes de las 04:30, la sesión es del día anterior
        if now.hour < 4 or (now.hour == 4 and now.minute < 30):
            session_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            session_date = now.strftime('%Y-%m-%d')
        return session_date
    
    def get_active_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de la sesión activa actual desde el turno unificado.
        
        Returns:
            dict: Información de la sesión activa o None
        """
        # Intentar obtener información del turno activo
        shift_status = self.shift_service.get_current_shift_status()
        
        if shift_status.is_open:
            # Usar información del turno unificado
            # Extraer hora de inicio en formato HH:MM:SS
            hora_inicio = ''
            if shift_status.opened_at:
                try:
                    from datetime import datetime
                    # Parsear desde ISO format
                    if 'T' in shift_status.opened_at:
                        parsed = datetime.fromisoformat(shift_status.opened_at.replace('Z', '+00:00'))
                        hora_inicio = parsed.strftime('%H:%M:%S')
                    else:
                        # Si ya está en formato legible, extraer solo la hora
                        hora_inicio = shift_status.opened_at[11:19] if len(shift_status.opened_at) > 19 else shift_status.opened_at
                except:
                    # Fallback: usar solo la parte de tiempo si es ISO
                    if 'T' in shift_status.opened_at:
                        hora_inicio = shift_status.opened_at.split('T')[1][:8]
                    else:
                        hora_inicio = shift_status.opened_at[:8] if len(shift_status.opened_at) >= 8 else ''
            
            return {
                'fecha_sesion': shift_status.shift_date or self._get_current_session_date(),
                'fiesta_nombre': shift_status.fiesta_nombre or '',
                'djs': shift_status.djs or '',
                'bartenders': ', '.join(shift_status.bartenders) if shift_status.bartenders else '',
                'estado': 'abierta',
                'hora_inicio': hora_inicio if hora_inicio else datetime.now().strftime('%H:%M:%S')
            }
        
        # Fallback: buscar en sesiones antiguas (compatibilidad)
        session_date = self._get_current_session_date()
        session = self.survey_repository.find_session_by_date(session_date)
        
        if session and session.estado == 'abierta':
            return {
                'fecha_sesion': session.fecha_sesion,
                'fiesta_nombre': session.fiesta_nombre,
                'djs': session.djs,
                'bartenders': session.bartenders,
                'estado': session.estado,
                'hora_inicio': session.hora_inicio
            }
        
        return None
    
    def save_survey_response(self, request: SurveyResponseRequest) -> Tuple[bool, str]:
        """
        Guarda una respuesta de encuesta.
        
        Args:
            request: DTO con información de la respuesta
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        # Validar request
        try:
            request.validate()
        except ValueError as e:
            return False, f"Datos de respuesta inválidos: {str(e)}"
        
        # Obtener información de la sesión activa
        session_info = self.get_active_session_info()
        session_date = self._get_current_session_date()
        
        # Crear entidad SurveyResponse
        response = SurveyResponse(
            barra=str(request.barra),
            rating=int(request.rating),
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            comment=request.comment or '',
            fiesta_nombre=request.fiesta_nombre or (session_info.get('fiesta_nombre') if session_info else ''),
            djs=request.djs or (session_info.get('djs') if session_info else ''),
            bartender_nombre=request.bartender_nombre or '',
            fecha_sesion=session_date
        )
        
        # Validar respuesta
        try:
            response.validate()
        except ValueError as e:
            return False, f"Respuesta inválida: {str(e)}"
        
        # Guardar respuesta
        if not self.survey_repository.save_response(response):
            return False, "Error al guardar la respuesta"
        
        # Crear/actualizar sesión si no existe
        session = self.survey_repository.find_session_by_date(session_date)
        if not session:
            # Crear nueva sesión
            session = SurveySession(
                fecha_sesion=session_date,
                fiesta_nombre=response.fiesta_nombre,
                hora_inicio=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                estado='abierta',
                djs=response.djs,
                bartenders=response.bartender_nombre
            )
        else:
            # Actualizar sesión existente
            if session.estado == 'cerrada':
                # Si está cerrada, no actualizar
                pass
        
        # Actualizar estadísticas de sesión
        all_responses = self.survey_repository.find_responses_by_session_date(session_date)
        session.total_respuestas = len(all_responses)
        
        if all_responses:
            total_rating = sum(r.rating for r in all_responses)
            session.promedio_rating = round(total_rating / len(all_responses), 2)
        else:
            session.promedio_rating = 0.0
        
        self.survey_repository.save_session(session)
        
        # Emitir eventos
        if self.event_publisher:
            response_dict = {
                'barra': response.barra,
                'rating': response.rating,
                'comment': response.comment,
                'fiesta_nombre': response.fiesta_nombre,
                'djs': response.djs,
                'bartender_nombre': response.bartender_nombre,
                'timestamp': response.timestamp
            }
            self.event_publisher.emit_survey_response_created(response_dict)
        
        current_app.logger.info(
            f"Respuesta de encuesta guardada: Barra {response.barra}, Rating {response.rating}"
        )
        
        return True, "Respuesta guardada correctamente"
    
    def get_responses_by_session(self, session_date: str, barra: Optional[str] = None) -> List[SurveyResponse]:
        """
        Obtiene respuestas de una sesión específica.
        
        Args:
            session_date: Fecha de sesión (YYYY-MM-DD)
            barra: Opcional, filtrar por barra ('1' o '2')
            
        Returns:
            List[SurveyResponse]: Lista de respuestas
        """
        responses = self.survey_repository.find_responses_by_session_date(session_date)
        
        if barra:
            responses = [r for r in responses if r.barra == str(barra)]
        
        return responses
    
    def get_all_responses(self) -> List[SurveyResponse]:
        """
        Obtiene todas las respuestas.
        
        Returns:
            List[SurveyResponse]: Lista de todas las respuestas
        """
        return self.survey_repository.find_all_responses()
    
    def close_session(self, session_date: str) -> Tuple[bool, str]:
        """
        Cierra una sesión de encuestas.
        
        Args:
            session_date: Fecha de sesión (YYYY-MM-DD)
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        session = self.survey_repository.find_session_by_date(session_date)
        
        if not session:
            return False, f"No se encontró la sesión del {session_date}"
        
        if session.estado == 'cerrada':
            return False, "La sesión ya está cerrada"
        
        # Cerrar sesión
        session.close()
        
        # Recalcular estadísticas finales
        responses = self.survey_repository.find_responses_by_session_date(session_date)
        session.total_respuestas = len(responses)
        
        if responses:
            total_rating = sum(r.rating for r in responses)
            session.promedio_rating = round(total_rating / len(responses), 2)
        else:
            session.promedio_rating = 0.0
        
        # Guardar sesión cerrada
        if not self.survey_repository.save_session(session):
            return False, "Error al guardar la sesión cerrada"
        
        current_app.logger.info(f"Sesión de encuestas cerrada: {session_date}")
        
        return True, f"Sesión del {session_date} cerrada correctamente"
    
    def get_session_summary(self, session_date: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resumen de una sesión.
        
        Args:
            session_date: Fecha de sesión (YYYY-MM-DD)
            
        Returns:
            dict: Resumen de la sesión o None
        """
        session = self.survey_repository.find_session_by_date(session_date)
        if not session:
            return None
        
        responses = self.survey_repository.find_responses_by_session_date(session_date)
        
        # Calcular estadísticas por barra
        barra_stats = {}
        for response in responses:
            barra = response.barra
            if barra not in barra_stats:
                barra_stats[barra] = {
                    'total': 0,
                    'sum_rating': 0,
                    'ratings': []
                }
            
            barra_stats[barra]['total'] += 1
            barra_stats[barra]['sum_rating'] += response.rating
            barra_stats[barra]['ratings'].append(response.rating)
        
        # Calcular promedios por barra
        for barra in barra_stats:
            stats = barra_stats[barra]
            stats['promedio'] = round(stats['sum_rating'] / stats['total'], 2) if stats['total'] > 0 else 0.0
        
        return {
            'fecha_sesion': session.fecha_sesion,
            'fiesta_nombre': session.fiesta_nombre,
            'djs': session.djs,
            'bartenders': session.bartenders,
            'hora_inicio': session.hora_inicio,
            'hora_fin': session.hora_fin,
            'estado': session.estado,
            'total_respuestas': len(responses),
            'promedio_rating': session.promedio_rating,
            'barra_stats': barra_stats
        }
    
    def get_survey_results(self, barra: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene resultados de encuestas para la sesión activa actual.
        
        Args:
            barra: Opcional, filtrar por barra ('1' o '2')
            
        Returns:
            Dict[str, Any]: Estadísticas de encuestas para la sesión activa
        """
        from collections import Counter, defaultdict
        
        # Verificar si hay turno abierto
        shift_status = self.shift_service.get_current_shift_status()
        if not shift_status.is_open:
            # Si no hay turno abierto, retornar datos vacíos
            return {
                'total': 0,
                'average_rating': 0.0,
                'ratings_count': {},
                'by_barra': {},
                'by_hour': {},
                'recent_responses': [],
                'session_info': None,
                'session_date': None
            }
        
        # Obtener información de la sesión activa
        session_info = self.get_active_session_info()
        if not session_info:
            return {
                'total': 0,
                'average_rating': 0.0,
                'ratings_count': {},
                'by_barra': {},
                'by_hour': {},
                'recent_responses': [],
                'session_info': None,
                'session_date': None
            }
        
        session_date = session_info.get('fecha_sesion') or self._get_current_session_date()
        hora_inicio_str = session_info.get('hora_inicio', '00:00:00')
        
        # Ensure hora_inicio_str is just the time part if it's an ISO datetime
        if 'T' in hora_inicio_str and len(hora_inicio_str) > 10:
            hora_inicio_str = hora_inicio_str[11:19]  # Extract HH:MM:SS
        elif len(hora_inicio_str) > 8:  # If it's a full datetime string without 'T'
            hora_inicio_str = hora_inicio_str[11:19]
        
        # Filter responses by session date
        all_responses = self.survey_repository.find_responses_by_session_date(session_date)
        
        # If barra filter is applied, filter here
        if barra:
            all_responses = [r for r in all_responses if r.barra == str(barra)]
        
        # Filter only responses created AFTER session start
        responses = []
        try:
            # Ensure hora_inicio_str is in HH:MM:SS format
            if len(hora_inicio_str) == 5:  # HH:MM
                hora_inicio_str = hora_inicio_str + ':00'  # Convert to HH:MM:SS
            elif len(hora_inicio_str) < 5:
                hora_inicio_str = '00:00:00'
            
            session_start_datetime = datetime.strptime(
                f"{session_date} {hora_inicio_str}",
                '%Y-%m-%d %H:%M:%S'
            )
            
            for r in all_responses:
                try:
                    response_datetime = datetime.strptime(r.timestamp, '%Y-%m-%d %H:%M:%S')
                    if response_datetime >= session_start_datetime:
                        responses.append(r)
                except ValueError:
                    current_app.logger.warning(f"Could not parse timestamp for survey response: {r.timestamp}")
                    pass
        except ValueError as e:
            current_app.logger.error(f"Error parsing session start time for survey results: {e} with date {session_date} and time {hora_inicio_str}")
            responses = []  # Fallback to no responses if session start time is invalid
        
        total = len(responses)
        ratings = [r.rating for r in responses]
        
        # Calcular estadísticas por hora
        hour_counts = Counter()
        for r in responses:
            try:
                response_hour = datetime.strptime(r.timestamp, '%Y-%m-%d %H:%M:%S').hour
                hour_counts[response_hour] += 1
            except (ValueError, AttributeError):
                pass  # Skip invalid timestamps
        
        stats = {
            'total': total,
            'average_rating': sum(ratings) / len(ratings) if ratings else 0.0,
            'ratings_count': dict(Counter(ratings)),
            'by_barra': dict(Counter([r.barra for r in responses])),
            'by_hour': dict(hour_counts),
            'recent_responses': [self._response_to_dict(r) for r in responses[-50:]] if responses else [],
            'session_info': session_info,
            'session_date': session_date
        }
        
        # Emit event for real-time updates (if publisher supports it)
        if self.event_publisher and hasattr(self.event_publisher, 'emit_survey_stats_update'):
            try:
                self.event_publisher.emit_survey_stats_update(stats)
            except Exception as e:
                current_app.logger.warning(f"Error emitiendo evento de estadísticas: {e}")
        
        return stats
    
    def _response_to_dict(self, response: SurveyResponse) -> Dict[str, Any]:
        """Convierte una SurveyResponse a diccionario para JSON"""
        return {
            'timestamp': response.timestamp,
            'barra': response.barra,
            'rating': response.rating,
            'comment': response.comment,
            'fiesta_nombre': response.fiesta_nombre,
            'djs': response.djs,
            'bartender_nombre': response.bartender_nombre,
            'fecha_sesion': response.fecha_sesion
        }

