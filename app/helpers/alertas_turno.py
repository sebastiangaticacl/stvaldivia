"""
Helper para detección y gestión de alertas de pérdida crítica en turnos
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import current_app
from app.models import db
from app.models.bartender_turno_models import (
    BartenderTurno, TurnoDesviacionInventario, AlertaFugaTurno
)
from decimal import Decimal


class AlertasTurnoHelper:
    """
    Helper para detectar y gestionar alertas de pérdida crítica.
    """
    
    # Umbrales configurables
    UMBRAL_PERDIDA_CRITICA_PORC = Decimal('5.0')  # 5%
    UMBRAL_PERDIDA_CRITICA_MONTO = Decimal('10000.0')  # $10,000 CLP
    
    def detectar_alertas_turno(
        self,
        turno_id: int
    ) -> Tuple[bool, str, List[AlertaFugaTurno]]:
        """
        Detecta y registra alertas de pérdida crítica para un turno.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Tuple[bool, str, List[AlertaFugaTurno]]
        """
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return False, "Turno no encontrado", []
            
            if turno.estado != 'cerrado':
                return False, "El turno debe estar cerrado para detectar alertas", []
            
            # Obtener todas las desviaciones del turno
            desviaciones = TurnoDesviacionInventario.query.filter_by(turno_id=turno_id).all()
            
            alertas = []
            hay_fuga_critica = False
            
            for desviacion in desviaciones:
                # Solo alertar sobre pérdidas (diferencias negativas)
                if desviacion.diferencia_turno >= 0:
                    continue
                
                diferencia_abs = abs(Decimal(str(desviacion.diferencia_turno)))
                diferencia_porc_abs = abs(Decimal(str(desviacion.diferencia_porcentual_turno)))
                costo_abs = abs(Decimal(str(desviacion.costo_diferencia)))
                
                # Verificar si cumple umbrales de alerta
                es_critica = (
                    diferencia_porc_abs > self.UMBRAL_PERDIDA_CRITICA_PORC or
                    costo_abs > self.UMBRAL_PERDIDA_CRITICA_MONTO
                )
                
                if es_critica:
                    hay_fuga_critica = True
                    
                    # Determinar criticidad
                    if diferencia_porc_abs > Decimal('10.0') or costo_abs > Decimal('20000.0'):
                        criticidad = "alta"
                    elif diferencia_porc_abs > Decimal('7.0') or costo_abs > Decimal('15000.0'):
                        criticidad = "media"
                    else:
                        criticidad = "baja"
                    
                    # Crear o actualizar alerta
                    alerta = AlertaFugaTurno.query.filter_by(
                        turno_id=turno_id,
                        insumo_id=desviacion.insumo_id
                    ).first()
                    
                    if alerta:
                        alerta.diferencia_turno = desviacion.diferencia_turno
                        alerta.diferencia_porcentual_turno = desviacion.diferencia_porcentual_turno
                        alerta.costo_diferencia = desviacion.costo_diferencia
                        alerta.criticidad = criticidad
                    else:
                        alerta = AlertaFugaTurno(
                            turno_id=turno_id,
                            insumo_id=desviacion.insumo_id,
                            ubicacion=desviacion.ubicacion,
                            diferencia_turno=desviacion.diferencia_turno,
                            diferencia_porcentual_turno=desviacion.diferencia_porcentual_turno,
                            costo_diferencia=desviacion.costo_diferencia,
                            criticidad=criticidad,
                            atendida=False
                        )
                        db.session.add(alerta)
                    
                    alertas.append(alerta)
            
            # Actualizar flag de fuga crítica en el turno
            turno.flag_fuga_critica = hay_fuga_critica
            
            db.session.commit()
            
            mensaje = f"Alertas detectadas: {len(alertas)} insumos con pérdida crítica"
            return True, mensaje, alertas
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al detectar alertas: {e}", exc_info=True)
            return False, f"Error al detectar alertas: {str(e)}", []
    
    def marcar_alerta_atendida(
        self,
        alerta_id: int,
        observaciones: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Marca una alerta como atendida.
        
        Args:
            alerta_id: ID de la alerta
            observaciones: Observaciones sobre la atención
            
        Returns:
            Tuple[bool, str]
        """
        try:
            alerta = AlertaFugaTurno.query.get(alerta_id)
            if not alerta:
                return False, "Alerta no encontrada"
            
            alerta.atendida = True
            alerta.fecha_atencion = datetime.utcnow()
            alerta.observaciones_atencion = observaciones
            
            db.session.commit()
            
            return True, "Alerta marcada como atendida"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al marcar alerta: {e}", exc_info=True)
            return False, f"Error al marcar alerta: {str(e)}"
    
    def get_alertas_pendientes(
        self,
        ubicacion: Optional[str] = None,
        criticidad: Optional[str] = None
    ) -> List[AlertaFugaTurno]:
        """
        Obtiene alertas pendientes de atención.
        
        Args:
            ubicacion: Filtrar por ubicación (opcional)
            criticidad: Filtrar por criticidad (opcional)
            
        Returns:
            Lista de alertas pendientes
        """
        try:
            query = AlertaFugaTurno.query.filter_by(atendida=False)
            
            if ubicacion:
                query = query.filter_by(ubicacion=ubicacion)
            
            if criticidad:
                query = query.filter_by(criticidad=criticidad)
            
            return query.order_by(AlertaFugaTurno.fecha_hora.desc()).all()
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener alertas pendientes: {e}", exc_info=True)
            return []
    
    def get_alertas_turno(self, turno_id: int) -> List[AlertaFugaTurno]:
        """Obtiene todas las alertas de un turno"""
        try:
            return AlertaFugaTurno.query.filter_by(turno_id=turno_id).order_by(
                AlertaFugaTurno.criticidad.desc(),
                AlertaFugaTurno.fecha_hora.desc()
            ).all()
        except Exception as e:
            current_app.logger.error(f"Error al obtener alertas del turno: {e}", exc_info=True)
            return []
    
    def get_resumen_alertas(
        self,
        ubicacion: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtiene un resumen de alertas con filtros opcionales.
        
        Returns:
            Dict con estadísticas de alertas
        """
        try:
            query = AlertaFugaTurno.query
            
            if ubicacion:
                query = query.filter_by(ubicacion=ubicacion)
            
            if fecha_desde:
                query = query.filter(AlertaFugaTurno.fecha_hora >= fecha_desde)
            
            if fecha_hasta:
                query = query.filter(AlertaFugaTurno.fecha_hora <= fecha_hasta)
            
            alertas = query.all()
            
            return {
                'total_alertas': len(alertas),
                'alertas_pendientes': sum(1 for a in alertas if not a.atendida),
                'alertas_atendidas': sum(1 for a in alertas if a.atendida),
                'alertas_alta': sum(1 for a in alertas if a.criticidad == 'alta'),
                'alertas_media': sum(1 for a in alertas if a.criticidad == 'media'),
                'alertas_baja': sum(1 for a in alertas if a.criticidad == 'baja'),
                'total_costo_perdidas': sum(abs(float(a.costo_diferencia)) for a in alertas),
                'promedio_diferencia_porcentual': sum(abs(float(a.diferencia_porcentual_turno)) for a in alertas) / len(alertas) if alertas else 0.0
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de alertas: {e}", exc_info=True)
            return {}
    
    def actualizar_umbrales(
        self,
        umbral_porcentual: Optional[Decimal] = None,
        umbral_monto: Optional[Decimal] = None
    ):
        """
        Actualiza los umbrales de alerta (para configuración dinámica).
        
        Args:
            umbral_porcentual: Nuevo umbral porcentual (opcional)
            umbral_monto: Nuevo umbral de monto (opcional)
        """
        if umbral_porcentual is not None:
            self.UMBRAL_PERDIDA_CRITICA_PORC = umbral_porcentual
        
        if umbral_monto is not None:
            self.UMBRAL_PERDIDA_CRITICA_MONTO = umbral_monto
        
        current_app.logger.info(
            f"Umbrales actualizados: {self.UMBRAL_PERDIDA_CRITICA_PORC}% / ${self.UMBRAL_PERDIDA_CRITICA_MONTO}"
        )


def get_alertas_turno_helper() -> AlertasTurnoHelper:
    """Factory function para obtener instancia del helper"""
    return AlertasTurnoHelper()





