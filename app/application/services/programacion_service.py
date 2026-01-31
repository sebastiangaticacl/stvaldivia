"""
Servicio de Aplicación: Programación de Eventos
Gestiona eventos públicos e internos
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from flask import current_app

from app.models import db
from app.helpers.timezone_utils import CHILE_TZ
from app.models.programacion_models import ProgramacionEvento


class ProgramacionService:
    """
    Servicio para gestión de programación de eventos.
    Maneja información pública e interna de eventos.
    """
    
    def __init__(self):
        """Inicializa el servicio de programación"""
        pass
    
    def get_evento_para_fecha(self, fecha: date) -> Optional[ProgramacionEvento]:
        """
        Obtiene el evento para una fecha específica.
        
        Args:
            fecha: Fecha del evento
            
        Returns:
            ProgramacionEvento o None si no existe
        """
        try:
            return ProgramacionEvento.query.filter_by(
                fecha=fecha,
                eliminado_en=None
            ).first()
        except Exception as e:
            current_app.logger.error(f"Error al obtener evento para fecha {fecha}: {e}", exc_info=True)
            return None
    
    def get_eventos_entre(self, f_inicio: date, f_fin: date) -> List[ProgramacionEvento]:
        """
        Obtiene eventos entre dos fechas (inclusive).
        
        Args:
            f_inicio: Fecha de inicio
            f_fin: Fecha de fin
            
        Returns:
            Lista de ProgramacionEvento ordenada por fecha
        """
        try:
            return ProgramacionEvento.query.filter(
                ProgramacionEvento.fecha >= f_inicio,
                ProgramacionEvento.fecha <= f_fin,
                ProgramacionEvento.eliminado_en.is_(None)
            ).order_by(ProgramacionEvento.fecha.asc()).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener eventos entre {f_inicio} y {f_fin}: {e}", exc_info=True)
            return []
    
    def get_evento_hoy(self) -> Optional[ProgramacionEvento]:
        """
        Obtiene el evento de hoy.
        
        Returns:
            ProgramacionEvento o None si no existe
        """
        try:
            fecha_hoy = datetime.now(CHILE_TZ).date()
            return self.get_evento_para_fecha(fecha_hoy)
        except Exception as e:
            current_app.logger.error(f"Error al obtener evento de hoy: {e}", exc_info=True)
            return None
    
    def get_public_info_for_today(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información pública del evento de hoy.
        Formato optimizado para IA.
        
        Returns:
            Dict con información pública o None si no hay evento
        """
        evento = self.get_evento_hoy()
        if not evento:
            return None
        
        # Solo devolver si está publicado
        if evento.estado_publico != 'publicado':
            return None
        
        return evento.to_public_dict()
    
    def get_public_info_for_fecha(self, fecha: date) -> Optional[Dict[str, Any]]:
        """
        Obtiene información pública del evento para una fecha específica.
        Formato optimizado para IA.
        
        Args:
            fecha: Fecha del evento
            
        Returns:
            Dict con información pública o None si no hay evento
        """
        evento = self.get_evento_para_fecha(fecha)
        if not evento:
            return None
        
        # Solo devolver si está publicado
        if evento.estado_publico != 'publicado':
            return None
        
        return evento.to_public_dict()
    
    def get_upcoming_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene eventos futuros (solo campos públicos).
        
        Args:
            limit: Número máximo de eventos a devolver
            
        Returns:
            Lista de dicts con información pública de eventos futuros
        """
        try:
            fecha_hoy = datetime.now(CHILE_TZ).date()
            
            eventos = ProgramacionEvento.query.filter(
                ProgramacionEvento.fecha >= fecha_hoy,
                ProgramacionEvento.estado_publico == 'publicado',
                ProgramacionEvento.eliminado_en.is_(None)
            ).order_by(ProgramacionEvento.fecha.asc()).limit(limit).all()
            
            return [evento.to_public_dict() for evento in eventos]
        except Exception as e:
            current_app.logger.error(f"Error al obtener eventos futuros: {e}", exc_info=True)
            return []
    
    def get_eventos_mes(self, año: int, mes: int) -> List[ProgramacionEvento]:
        """
        Obtiene todos los eventos de un mes específico.
        
        Args:
            año: Año
            mes: Mes (1-12)
            
        Returns:
            Lista de ProgramacionEvento ordenada por fecha
        """
        try:
            # Calcular primera y última fecha del mes
            fecha_inicio = date(año, mes, 1)
            
            # Calcular última fecha del mes
            if mes == 12:
                fecha_fin = date(año + 1, 1, 1) - timedelta(days=1)
            else:
                fecha_fin = date(año, mes + 1, 1) - timedelta(days=1)
            
            return self.get_eventos_entre(fecha_inicio, fecha_fin)
        except Exception as e:
            current_app.logger.error(f"Error al obtener eventos del mes {año}-{mes}: {e}", exc_info=True)
            return []
    
    def crear_evento(self, datos: Dict[str, Any], creado_por: str) -> Optional[ProgramacionEvento]:
        """
        Crea un nuevo evento.
        
        Args:
            datos: Dict con los datos del evento
            creado_por: Usuario que crea el evento
            
        Returns:
            ProgramacionEvento creado o None si hay error
        """
        try:
            evento = ProgramacionEvento()
            
            # Campos básicos
            if 'fecha' in datos:
                evento.fecha = datos['fecha'] if isinstance(datos['fecha'], date) else datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
            evento.nombre_evento = datos.get('nombre_evento', '')
            evento.tipo_noche = datos.get('tipo_noche')
            
            # Campos públicos
            evento.dj_principal = datos.get('dj_principal')
            evento.otros_djs = datos.get('otros_djs')
            evento.estilos_musica = datos.get('estilos_musica')
            
            if 'horario_apertura_publico' in datos and datos['horario_apertura_publico']:
                if isinstance(datos['horario_apertura_publico'], str):
                    hora, minuto = map(int, datos['horario_apertura_publico'].split(':'))
                    evento.horario_apertura_publico = datetime.strptime(datos['horario_apertura_publico'], '%H:%M').time()
                else:
                    evento.horario_apertura_publico = datos['horario_apertura_publico']
            
            if 'horario_cierre_publico' in datos and datos['horario_cierre_publico']:
                if isinstance(datos['horario_cierre_publico'], str):
                    evento.horario_cierre_publico = datetime.strptime(datos['horario_cierre_publico'], '%H:%M').time()
                else:
                    evento.horario_cierre_publico = datos['horario_cierre_publico']
            
            if 'precios' in datos:
                evento.set_tiers_precios(datos['precios'])
            
            evento.info_lista = datos.get('info_lista')
            evento.descripcion_corta = datos.get('descripcion_corta')
            evento.copy_ig_corto = datos.get('copy_ig_corto')
            evento.copy_whatsapp_corto = datos.get('copy_whatsapp_corto')
            evento.hashtags_sugeridos = datos.get('hashtags_sugeridos')
            evento.estado_publico = datos.get('estado_publico', 'borrador')
            
            # Campos internos
            evento.estado_produccion = datos.get('estado_produccion', 'idea')
            evento.dj_confirmado = datos.get('dj_confirmado', False)
            evento.cache_dj_principal = datos.get('cache_dj_principal')
            evento.cache_otros_djs = datos.get('cache_otros_djs')
            evento.costos_produccion_estimados = datos.get('costos_produccion_estimados')
            evento.presupuesto_marketing = datos.get('presupuesto_marketing')
            evento.ingresos_estimados = datos.get('ingresos_estimados')
            evento.aforo_objetivo = datos.get('aforo_objetivo')
            evento.notas_internas = datos.get('notas_internas')
            
            evento.creado_por = creado_por
            
            db.session.add(evento)
            db.session.commit()
            
            current_app.logger.info(f"✅ Evento creado: {evento.nombre_evento} ({evento.fecha})")
            return evento
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear evento: {e}", exc_info=True)
            return None
    
    def actualizar_evento(self, evento_id: int, datos: Dict[str, Any], actualizado_por: str) -> Optional[ProgramacionEvento]:
        """
        Actualiza un evento existente.
        
        Args:
            evento_id: ID del evento
            datos: Dict con los datos a actualizar
            actualizado_por: Usuario que actualiza el evento
            
        Returns:
            ProgramacionEvento actualizado o None si hay error
        """
        try:
            evento = ProgramacionEvento.query.get(evento_id)
            if not evento:
                return None
            
            # Actualizar campos básicos
            if 'fecha' in datos:
                evento.fecha = datos['fecha'] if isinstance(datos['fecha'], date) else datetime.strptime(datos['fecha'], '%Y-%m-%d').date()
            if 'nombre_evento' in datos:
                evento.nombre_evento = datos['nombre_evento']
            if 'tipo_noche' in datos:
                evento.tipo_noche = datos['tipo_noche']
            
            # Actualizar campos públicos
            if 'dj_principal' in datos:
                evento.dj_principal = datos['dj_principal']
            if 'otros_djs' in datos:
                evento.otros_djs = datos['otros_djs']
            if 'estilos_musica' in datos:
                evento.estilos_musica = datos['estilos_musica']
            
            if 'horario_apertura_publico' in datos:
                if datos['horario_apertura_publico']:
                    if isinstance(datos['horario_apertura_publico'], str):
                        evento.horario_apertura_publico = datetime.strptime(datos['horario_apertura_publico'], '%H:%M').time()
                    else:
                        evento.horario_apertura_publico = datos['horario_apertura_publico']
                else:
                    evento.horario_apertura_publico = None
            
            if 'horario_cierre_publico' in datos:
                if datos['horario_cierre_publico']:
                    if isinstance(datos['horario_cierre_publico'], str):
                        evento.horario_cierre_publico = datetime.strptime(datos['horario_cierre_publico'], '%H:%M').time()
                    else:
                        evento.horario_cierre_publico = datos['horario_cierre_publico']
                else:
                    evento.horario_cierre_publico = None
            
            if 'precios' in datos:
                evento.set_tiers_precios(datos['precios'])
            
            if 'info_lista' in datos:
                evento.info_lista = datos['info_lista']
            if 'descripcion_corta' in datos:
                evento.descripcion_corta = datos['descripcion_corta']
            if 'copy_ig_corto' in datos:
                evento.copy_ig_corto = datos['copy_ig_corto']
            if 'copy_whatsapp_corto' in datos:
                evento.copy_whatsapp_corto = datos['copy_whatsapp_corto']
            if 'hashtags_sugeridos' in datos:
                evento.hashtags_sugeridos = datos['hashtags_sugeridos']
            if 'estado_publico' in datos:
                evento.estado_publico = datos['estado_publico']
            
            # Actualizar campos internos
            if 'estado_produccion' in datos:
                evento.estado_produccion = datos['estado_produccion']
            if 'dj_confirmado' in datos:
                evento.dj_confirmado = datos['dj_confirmado']
            if 'cache_dj_principal' in datos:
                evento.cache_dj_principal = datos['cache_dj_principal']
            if 'cache_otros_djs' in datos:
                evento.cache_otros_djs = datos['cache_otros_djs']
            if 'costos_produccion_estimados' in datos:
                evento.costos_produccion_estimados = datos['costos_produccion_estimados']
            if 'presupuesto_marketing' in datos:
                evento.presupuesto_marketing = datos['presupuesto_marketing']
            if 'ingresos_estimados' in datos:
                evento.ingresos_estimados = datos['ingresos_estimados']
            if 'aforo_objetivo' in datos:
                evento.aforo_objetivo = datos['aforo_objetivo']
            if 'notas_internas' in datos:
                evento.notas_internas = datos['notas_internas']
            
            evento.actualizado_por = actualizado_por
            evento.actualizado_en = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Evento actualizado: {evento.nombre_evento} ({evento.fecha})")
            return evento
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar evento: {e}", exc_info=True)
            return None


