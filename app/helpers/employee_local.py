"""
Funciones helper para obtener información de empleados desde la base de datos
(No consulta la API de PHP POS)
"""
from flask import current_app
from app.models.pos_models import Employee
from app.models import db
import logging

logger = logging.getLogger(__name__)


def get_employee_local(employee_id):
    """
    Obtiene información de un empleado desde la base de datos
    
    Args:
        employee_id: ID del empleado
        
    Returns:
        dict: Información del empleado o None si no se encuentra
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            return None
        
        if not employee.is_active or employee.deleted == '1':
            logger.debug(f"Empleado {employee_id} está inactivo o eliminado")
            return None
        
        return {
            'id': str(employee.id),
            'person_id': str(employee.id),
            'employee_id': str(employee.id),
            'name': employee.name or 'Empleado',
            'first_name': employee.first_name or '',
            'last_name': employee.last_name or '',
            'pin': employee.pin,
            'cargo': employee.cargo or '',
            'is_bartender': employee.is_bartender,
            'is_cashier': employee.is_cashier,
            'custom_fields': {
                'Cargo': employee.cargo or '',
                'Pin': employee.pin or ''
            }
        }
    except Exception as e:
        logger.error(f"Error al obtener empleado local {employee_id}: {e}")
        return None


def authenticate_employee_local(employee_id, pin):
    """
    Autentica un empleado usando la base de datos
    
    Args:
        employee_id: ID del empleado
        pin: PIN a verificar
        
    Returns:
        dict: Información del empleado autenticado o None
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee:
            logger.warning(f"⚠️ Empleado {employee_id} no encontrado en la base de datos")
            return None
        
        if not employee.is_active:
            logger.warning(f"⚠️ Empleado {employee_id} ({employee.name}) está inactivo")
            return None
        
        if employee.deleted == '1':
            logger.warning(f"⚠️ Empleado {employee_id} ({employee.name}) está eliminado")
            return None
        
        if not employee.pin:
            logger.warning(f"⚠️ Empleado {employee_id} ({employee.name}) no tiene PIN configurado")
            return None
        
        # Verificar PIN usando hash si está disponible, sino usar texto plano (migración)
        from werkzeug.security import check_password_hash, generate_password_hash
        
        pin_valid = False
        
        if employee.pin_hash:
            # Usar hash si está disponible (método seguro)
            pin_valid = check_password_hash(employee.pin_hash, pin)
            if pin_valid:
                logger.info(f"✅ PIN verificado con hash para empleado {employee_id} ({employee.name})")
        elif employee.pin:
            # Fallback a texto plano solo para migración (legacy)
            stored_pin = str(employee.pin).strip().upper()
            provided_pin = str(pin).strip().upper()
            pin_valid = (stored_pin == provided_pin)
            
            if pin_valid:
                # Migrar a hash automáticamente
                logger.info(f"🔄 Migrando PIN a hash para empleado {employee_id} ({employee.name})")
                employee.pin_hash = generate_password_hash(pin, method='pbkdf2:sha256')
                try:
                    db.session.commit()
                    logger.info(f"✅ PIN migrado a hash exitosamente")
                except Exception as e:
                    logger.error(f"❌ Error al migrar PIN a hash: {e}")
                    db.session.rollback()
        
        if not pin_valid:
            logger.warning(f"❌ PIN incorrecto para empleado {employee_id} ({employee.name})")
            return None
        
        logger.info(f"✅ PIN correcto para empleado {employee_id} ({employee.name})")
        return {
            'id': str(employee.id),
            'name': employee.name or 'Empleado',
            'first_name': employee.first_name or '',
            'last_name': employee.last_name or '',
            'pin': employee.pin
        }
    except Exception as e:
        logger.error(f"Error al autenticar empleado local {employee_id}: {e}", exc_info=True)
        return None


def get_employees_local(only_bartenders=False, only_cashiers=False):
    """
    Obtiene lista de empleados desde la base de datos
    
    Args:
        only_bartenders: Si es True, filtra solo bartenders
        only_cashiers: Si es True, filtra solo cajeros
        
    Returns:
        list: Lista de empleados
    """
    try:
        query = Employee.query.filter(
            Employee.is_active == True,
            Employee.deleted != '1'
        )
        
        if only_bartenders:
            query = query.filter(Employee.is_bartender == True)
        
        if only_cashiers:
            query = query.filter(Employee.is_cashier == True)
        
        employees = query.order_by(Employee.name).all()
        
        result = []
        for emp in employees:
            result.append({
                'id': str(emp.id),
                'person_id': str(emp.id),
                'employee_id': str(emp.id),
                'name': emp.name or 'Empleado',
                'first_name': emp.first_name or '',
                'last_name': emp.last_name or '',
                'pin': emp.pin,
                'cargo': emp.cargo or '',
                'is_bartender': emp.is_bartender,
                'is_cashier': emp.is_cashier,
                'custom_fields': {
                    'Cargo': emp.cargo or '',
                    'Pin': emp.pin or ''
                }
            })
        
        return result
    except Exception as e:
        logger.error(f"Error al obtener empleados locales: {e}")
        return []


def find_employee_by_name(name):
    """
    Busca un empleado por nombre (parcial o completo) en la base de datos
    
    Args:
        name: Nombre del empleado a buscar
        
    Returns:
        Employee: Objeto Employee o None si no se encuentra
    """
    try:
        name_lower = name.lower().strip()
        
        # Buscar por nombre completo
        employee = Employee.query.filter(
            Employee.is_active == True,
            Employee.deleted != '1',
            db.func.lower(Employee.name).contains(name_lower)
        ).first()
        
        if not employee:
            # Buscar por first_name + last_name
            employee = Employee.query.filter(
                Employee.is_active == True,
                Employee.deleted != '1',
                db.or_(
                    db.func.lower(Employee.first_name).contains(name_lower),
                    db.func.lower(Employee.last_name).contains(name_lower),
                    db.func.lower(
                        db.func.concat(Employee.first_name, ' ', Employee.last_name)
                    ).contains(name_lower)
                )
            ).first()
        
        return employee
    except Exception as e:
        logger.error(f"Error al buscar empleado por nombre '{name}': {e}")
        return None

