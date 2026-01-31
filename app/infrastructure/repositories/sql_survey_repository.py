"""
Repositorio de Encuestas SQL
Implementación de SurveyRepository usando SQLAlchemy.
"""
from typing import List, Optional
from datetime import datetime, timedelta, date, time
from flask import current_app
import json

from app.models import db
from app.models.survey_models import SurveyResponse, SurveySession
from app.domain.survey import SurveyResponse as DomainSurveyResponse, SurveySession as DomainSurveySession
from app.infrastructure.repositories.survey_repository import SurveyRepository


class SqlSurveyRepository(SurveyRepository):
    """
    Implementación SQL del repositorio de encuestas.
    Usa los modelos SurveyResponse y SurveySession.
    """
    
    def __init__(self):
        """Inicializa el repositorio"""
        pass
    
    def _ensure_tables_exist(self):
        """Verifica que las tablas existen"""
        try:
            from flask import has_app_context
            if not has_app_context():
                return
            
            # Intentar consultas simples para verificar que las tablas existen
            try:
                SurveyResponse.query.limit(1).all()
                SurveySession.query.limit(1).all()
            except Exception as e:
                # Si las tablas no existen, intentar crearlas
                current_app.logger.warning(f"⚠️ Tablas de encuestas no encontradas, intentando crear: {e}")
                try:
                    db.create_all()
                    current_app.logger.info("✅ Tablas de encuestas creadas exitosamente")
                except Exception as create_error:
                    current_app.logger.error(f"❌ Error al crear tablas de encuestas: {create_error}")
                    raise RuntimeError(
                        f"No se pudo crear las tablas de encuestas. "
                        f"Verifica la conexión a la base de datos: {create_error}"
                    ) from create_error
        except RuntimeError:
            raise
        except Exception as e:
            try:
                current_app.logger.warning(f"⚠️ Advertencia al verificar tablas de encuestas: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ Advertencia al verificar tablas de encuestas: {e}")
    
    def _get_current_session_date(self) -> str:
        """Obtiene la fecha de sesión actual (si es después de 04:30, la sesión es del día anterior)"""
        from app.helpers.timezone_utils import CHILE_TZ
        now = datetime.now(CHILE_TZ)
        # Si es antes de las 04:30, la sesión es del día anterior
        if now.hour < 4 or (now.hour == 4 and now.minute < 30):
            session_date = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            session_date = now.strftime('%Y-%m-%d')
        return session_date
    
    def save_response(self, response: DomainSurveyResponse) -> bool:
        """Guarda una respuesta de encuesta"""
        try:
            self._ensure_tables_exist()
            
            # Validar la respuesta
            response.validate()
            
            # Si no tiene fecha_sesion, calcularla
            if not response.fecha_sesion:
                response.fecha_sesion = self._get_current_session_date()
            
            # Si no tiene timestamp, agregarlo
            if not response.timestamp:
                from app.helpers.timezone_utils import CHILE_TZ
                timestamp = datetime.now(CHILE_TZ)
            else:
                # Parsear timestamp string a datetime
                try:
                    timestamp = datetime.strptime(response.timestamp, '%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = datetime.now()
            
            # Parsear fecha_sesion
            try:
                fecha_sesion_date = datetime.strptime(response.fecha_sesion, '%Y-%m-%d').date()
            except:
                fecha_sesion_date = date.today()
            
            # Crear registro en base de datos
            db_response = SurveyResponse(
                timestamp=timestamp,
                barra=response.barra,
                rating=response.rating,
                comment=response.comment or '',
                fiesta_nombre=response.fiesta_nombre or '',
                djs=response.djs or '',
                bartender_nombre=response.bartender_nombre or '',
                fecha_sesion=fecha_sesion_date
            )
            
            db.session.add(db_response)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al guardar respuesta de encuesta SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
    
    def find_responses_by_session_date(self, fecha_sesion: str) -> List[DomainSurveyResponse]:
        """Obtiene respuestas de una sesión específica"""
        try:
            self._ensure_tables_exist()
            
            # Parsear fecha
            try:
                fecha_sesion_date = datetime.strptime(fecha_sesion, '%Y-%m-%d').date()
            except:
                return []
            
            # Buscar respuestas
            db_responses = SurveyResponse.query.filter_by(fecha_sesion=fecha_sesion_date).all()
            
            responses = []
            for db_resp in db_responses:
                domain_resp = DomainSurveyResponse(
                    timestamp=db_resp.timestamp.strftime('%Y-%m-%d %H:%M:%S') if db_resp.timestamp else '',
                    barra=db_resp.barra,
                    rating=db_resp.rating,
                    comment=db_resp.comment or '',
                    fiesta_nombre=db_resp.fiesta_nombre or '',
                    djs=db_resp.djs or '',
                    bartender_nombre=db_resp.bartender_nombre or '',
                    fecha_sesion=db_resp.fecha_sesion.isoformat() if db_resp.fecha_sesion else ''
                )
                responses.append(domain_resp)
            
            return responses
        except Exception as e:
            error_msg = f"Error al obtener respuestas de sesión SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return []
    
    def find_all_responses(self) -> List[DomainSurveyResponse]:
        """Obtiene todas las respuestas"""
        try:
            self._ensure_tables_exist()
            
            db_responses = SurveyResponse.query.order_by(SurveyResponse.timestamp.desc()).all()
            
            responses = []
            for db_resp in db_responses:
                domain_resp = DomainSurveyResponse(
                    timestamp=db_resp.timestamp.strftime('%Y-%m-%d %H:%M:%S') if db_resp.timestamp else '',
                    barra=db_resp.barra,
                    rating=db_resp.rating,
                    comment=db_resp.comment or '',
                    fiesta_nombre=db_resp.fiesta_nombre or '',
                    djs=db_resp.djs or '',
                    bartender_nombre=db_resp.bartender_nombre or '',
                    fecha_sesion=db_resp.fecha_sesion.isoformat() if db_resp.fecha_sesion else ''
                )
                responses.append(domain_resp)
            
            return responses
        except Exception as e:
            error_msg = f"Error al obtener todas las respuestas SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return []
    
    def save_session(self, session: DomainSurveySession) -> bool:
        """Guarda o actualiza una sesión de encuestas"""
        try:
            self._ensure_tables_exist()
            
            # Parsear fecha_sesion
            try:
                fecha_sesion_date = datetime.strptime(session.fecha_sesion, '%Y-%m-%d').date()
            except:
                fecha_sesion_date = date.today()
            
            # Parsear horas
            hora_inicio_time = None
            hora_fin_time = None
            if session.hora_inicio:
                try:
                    hora_inicio_time = datetime.strptime(session.hora_inicio, '%H:%M:%S').time()
                except:
                    try:
                        hora_inicio_time = datetime.strptime(session.hora_inicio, '%Y-%m-%d %H:%M:%S').time()
                    except:
                        pass
            if session.hora_fin:
                try:
                    hora_fin_time = datetime.strptime(session.hora_fin, '%H:%M:%S').time()
                except:
                    try:
                        hora_fin_time = datetime.strptime(session.hora_fin, '%Y-%m-%d %H:%M:%S').time()
                    except:
                        pass
            
            # Buscar sesión existente
            db_session = SurveySession.query.filter_by(fecha_sesion=fecha_sesion_date).first()
            
            if db_session:
                # Actualizar existente
                db_session.fiesta_nombre = session.fiesta_nombre or ''
                db_session.djs = session.djs or ''
                db_session.bartenders = session.bartenders or ''
                db_session.hora_inicio = hora_inicio_time
                db_session.hora_fin = hora_fin_time
                db_session.total_respuestas = session.total_respuestas
                db_session.promedio_rating = session.promedio_rating
                db_session.estado = session.estado
                db_session.updated_at = datetime.utcnow()
            else:
                # Crear nuevo
                db_session = SurveySession(
                    fecha_sesion=fecha_sesion_date,
                    fiesta_nombre=session.fiesta_nombre or '',
                    djs=session.djs or '',
                    bartenders=session.bartenders or '',
                    hora_inicio=hora_inicio_time,
                    hora_fin=hora_fin_time,
                    total_respuestas=session.total_respuestas,
                    promedio_rating=session.promedio_rating,
                    estado=session.estado
                )
                db.session.add(db_session)
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al guardar sesión de encuesta SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
    
    def find_session_by_date(self, fecha_sesion: str) -> Optional[DomainSurveySession]:
        """Obtiene una sesión por fecha"""
        try:
            self._ensure_tables_exist()
            
            # Parsear fecha
            try:
                fecha_sesion_date = datetime.strptime(fecha_sesion, '%Y-%m-%d').date()
            except:
                return None
            
            # Buscar sesión
            db_session = SurveySession.query.filter_by(fecha_sesion=fecha_sesion_date).first()
            
            if not db_session:
                return None
            
            # Convertir a dominio
            domain_session = DomainSurveySession(
                fecha_sesion=db_session.fecha_sesion.isoformat() if db_session.fecha_sesion else '',
                fiesta_nombre=db_session.fiesta_nombre or '',
                hora_inicio=db_session.hora_inicio.strftime('%H:%M:%S') if db_session.hora_inicio else '',
                estado=db_session.estado,
                djs=db_session.djs or '',
                bartenders=db_session.bartenders or '',
                hora_fin=db_session.hora_fin.strftime('%H:%M:%S') if db_session.hora_fin else '',
                total_respuestas=db_session.total_respuestas,
                promedio_rating=float(db_session.promedio_rating) if db_session.promedio_rating else 0.0
            )
            
            return domain_session
        except Exception as e:
            error_msg = f"Error al obtener sesión por fecha SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return None
    
    def find_all_sessions(self) -> List[DomainSurveySession]:
        """Obtiene todas las sesiones"""
        try:
            self._ensure_tables_exist()
            
            db_sessions = SurveySession.query.order_by(SurveySession.fecha_sesion.desc()).all()
            
            sessions = []
            for db_sess in db_sessions:
                domain_sess = DomainSurveySession(
                    fecha_sesion=db_sess.fecha_sesion.isoformat() if db_sess.fecha_sesion else '',
                    fiesta_nombre=db_sess.fiesta_nombre or '',
                    hora_inicio=db_sess.hora_inicio.strftime('%H:%M:%S') if db_sess.hora_inicio else '',
                    estado=db_sess.estado,
                    djs=db_sess.djs or '',
                    bartenders=db_sess.bartenders or '',
                    hora_fin=db_sess.hora_fin.strftime('%H:%M:%S') if db_sess.hora_fin else '',
                    total_respuestas=db_sess.total_respuestas,
                    promedio_rating=float(db_sess.promedio_rating) if db_sess.promedio_rating else 0.0
                )
                sessions.append(domain_sess)
            
            return sessions
        except Exception as e:
            error_msg = f"Error al obtener todas las sesiones SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return []

