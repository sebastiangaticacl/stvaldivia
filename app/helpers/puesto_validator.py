"""
Helper para validar acceso de empleados a puestos de trabajo según su cargo y asignación al turno
"""
from flask import current_app
from app.models.jornada_models import Jornada, PlanillaTrabajador
from sqlalchemy import or_, func
from app.models.pos_models import Employee
from datetime import datetime
from app.helpers.timezone_utils import CHILE_TZ


def puede_abrir_puesto(employee_id, tipo_puesto):
    """
    Valida si un empleado puede abrir un puesto de trabajo específico.
    Todo se define en la apertura del turno, así que solo verificamos:
    - Que haya un turno abierto
    - Que el empleado esté en la planilla del turno
    - Que su área/rol en la planilla corresponda al tipo de puesto
    
    Args:
        employee_id: ID del empleado
        tipo_puesto: Tipo de puesto ("caja" o "barra")
    
    Returns:
        tuple: (puede_acceder: bool, mensaje: str, jornada_id: int o None)
    """
    try:
        # Normalizar tipo_puesto
        tipo_puesto_lower = tipo_puesto.lower()
        
        if tipo_puesto_lower not in ['caja', 'barra', 'guardarropia', 'guardarropía']:
            return False, f"Tipo de puesto inválido: {tipo_puesto}", None
        
        # Buscar jornada abierta actual
        jornada_actual = Jornada.query.filter_by(estado_apertura='abierto').order_by(
            Jornada.fecha_jornada.desc()
        ).first()
        
        if not jornada_actual:
            return False, "No hay un turno abierto actualmente", None
        
        # Verificar que el empleado esté en la planilla del turno
        planilla = PlanillaTrabajador.query.filter_by(
            jornada_id=jornada_actual.id,
            id_empleado=str(employee_id)
        ).first()
        
        if not planilla:
            return False, f"No estás asignado al turno actual ({jornada_actual.fecha_jornada})", None
        
        # Validar según tipo de puesto según lo definido en la apertura del turno
        rol_planilla = (planilla.rol or '').lower()
        area_planilla = (planilla.area or '').lower()
        
        # Para CAJA: verificar que el área/rol contenga "caja" o "cajero"
        if tipo_puesto_lower == 'caja':
            if 'caja' in area_planilla or 'cajero' in rol_planilla or 'caja' in rol_planilla:
                return True, f"Acceso permitido a Caja - Turno: {jornada_actual.fecha_jornada}", jornada_actual.id
            else:
                return False, f"No estás asignado a Caja en este turno. Tu asignación: {planilla.area or planilla.rol or 'N/A'}", None
        
        # Para BARRA: verificar que el área/rol contenga "barra" o "bartender"
        elif tipo_puesto_lower == 'barra':
            if 'barra' in area_planilla or 'bartender' in rol_planilla or 'barra' in rol_planilla or 'bar' in area_planilla:
                return True, f"Acceso permitido a Barra - Turno: {jornada_actual.fecha_jornada}", jornada_actual.id
            else:
                return False, f"No estás asignado a Barra en este turno. Tu asignación: {planilla.area or planilla.rol or 'N/A'}", None
        
        # Para GUARDARROPÍA: verificar que el área/rol contenga "guardarropía" o "guardarropia"
        elif tipo_puesto_lower in ['guardarropia', 'guardarropía']:
            if 'guardarrop' in area_planilla or 'guardarrop' in rol_planilla or 'guardarropia' in area_planilla or 'guardarropia' in rol_planilla:
                return True, f"Acceso permitido a Guardarropía - Turno: {jornada_actual.fecha_jornada}", jornada_actual.id
            else:
                return False, f"No estás asignado a Guardarropía en este turno. Tu asignación: {planilla.area or planilla.rol or 'N/A'}", None
        
        return False, "Error de validación", None
        
    except Exception as e:
        current_app.logger.error(f"Error al validar acceso a puesto: {e}", exc_info=True)
        return False, f"Error al validar acceso: {str(e)}", None


def obtener_empleados_habilitados_para_puesto(tipo_puesto, jornada_id=None):
    """
    Obtiene lista de empleados habilitados para un tipo de puesto específico
    según su asignación al turno.
    
    Args:
        tipo_puesto: Tipo de puesto ("caja" o "barra")
        jornada_id: ID de la jornada (opcional, si no se proporciona busca la abierta)
    
    Returns:
        list: Lista de diccionarios con información de empleados
    """
    try:
        current_app.logger.info(f"🔍 Buscando empleados habilitados para {tipo_puesto} (jornada_id: {jornada_id})")
        
        # Buscar jornada
        if jornada_id:
            jornada = Jornada.query.get(jornada_id)
        else:
            jornada = Jornada.query.filter_by(estado_apertura='abierto').order_by(
                Jornada.fecha_jornada.desc()
            ).first()
        
        if not jornada:
            current_app.logger.warning(f"⚠️  No se encontró jornada {'con ID ' + str(jornada_id) if jornada_id else 'abierta'}")
            return []
        
        # Normalizar tipo de puesto
        tipo_puesto_lower = tipo_puesto.lower()
        
        # Obtener trabajadores de la planilla según tipo de puesto
        if tipo_puesto_lower == 'caja':
            # Filtrar cajeros (búsqueda case-insensitive compatible MySQL)
            planilla_workers = PlanillaTrabajador.query.filter_by(
                jornada_id=jornada.id
            ).filter(
                or_(
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%cajero%')),
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%caja%')),
                    func.lower(PlanillaTrabajador.area).like(func.lower('%caja%'))
                )
            ).all()
        elif tipo_puesto_lower == 'barra':
            # Filtrar bartenders (búsqueda case-insensitive compatible MySQL)
            planilla_workers = PlanillaTrabajador.query.filter_by(
                jornada_id=jornada.id
            ).filter(
                or_(
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%bartender%')),
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%barra%')),
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%bar%')),
                    func.lower(PlanillaTrabajador.area).like(func.lower('%barra%')),
                    func.lower(PlanillaTrabajador.area).like(func.lower('%bar%'))
                )
            ).all()
        elif tipo_puesto_lower in ['guardarropia', 'guardarropía']:
            # Filtrar trabajadores de guardarropía (búsqueda case-insensitive compatible MySQL)
            planilla_workers = PlanillaTrabajador.query.filter_by(
                jornada_id=jornada.id
            ).filter(
                or_(
                    func.lower(PlanillaTrabajador.rol).like(func.lower('%guardarrop%')),
                    func.lower(PlanillaTrabajador.area).like(func.lower('%guardarrop%'))
                )
            ).all()
        else:
            return []
        
        # Convertir a formato esperado
        employees = []
        current_app.logger.info(f"📋 Encontrados {len(planilla_workers)} trabajadores en planilla para {tipo_puesto}")
        
        for trabajador in planilla_workers:
            # Obtener información del empleado (si existe)
            employee = Employee.query.filter_by(id=str(trabajador.id_empleado), is_active=True).first()
            
            # Si no está en Employee o está inactivo, usar datos de la planilla
            if not employee:
                current_app.logger.warning(f"⚠️  Empleado {trabajador.id_empleado} ({trabajador.nombre_empleado}) no encontrado en tabla Employee, usando datos de planilla")
                nombre_parts = trabajador.nombre_empleado.split() if trabajador.nombre_empleado else []
                employees.append({
                    'person_id': trabajador.id_empleado,
                    'employee_id': trabajador.id_empleado,
                    'id': trabajador.id_empleado,
                    'first_name': nombre_parts[0] if nombre_parts else '',
                    'last_name': ' '.join(nombre_parts[1:]) if len(nombre_parts) > 1 else '',
                    'name': trabajador.nombre_empleado or 'Empleado',
                    'job_title': trabajador.rol or tipo_puesto.title(),
                    'custom_fields': {
                        'Cargo': trabajador.rol or '',
                        'Area': trabajador.area or ''
                    }
                })
            else:
                # Usar datos de Employee si está disponible
                employees.append({
                    'person_id': trabajador.id_empleado,
                    'employee_id': trabajador.id_empleado,
                    'id': trabajador.id_empleado,
                    'first_name': employee.first_name or trabajador.nombre_empleado.split()[0] if trabajador.nombre_empleado else '',
                    'last_name': employee.last_name or ' '.join(trabajador.nombre_empleado.split()[1:]) if len(trabajador.nombre_empleado.split()) > 1 else '',
                    'name': employee.name or trabajador.nombre_empleado,
                    'job_title': trabajador.rol or employee.cargo or tipo_puesto.title(),
                    'custom_fields': {
                        'Cargo': trabajador.rol or employee.cargo or '',
                        'Area': trabajador.area or ''
                    }
                })
        
        current_app.logger.info(f"✅ Retornando {len(employees)} empleados habilitados para {tipo_puesto}")
        return employees
        
    except Exception as e:
        current_app.logger.error(f"Error al obtener empleados habilitados: {e}", exc_info=True)
        return []
