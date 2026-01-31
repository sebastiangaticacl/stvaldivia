"""
Helper para gestionar empleados en base de datos local
Sincroniza desde PHP POS API y almacena localmente para acceso rápido
"""
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from flask import current_app
from app.models import db, Employee
from app.helpers.pos_api import _get_employees_internal, get_entity_details, get_employee_pin
import json
import logging

logger = logging.getLogger(__name__)

# Tiempo de sincronización automática (24 horas)
SYNC_INTERVAL_HOURS = 24

def sync_employees_from_api(force: bool = False) -> int:
    """
    Sincroniza empleados desde PHP POS API a la base de datos local
    
    Args:
        force: Si es True, sincroniza aunque no haya pasado el tiempo de sincronización
        
    Returns:
        int: Número de empleados sincronizados
    """
    try:
        # Verificar si necesita sincronización
        if not force:
            # Verificar último empleado sincronizado
            last_synced = Employee.query.order_by(Employee.last_synced_at.desc()).first()
            if last_synced and last_synced.last_synced_at:
                # Asegurar que last_synced_at sea naive datetime (sin timezone)
                last_sync_dt = last_synced.last_synced_at
                if last_sync_dt.tzinfo:
                    last_sync_dt = last_sync_dt.replace(tzinfo=None)
                
                now = datetime.utcnow()
                time_since_sync = now - last_sync_dt
                
                if time_since_sync < timedelta(hours=SYNC_INTERVAL_HOURS):
                    logger.info(f"⏭️  Sincronización de empleados no necesaria (última sync hace {time_since_sync})")
                    return Employee.query.count()
        
        logger.info("🔄 Sincronizando empleados desde PHP POS API...")
        
        # Obtener todos los empleados desde la API
        api_employees = _get_employees_internal(only_bartenders=False, only_cashiers=False)
        
        if not api_employees:
            logger.warning("⚠️  No se obtuvieron empleados desde la API")
            return Employee.query.count()
        
        synced_count = 0
        now = datetime.utcnow()
        
        for emp in api_employees:
            try:
                # Obtener ID del empleado
                emp_id = str(emp.get('person_id') or emp.get('employee_id') or emp.get('id', ''))
                if not emp_id:
                    continue
                
                # Obtener nombre
                first_name = emp.get('first_name', '')
                last_name = emp.get('last_name', '')
                name = f"{first_name} {last_name}".strip() or emp.get('name', 'Empleado')
                
                # Obtener PIN desde custom_fields
                pin = get_employee_pin(emp)
                
                # Obtener custom_fields
                custom_fields = emp.get('custom_fields', {})
                if isinstance(custom_fields, dict):
                    cargo = custom_fields.get('Cargo', '')
                else:
                    cargo = ''
                
                # Determinar tipo de empleado
                is_bartender = cargo == 'Bartender'
                is_cashier = cargo == 'Cajero'
                
                # Verificar si existe
                existing = Employee.query.get(emp_id)
                
                if existing:
                    # Actualizar empleado existente
                    existing.first_name = first_name
                    existing.last_name = last_name
                    existing.name = name
                    existing.pin = pin
                    existing.custom_fields = json.dumps(custom_fields) if custom_fields else None
                    existing.cargo = cargo
                    existing.is_bartender = is_bartender
                    existing.is_cashier = is_cashier
                    existing.is_active = emp.get('deleted', '0') == '0'
                    existing.deleted = str(emp.get('deleted', '0'))
                    existing.last_synced_at = now
                    existing.updated_at = now
                else:
                    # Crear nuevo empleado
                    new_employee = Employee(
                        id=emp_id,
                        person_id=emp.get('person_id'),
                        employee_id=emp.get('employee_id'),
                        first_name=first_name,
                        last_name=last_name,
                        name=name,
                        pin=pin,
                        custom_fields=json.dumps(custom_fields) if custom_fields else None,
                        cargo=cargo,
                        is_bartender=is_bartender,
                        is_cashier=is_cashier,
                        is_active=emp.get('deleted', '0') == '0',
                        deleted=str(emp.get('deleted', '0')),
                        last_synced_at=now,
                        synced_from_phppos=True
                    )
                    db.session.add(new_employee)
                
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error al sincronizar empleado {emp.get('id', 'unknown')}: {e}")
                continue
        
        db.session.commit()
        logger.info(f"✅ {synced_count} empleados sincronizados desde PHP POS API")
        return synced_count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al sincronizar empleados: {e}", exc_info=True)
        return Employee.query.count()

def get_employees_local(only_bartenders: bool = False, only_cashiers: bool = False, sync_if_needed: bool = True) -> List[Dict[str, Any]]:
    """
    Obtiene empleados desde la base de datos local
    
    Args:
        only_bartenders: Si es True, filtra solo bartenders
        only_cashiers: Si es True, filtra solo cajeros
        sync_if_needed: Si es True, sincroniza desde API si es necesario
        
    Returns:
        Lista de empleados como diccionarios
    """
    try:
        # Sincronizar si es necesario
        if sync_if_needed:
            sync_employees_from_api(force=False)
        
        # Construir query
        query = Employee.query.filter(Employee.is_active == True, Employee.deleted == '0')
        
        if only_bartenders:
            query = query.filter(Employee.is_bartender == True)
        elif only_cashiers:
            query = query.filter(Employee.is_cashier == True)
        
        employees = query.all()
        
        return [emp.to_dict() for emp in employees]
        
    except Exception as e:
        logger.error(f"Error al obtener empleados locales: {e}", exc_info=True)
        return []

def get_employee_by_id(employee_id: str, sync_if_needed: bool = True) -> Optional[Dict[str, Any]]:
    """
    Obtiene un empleado por ID desde la base de datos local
    
    Args:
        employee_id: ID del empleado
        sync_if_needed: Si es True, sincroniza desde API si es necesario
        
    Returns:
        Diccionario con información del empleado o None
    """
    try:
        # Sincronizar si es necesario
        if sync_if_needed:
            sync_employees_from_api(force=False)
        
        employee = Employee.query.get(employee_id)
        
        if employee and employee.is_active and employee.deleted == '0':
            return employee.to_dict()
        
        return None
        
    except Exception as e:
        logger.error(f"Error al obtener empleado {employee_id}: {e}")
        return None

def verify_employee_pin_local(employee_id: str, pin: str) -> bool:
    """
    Verifica el PIN de un empleado desde la base de datos local
    
    Args:
        employee_id: ID del empleado
        pin: PIN a verificar
        
    Returns:
        bool: True si el PIN es correcto
    """
    try:
        employee = Employee.query.get(employee_id)
        
        if not employee or not employee.is_active or employee.deleted != '0':
            logger.warning(f"⚠️  Empleado {employee_id} no encontrado o inactivo")
            return False
        
        if not employee.pin:
            logger.warning(f"⚠️  Empleado {employee_id} no tiene PIN configurado")
            return False
        
        # Verificar PIN usando hash si está disponible, sino usar texto plano (migración)
        from werkzeug.security import check_password_hash, generate_password_hash
        
        pin_valid = False
        
        if employee.pin_hash:
            # Usar hash si está disponible (método seguro)
            pin_valid = check_password_hash(employee.pin_hash, pin)
        elif employee.pin:
            # Fallback a texto plano solo para migración (legacy)
            pin_valid = (str(employee.pin) == str(pin))
            
            if pin_valid:
                # Migrar a hash automáticamente
                logger.info(f"🔄 Migrando PIN a hash para empleado {employee_id}")
                employee.pin_hash = generate_password_hash(pin, method='pbkdf2:sha256')
                try:
                    db.session.commit()
                    logger.info(f"✅ PIN migrado a hash exitosamente")
                except Exception as e:
                    logger.error(f"❌ Error al migrar PIN a hash: {e}")
                    db.session.rollback()
        
        logger.info(f"{'✅' if pin_valid else '❌'} PIN {'válido' if pin_valid else 'inválido'} para empleado {employee_id}")
        return pin_valid
        
    except Exception as e:
        logger.error(f"Error al verificar PIN local: {e}")
        return False

