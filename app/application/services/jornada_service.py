"""
Servicio de Aplicación: Jornada
Gestiona el flujo completo de apertura de jornada
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
import pytz

from app.models import db
from app.helpers.timezone_utils import CHILE_TZ
from app.models.jornada_models import Jornada, PlanillaTrabajador, AperturaCaja
from app.application.dto.jornada_dto import (
    CrearJornadaRequest, AgregarTrabajadorRequest, AsignarResponsablesRequest,
    AbrirCajaRequest, CompletarChecklistTecnicoRequest, AbrirLocalRequest
)


class JornadaService:
    """
    Servicio para gestión de jornadas.
    Maneja todo el flujo de apertura de jornada.
    """
    
    def __init__(self):
        """Inicializa el servicio de jornada"""
        pass
    
    def crear_jornada(self, request: CrearJornadaRequest, creado_por: str) -> Tuple[bool, str, Optional[Jornada]]:
        """
        Crea una nueva jornada.
        
        Args:
            request: DTO con información de la jornada
            creado_por: Usuario que crea la jornada
            
        Returns:
            Tuple[bool, str, Optional[Jornada]]: (éxito, mensaje, jornada)
        """
        try:
            # Normalizar fecha antes de validar
            from app.helpers.date_normalizer import normalize_shift_date
            fecha_normalizada = normalize_shift_date(request.fecha_jornada)
            if not fecha_normalizada:
                return False, f"Formato de fecha inválido: {request.fecha_jornada}. Use YYYY-MM-DD.", None
            request.fecha_jornada = fecha_normalizada
            
            request.validate()
            
            # Verificar que no haya una jornada abierta para esta fecha
            jornada_existente_abierta = Jornada.query.filter_by(
                fecha_jornada=request.fecha_jornada,
                estado_apertura='abierto'
            ).first()
            
            if jornada_existente_abierta:
                return False, f"Ya existe una jornada abierta para la fecha {request.fecha_jornada}", None
            
            # Si hay una jornada cerrada para esta fecha, eliminarla completamente para evitar conflictos
            jornada_existente_cerrada = Jornada.query.filter_by(
                fecha_jornada=request.fecha_jornada,
                estado_apertura='cerrado'
            ).first()
            
            if jornada_existente_cerrada:
                current_app.logger.info(f"🗑️ Eliminando jornada cerrada anterior para {request.fecha_jornada} (ID: {jornada_existente_cerrada.id})")
                # Eliminar jornada cerrada (cascade eliminará planilla y cajas)
                db.session.delete(jornada_existente_cerrada)
                db.session.commit()
            
            # También verificar jornadas en estado 'preparando' para la misma fecha y eliminarlas
            jornadas_preparando = Jornada.query.filter_by(
                fecha_jornada=request.fecha_jornada,
                estado_apertura='preparando'
            ).all()
            
            for jornada_prep in jornadas_preparando:
                current_app.logger.info(f"🗑️ Eliminando jornada en preparación anterior para {request.fecha_jornada} (ID: {jornada_prep.id})")
                db.session.delete(jornada_prep)
            
            if jornadas_preparando:
                db.session.commit()
            
            # Crear nueva jornada
            import json
            
            # horario_cierre_programado y fecha_cierre_programada son opcionales
            # Se registrarán automáticamente cuando se cierre el turno
            jornada = Jornada(
                fecha_jornada=request.fecha_jornada,
                fecha_cierre_programada=request.fecha_cierre_programada,  # Opcional
                tipo_turno=request.tipo_turno,
                nombre_fiesta=request.nombre_fiesta,
                horario_apertura_programado=request.horario_apertura_programado,
                horario_cierre_programado=request.horario_cierre_programado,  # Opcional - se registrará al cerrar
                djs=request.djs or '',
                estado_apertura='preparando',
                abierto_por=creado_por
            )
            
            # Guardar barras como JSON
            if request.barras_disponibles:
                jornada.barras_disponibles = json.dumps(request.barras_disponibles)
            else:
                jornada.barras_disponibles = json.dumps([
                    'Barra Principal',
                    'Barra Terraza',
                    'Barra VIP',
                    'Barra Exterior'
                ])
            
            db.session.add(jornada)
            db.session.flush()  # Para obtener el ID sin commit
            
            # ⭐ COPIAR PROGRAMACIÓN SI EXISTE
            try:
                from app.models.programacion_models import ProgramacionAsignacion
                from app.models.jornada_models import PlanillaTrabajador
                from app.models.pos_models import Employee
                from datetime import datetime
                
                # Mapear tipo_turno de jornada a tipo_turno de programación
                tipo_turno_programacion = 'NOCHE' if request.tipo_turno.upper() in ['NOCHE', 'NOCTURNO'] else 'DIA'
                
                # Convertir fecha_jornada (string) a date
                fecha_programacion = datetime.strptime(request.fecha_jornada, '%Y-%m-%d').date()
                
                # Buscar asignaciones de programación para esta fecha y tipo de turno
                asignaciones = ProgramacionAsignacion.query.filter_by(
                    fecha=fecha_programacion,
                    tipo_turno=tipo_turno_programacion
                ).all()
                
                if asignaciones:
                    current_app.logger.info(f"📋 Copiando {len(asignaciones)} asignaciones de programación a la planilla...")
                    copiados = 0
                    
                    for asignacion in asignaciones:
                        # Verificar que el trabajador existe
                        trabajador = Employee.query.get(asignacion.trabajador_id)
                        if not trabajador:
                            current_app.logger.warning(f"⚠️ Trabajador {asignacion.trabajador_id} de programación no encontrado, saltando...")
                            continue
                        
                        # Verificar que no esté duplicado
                        existente = PlanillaTrabajador.query.filter_by(
                            jornada_id=jornada.id,
                            id_empleado=asignacion.trabajador_id
                        ).first()
                        
                        if existente:
                            current_app.logger.warning(f"⚠️ Trabajador {trabajador.name} ya está en la planilla, saltando...")
                            continue
                        
                        # Obtener horarios de la jornada
                        hora_inicio = request.horario_apertura_programado or '22:00'
                        hora_fin = request.horario_cierre_programado or '05:00'
                        
                        # Calcular costo_hora
                        costo_hora = 0.0
                        try:
                            from app.models.cargo_salary_models import CargoSalaryConfig
                            if asignacion.cargo:
                                config_cargo = CargoSalaryConfig.query.filter_by(cargo=asignacion.cargo.nombre).first()
                                if config_cargo and config_cargo.sueldo_por_turno:
                                    from datetime import datetime as dt
                                    inicio = dt.strptime(hora_inicio, '%H:%M')
                                    fin = dt.strptime(hora_fin, '%H:%M')
                                    if fin < inicio:
                                        fin = fin.replace(day=fin.day + 1)
                                    diferencia = fin - inicio
                                    horas_turno = diferencia.total_seconds() / 3600.0
                                    costo_hora = float(config_cargo.sueldo_por_turno) / horas_turno if horas_turno > 0 else 0.0
                        except Exception as e:
                            current_app.logger.warning(f"Error calculando costo_hora: {e}")
                        
                        # Crear entrada en planilla desde programación
                        planilla_trabajador = PlanillaTrabajador(
                            jornada_id=jornada.id,
                            id_empleado=str(asignacion.trabajador_id).strip(),
                            nombre_empleado=trabajador.name or f'Empleado {asignacion.trabajador_id}',
                            rol=asignacion.cargo.nombre.upper() if asignacion.cargo else 'SIN CARGO',
                            hora_inicio=hora_inicio,
                            hora_fin=hora_fin,
                            costo_hora=float(costo_hora) if costo_hora else 0.0,
                            area=asignacion.cargo.nombre.upper() if asignacion.cargo else 'SIN CARGO',
                            cargo_id=asignacion.cargo_id,
                            origen='programacion'  # ⭐ Marcar como origen programación
                        )
                        
                        # Calcular costo total y pago
                        planilla_trabajador.calcular_costo_total()
                        planilla_trabajador.calcular_y_congelar_pago(
                            cargo_nombre=asignacion.cargo.nombre if asignacion.cargo else None
                        )
                        
                        db.session.add(planilla_trabajador)
                        copiados += 1
                    
                    if copiados > 0:
                        current_app.logger.info(f"✅ {copiados} trabajador(es) copiado(s) desde programación")
            except Exception as e:
                current_app.logger.warning(f"⚠️ Error al copiar programación (continuando): {e}", exc_info=True)
                # No fallar la creación de jornada si falla la copia de programación
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Jornada creada: {jornada.nombre_fiesta} ({jornada.fecha_jornada}) por {creado_por}")
            return True, f"Jornada creada correctamente", jornada
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e), None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear jornada: {e}", exc_info=True)
            return False, f"Error al crear jornada: {str(e)}", None
    
    def obtener_jornada_actual(self, fecha: Optional[str] = None) -> Optional[Jornada]:
        """
        Obtiene la jornada actual (en preparación o abierta).
        
        Args:
            fecha: Fecha de la jornada (opcional, usa fecha actual si no se proporciona)
            
        Returns:
            Jornada o None
        """
        try:
            if not fecha:
                fecha = datetime.now(CHILE_TZ).strftime('%Y-%m-%d')
            
            # Buscar jornada en preparación o abierta
            jornada = Jornada.query.filter_by(fecha_jornada=fecha).filter(
                Jornada.estado_apertura.in_(['preparando', 'revisando', 'listo', 'abierto'])
            ).first()
            
            return jornada
        except Exception as e:
            current_app.logger.error(f"Error al obtener jornada actual: {e}", exc_info=True)
            return None
    
    def agregar_trabajador_planilla(self, jornada_id: int, request: AgregarTrabajadorRequest) -> Tuple[bool, str]:
        """
        Agrega un trabajador a la planilla de la jornada.
        
        Args:
            jornada_id: ID de la jornada
            request: DTO con información del trabajador
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, "Jornada no encontrada"
            
            if jornada.estado_apertura == 'abierto':
                return False, "No se puede modificar la planilla de una jornada ya abierta"
            
            # Crear entrada en planilla
            planilla_trabajador = PlanillaTrabajador(
                jornada_id=jornada_id,
                id_empleado=request.id_empleado,
                nombre_empleado=request.nombre_empleado,
                rol=request.rol,
                hora_inicio=request.hora_inicio,
                hora_fin=request.hora_fin,
                costo_hora=request.costo_hora,
                area=request.area
            )
            
            # Calcular costo total (compatibilidad con código existente)
            planilla_trabajador.calcular_costo_total()
            
            # ⭐ CALCULAR Y CONGELAR PAGO AL MOMENTO DE ASIGNAR
            planilla_trabajador.calcular_y_congelar_pago(cargo_nombre=request.rol)
            
            db.session.add(planilla_trabajador)
            db.session.commit()
            
            current_app.logger.info(f"✅ Trabajador agregado a planilla: {request.nombre_empleado} en jornada {jornada_id}")
            return True, "Trabajador agregado correctamente"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al agregar trabajador a planilla: {e}", exc_info=True)
            return False, f"Error al agregar trabajador: {str(e)}"
    
    def eliminar_trabajador_planilla(self, planilla_id: int) -> Tuple[bool, str]:
        """
        Elimina un trabajador de la planilla.
        
        Args:
            planilla_id: ID de la entrada en la planilla
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            planilla = PlanillaTrabajador.query.get(planilla_id)
            if not planilla:
                return False, "Trabajador no encontrado en la planilla"
            
            jornada = planilla.jornada
            if jornada and jornada.estado_apertura == 'abierto':
                return False, "No se puede eliminar trabajador de una jornada ya abierta"
            
            db.session.delete(planilla)
            db.session.commit()
            
            return True, "Trabajador eliminado de la planilla"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al eliminar trabajador de planilla: {e}", exc_info=True)
            return False, f"Error al eliminar trabajador: {str(e)}"
    
    def asignar_responsables(self, jornada_id: int, request: AsignarResponsablesRequest) -> Tuple[bool, str]:
        """
        Asigna responsables por área a la jornada.
        
        Args:
            jornada_id: ID de la jornada
            request: DTO con responsables
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, "Jornada no encontrada"
            
            if jornada.estado_apertura == 'abierto':
                return False, "No se puede modificar los responsables de una jornada ya abierta"
            
            jornada.responsable_cajas = request.responsable_cajas
            jornada.responsable_puerta = request.responsable_puerta
            jornada.responsable_seguridad = request.responsable_seguridad
            jornada.responsable_admin = request.responsable_admin
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Responsables asignados a jornada {jornada_id}")
            return True, "Responsables asignados correctamente"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al asignar responsables: {e}", exc_info=True)
            return False, f"Error al asignar responsables: {str(e)}"
    
    def abrir_caja(self, jornada_id: int, request: AbrirCajaRequest) -> Tuple[bool, str]:
        """
        Abre una caja para la jornada.
        
        Args:
            jornada_id: ID de la jornada
            request: DTO con información de la apertura de caja
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, "Jornada no encontrada"
            
            # Verificar si la caja ya está abierta para esta jornada
            caja_existente = AperturaCaja.query.filter_by(
                jornada_id=jornada_id,
                id_caja=request.id_caja,
                estado='abierta'
            ).first()
            
            if caja_existente:
                return False, f"La caja {request.nombre_caja} ya está abierta para esta jornada"
            
            # Crear apertura de caja
            apertura_caja = AperturaCaja(
                jornada_id=jornada_id,
                id_caja=request.id_caja,
                nombre_caja=request.nombre_caja,
                id_empleado=request.id_empleado,
                nombre_empleado=request.nombre_empleado,
                fondo_inicial=request.fondo_inicial,
                abierto_por=request.abierto_por,
                estado='abierta'
            )
            
            db.session.add(apertura_caja)
            db.session.commit()
            
            current_app.logger.info(f"✅ Caja abierta: {request.nombre_caja} en jornada {jornada_id}")
            return True, f"Caja {request.nombre_caja} abierta correctamente"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al abrir caja: {e}", exc_info=True)
            return False, f"Error al abrir caja: {str(e)}"
    
    def completar_checklist_tecnico(self, jornada_id: int, request: CompletarChecklistTecnicoRequest) -> Tuple[bool, str]:
        """
        Completa el checklist técnico de la jornada.
        
        Args:
            jornada_id: ID de la jornada
            request: DTO con el checklist técnico
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, "Jornada no encontrada"
            
            jornada.set_checklist_tecnico(request.checklist)
            jornada.estado_apertura = 'revisando'
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Checklist técnico completado para jornada {jornada_id}")
            return True, "Checklist técnico completado correctamente"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al completar checklist técnico: {e}", exc_info=True)
            return False, f"Error al completar checklist: {str(e)}"
    
    def validar_listo_para_abrir(self, jornada_id: int) -> Dict[str, Any]:
        """
        Valida si la jornada está lista para abrir.
        
        Args:
            jornada_id: ID de la jornada
            
        Returns:
            dict: Estado de validación con detalles
        """
        try:
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return {
                    'valido': False,
                    'mensaje': 'Jornada no encontrada',
                    'detalles': {}
                }
            
            detalles = {
                'jornada_creada': True,
                'planilla_completa': False,
                'responsables_asignados': False,
                'cajas_abiertas': False,
                'checklist_tecnico_completo': False
            }
            
            # Validar planilla
            trabajadores = PlanillaTrabajador.query.filter_by(jornada_id=jornada_id).all()
            detalles['planilla_completa'] = len(trabajadores) > 0
            
            # Validar responsables (ya no son requeridos, pero verificamos si existen)
            # Los responsables fueron eliminados del sistema, así que siempre es True
            detalles['responsables_asignados'] = True  # Ya no se requieren responsables
            
            # Validar cajas (debe haber al menos una)
            cajas_abiertas = AperturaCaja.query.filter_by(
                jornada_id=jornada_id,
                estado='abierta'
            ).all()
            detalles['cajas_abiertas'] = len(cajas_abiertas) > 0
            detalles['cantidad_cajas'] = len(cajas_abiertas)
            
            # Validar checklist técnico
            checklist_tecnico = jornada.get_checklist_tecnico_dict()
            if checklist_tecnico:
                todos_completados = all(checklist_tecnico.values())
                detalles['checklist_tecnico_completo'] = todos_completados
            else:
                detalles['checklist_tecnico_completo'] = False
            
            # Determinar si está todo listo
            # Nota: responsables ya no son requeridos (fueron eliminados del sistema)
            # Nota: las cajas se abren automáticamente cuando los cajeros se loguean en los POS,
            #       por lo que no es un requisito previo para abrir el local
            # Nota: el checklist técnico tampoco es requerido - se puede completar después
            valido = detalles['planilla_completa']
            
            # Construir mensaje detallado si no está listo
            if not valido:
                pasos_faltantes = []
                if not detalles['planilla_completa']:
                    pasos_faltantes.append('Agregar trabajadores a la planilla')
                
                mensaje = f"Faltan completar pasos: {', '.join(pasos_faltantes)}"
            else:
                mensaje = 'Jornada lista para abrir'
            
            return {
                'valido': valido,
                'mensaje': mensaje,
                'detalles': detalles
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al validar jornada: {e}", exc_info=True)
            return {
                'valido': False,
                'mensaje': f'Error al validar: {str(e)}',
                'detalles': {}
            }
    
    def abrir_local(self, jornada_id: int, request: AbrirLocalRequest) -> Tuple[bool, str]:
        """
        Abre el local (finaliza el proceso de apertura).
        
        Args:
            jornada_id: ID de la jornada
            request: DTO con información
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            # Validar que esté listo
            validacion = self.validar_listo_para_abrir(jornada_id)
            if not validacion['valido']:
                return False, f"La jornada no está lista para abrir: {validacion['mensaje']}"
            
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return False, "Jornada no encontrada"
            
            if jornada.estado_apertura == 'abierto':
                return False, "La jornada ya está abierta"
            
            # Actualizar jornada usando hora de Chile (guardar directamente en hora local)
            now_chile = datetime.now(CHILE_TZ)
            # Guardar en hora local de Chile (sin timezone) para que se muestre correctamente
            now_local = now_chile.replace(tzinfo=None)
            jornada.estado_apertura = 'abierto'
            jornada.horario_apertura_real = now_local
            jornada.abierto_por = request.abierto_por
            jornada.abierto_en = now_local
            
            # Actualizar checklist de apertura
            checklist_apertura = {
                'jornada_abierta': True,
                'fecha_apertura': now_chile.isoformat(),
                'abierto_por': request.abierto_por
            }
            jornada.set_checklist_apertura(checklist_apertura)
            
                        # ========== REGISTRO DE TURNOS MOVIDO AL CIERRE ==========
            # Los EmployeeShift NO se crean al abrir el turno, sino al cerrarlo.
            # Esto permite manejar casos donde empleados:
            # - No terminan el turno
            # - No llegan
            # - Piden adelanto
            # - Piden pago extra programático
            # Los turnos se crearán en cerrar_jornada() con el estado correspondiente.
            current_app.logger.info(f"📋 Planilla encontrada: {len(PlanillaTrabajador.query.filter_by(jornada_id=jornada_id).all())} trabajadores para jornada {jornada_id} - Turnos se crearán al cerrar la jornada")
            db.session.commit()
            
            # Verificar que los EmployeeShift se guardaron correctamente
            from app.models.employee_shift_models import EmployeeShift
            shifts_guardados = EmployeeShift.query.filter_by(jornada_id=jornada_id).all()
            current_app.logger.info(f"✅ LOCAL ABIERTO - Jornada {jornada_id} ({jornada.nombre_fiesta}) por {request.abierto_por}")
            current_app.logger.info(f"💰 EmployeeShift guardados en BD: {len(shifts_guardados)} turnos para jornada {jornada_id}")
            for shift in shifts_guardados:
                current_app.logger.info(f"   - {shift.employee_name}: ${shift.sueldo_turno:.0f} (Pagado: {shift.pagado})")
            return True, "Local abierto correctamente. ¡La jornada ha comenzado!"
            
        except ValueError as e:
            db.session.rollback()
            return False, str(e)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al abrir local: {e}", exc_info=True)
            return False, f"Error al abrir local: {str(e)}"
    
    def obtener_resumen_jornada(self, jornada_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resumen completo de la jornada.
        
        Args:
            jornada_id: ID de la jornada
            
        Returns:
            dict con resumen o None
        """
        try:
            jornada = Jornada.query.get(jornada_id)
            if not jornada:
                return None
            
            trabajadores = PlanillaTrabajador.query.filter_by(jornada_id=jornada_id).all()
            cajas = AperturaCaja.query.filter_by(jornada_id=jornada_id).all()
            
            costo_total_planilla = sum(float(t.costo_total) for t in trabajadores)
            
            return {
                'jornada': jornada.to_dict(),
                'total_trabajadores': len(trabajadores),
                'costo_total_planilla': costo_total_planilla,
                'total_cajas': len(cajas),
                'cajas_abiertas': len([c for c in cajas if c.estado == 'abierta']),
                'trabajadores': [t.to_dict() for t in trabajadores],
                'cajas': [c.to_dict() for c in cajas]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de jornada: {e}", exc_info=True)
            return None

