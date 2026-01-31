"""
Repositorio de Encuestas (Surveys)
Interfaz e implementación CSV.
"""
from abc import ABC, abstractmethod
import os
import csv
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from flask import current_app

from app.domain.survey import SurveyResponse, SurveySession


class SurveyRepository(ABC):
    """Interfaz del repositorio de encuestas"""
    
    @abstractmethod
    def save_response(self, response: SurveyResponse) -> bool:
        """Guarda una respuesta de encuesta"""
        pass
    
    @abstractmethod
    def find_responses_by_session_date(self, fecha_sesion: str) -> List[SurveyResponse]:
        """Obtiene respuestas de una sesión específica"""
        pass
    
    @abstractmethod
    def find_all_responses(self) -> List[SurveyResponse]:
        """Obtiene todas las respuestas"""
        pass
    
    @abstractmethod
    def save_session(self, session: SurveySession) -> bool:
        """Guarda o actualiza una sesión de encuestas"""
        pass
    
    @abstractmethod
    def find_session_by_date(self, fecha_sesion: str) -> Optional[SurveySession]:
        """Obtiene una sesión por fecha"""
        pass
    
    @abstractmethod
    def find_all_sessions(self) -> List[SurveySession]:
        """Obtiene todas las sesiones"""
        pass


class CsvSurveyRepository(SurveyRepository):
    """
    Implementación del repositorio usando archivos CSV.
    Mantiene compatibilidad con survey.py existente.
    """
    
    RESPONSES_FILE = 'survey_responses.csv'
    SESSIONS_FILE = 'survey_sessions.csv'
    
    RESPONSES_HEADER = ['timestamp', 'barra', 'rating', 'comment', 'fiesta_nombre', 'djs', 'bartender_nombre', 'fecha_sesion']
    SESSIONS_HEADER = ['fecha_sesion', 'fiesta_nombre', 'djs', 'bartenders', 'hora_inicio', 'hora_fin', 'total_respuestas', 'promedio_rating', 'estado']
    
    def _get_responses_file_path(self) -> str:
        """Obtiene la ruta del archivo de respuestas"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de respuestas de encuestas desde archivo")
        instance_path = get_safe_instance_path() or current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.RESPONSES_FILE)
    
    def _get_sessions_file_path(self) -> str:
        """Obtiene la ruta del archivo de sesiones"""
        from app.helpers.production_check import is_production, get_safe_instance_path, ensure_not_production
        ensure_not_production("El sistema de sesiones de encuestas desde archivo")
        instance_path = get_safe_instance_path() or current_app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        return os.path.join(instance_path, self.SESSIONS_FILE)
    
    def _ensure_responses_file(self) -> None:
        """Asegura que el archivo de respuestas existe con el header correcto"""
        responses_file = self._get_responses_file_path()
        
        if not os.path.exists(responses_file):
            with open(responses_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.RESPONSES_HEADER)
        else:
            # Verificar que el header sea correcto
            try:
                with open(responses_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header != self.RESPONSES_HEADER:
                        # Leer todas las filas existentes
                        rows = list(reader)
                        # Reescribir con nuevo header
                        with open(responses_file, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(self.RESPONSES_HEADER)
                            # Migrar datos antiguos (agregar columnas vacías si faltan)
                            for row in rows:
                                while len(row) < len(self.RESPONSES_HEADER):
                                    row.append('')
                                writer.writerow(row[:len(self.RESPONSES_HEADER)])
            except Exception as e:
                current_app.logger.error(f"Error actualizando header de respuestas: {e}")
                # Si hay error, crear nuevo archivo
                backup_file = responses_file + f'.backup_{int(datetime.now().timestamp())}'
                os.rename(responses_file, backup_file)
                with open(responses_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.RESPONSES_HEADER)
    
    def _ensure_sessions_file(self) -> None:
        """Asegura que el archivo de sesiones existe"""
        sessions_file = self._get_sessions_file_path()
        
        if not os.path.exists(sessions_file):
            with open(sessions_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.SESSIONS_HEADER)
    
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
    
    def save_response(self, response: SurveyResponse) -> bool:
        """Guarda una respuesta de encuesta"""
        self._ensure_responses_file()
        responses_file = self._get_responses_file_path()
        
        try:
            # Validar la respuesta antes de guardar
            response.validate()
            
            # Si no tiene fecha_sesion, calcularla
            if not response.fecha_sesion:
                response.fecha_sesion = self._get_current_session_date()
            
            # Si no tiene timestamp, agregarlo usando hora de Chile
            if not response.timestamp:
                from app.helpers.timezone_utils import CHILE_TZ
                response.timestamp = datetime.now(CHILE_TZ).strftime('%Y-%m-%d %H:%M:%S')
            
            # Guardar en CSV
            with open(responses_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(response.to_csv_row())
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar respuesta de encuesta: {e}")
            return False
    
    def find_responses_by_session_date(self, fecha_sesion: str) -> List[SurveyResponse]:
        """Obtiene respuestas de una sesión específica"""
        all_responses = self.find_all_responses()
        return [
            r for r in all_responses
            if r.fecha_sesion == fecha_sesion
        ]
    
    def find_all_responses(self) -> List[SurveyResponse]:
        """Obtiene todas las respuestas"""
        self._ensure_responses_file()
        responses_file = self._get_responses_file_path()
        
        responses = []
        try:
            with open(responses_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                if header != self.RESPONSES_HEADER:
                    return []
                
                for row in reader:
                    if len(row) < len(self.RESPONSES_HEADER):
                        # Completar fila si falta columnas
                        while len(row) < len(self.RESPONSES_HEADER):
                            row.append('')
                    
                    try:
                        response = SurveyResponse(
                            timestamp=row[0] or '',
                            barra=row[1] or '',
                            rating=int(row[2] or 0) if row[2] else 0,
                            comment=row[3] or '',
                            fiesta_nombre=row[4] or '',
                            djs=row[5] or '',
                            bartender_nombre=row[6] or '',
                            fecha_sesion=row[7] or ''
                        )
                        responses.append(response)
                    except Exception as e:
                        current_app.logger.warning(f"Error al parsear respuesta: {e}")
                        continue
        except FileNotFoundError:
            return []
        except Exception as e:
            current_app.logger.error(f"Error al cargar respuestas: {e}")
            return []
        
        return responses
    
    def save_session(self, session: SurveySession) -> bool:
        """Guarda o actualiza una sesión de encuestas"""
        self._ensure_sessions_file()
        sessions_file = self._get_sessions_file_path()
        
        try:
            # Leer todas las sesiones
            all_sessions = self.find_all_sessions()
            
            # Buscar si ya existe
            updated = False
            for i, s in enumerate(all_sessions):
                if s.fecha_sesion == session.fecha_sesion:
                    all_sessions[i] = session
                    updated = True
                    break
            
            # Si no existe, agregar
            if not updated:
                all_sessions.append(session)
            
            # Reescribir archivo
            with open(sessions_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.SESSIONS_HEADER)
                for s in all_sessions:
                    writer.writerow([
                        s.fecha_sesion,
                        s.fiesta_nombre,
                        s.djs,
                        s.bartenders,
                        s.hora_inicio,
                        s.hora_fin,
                        s.total_respuestas,
                        s.promedio_rating,
                        s.estado
                    ])
            
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar sesión: {e}")
            return False
    
    def find_session_by_date(self, fecha_sesion: str) -> Optional[SurveySession]:
        """Obtiene una sesión por fecha"""
        all_sessions = self.find_all_sessions()
        for session in all_sessions:
            if session.fecha_sesion == fecha_sesion:
                return session
        return None
    
    def find_all_sessions(self) -> List[SurveySession]:
        """Obtiene todas las sesiones"""
        self._ensure_sessions_file()
        sessions_file = self._get_sessions_file_path()
        
        sessions = []
        try:
            with open(sessions_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                if header != self.SESSIONS_HEADER:
                    return []
                
                for row in reader:
                    if len(row) < len(self.SESSIONS_HEADER):
                        # Completar fila si falta columnas
                        while len(row) < len(self.SESSIONS_HEADER):
                            row.append('')
                    
                    try:
                        session = SurveySession(
                            fecha_sesion=row[0] or '',
                            fiesta_nombre=row[1] or '',
                            hora_inicio=row[4] or '',
                            estado=row[8] if len(row) > 8 else 'abierta',
                            djs=row[2] or '',
                            bartenders=row[3] or '',
                            hora_fin=row[5] or '',
                            total_respuestas=int(row[6] or 0) if row[6] else 0,
                            promedio_rating=float(row[7] or 0) if row[7] else 0.0
                        )
                        sessions.append(session)
                    except Exception as e:
                        current_app.logger.warning(f"Error al parsear sesión: {e}")
                        continue
        except FileNotFoundError:
            return []
        except Exception as e:
            current_app.logger.error(f"Error al cargar sesiones: {e}")
            return []
        
        return sessions









