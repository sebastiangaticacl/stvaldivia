"""
Helpers para optimización de consultas de base de datos
"""
from functools import wraps
from flask import current_app
from app.models import db
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import func, case


def optimize_employee_shifts_query(query):
    """
    Optimiza una query de EmployeeShift con eager loading de relaciones
    """
    return query.options(
        # Pre-cargar relaciones comunes si existen
        # selectinload(EmployeeShift.employee)  # Si hay relación definida
    )


def get_employee_shifts_summary(employee_id=None, pagado=None, fecha_desde=None, fecha_hasta=None):
    """
    Obtiene resumen de turnos usando agregaciones SQL en lugar de Python
    Retorna: dict con totales calculados en BD
    """
    from app.models.employee_shift_models import EmployeeShift
    
    query = db.session.query(
        func.count(EmployeeShift.id).label('total_turnos'),
        func.sum(EmployeeShift.sueldo_turno).label('total_sueldo'),
        func.sum(EmployeeShift.bonos).label('total_bonos'),
        func.sum(EmployeeShift.descuentos).label('total_descuentos'),
        func.sum(
            case((EmployeeShift.pagado == True, EmployeeShift.sueldo_turno), else_=0)
        ).label('sueldo_pagado'),
        func.sum(
            case((EmployeeShift.pagado == False, EmployeeShift.sueldo_turno), else_=0)
        ).label('sueldo_pendiente')
    )
    
    if employee_id:
        query = query.filter(EmployeeShift.employee_id == str(employee_id))
    
    if pagado is not None:
        query = query.filter(EmployeeShift.pagado == pagado)
    
    if fecha_desde:
        query = query.filter(EmployeeShift.fecha_turno >= fecha_desde)
    
    if fecha_hasta:
        query = query.filter(EmployeeShift.fecha_turno <= fecha_hasta)
    
    result = query.first()
    
    return {
        'total_turnos': result.total_turnos or 0,
        'total_sueldo': float(result.total_sueldo or 0),
        'total_bonos': float(result.total_bonos or 0),
        'total_descuentos': float(result.total_descuentos or 0),
        'sueldo_pagado': float(result.sueldo_pagado or 0),
        'sueldo_pendiente': float(result.sueldo_pendiente or 0)
    }


def get_employee_payments_grouped(employee_ids=None):
    """
    Obtiene pagos agrupados por empleado usando SQL GROUP BY
    Mucho más eficiente que agrupar en Python
    """
    from app.models.employee_shift_models import EmployeeShift
    
    query = db.session.query(
        EmployeeShift.employee_id,
        EmployeeShift.employee_name,
        func.count(EmployeeShift.id).label('num_turnos'),
        func.sum(EmployeeShift.sueldo_turno).label('total_adeudado'),
        func.sum(EmployeeShift.bonos).label('total_bonos'),
        func.sum(EmployeeShift.descuentos).label('total_descuentos')
    ).filter(
        EmployeeShift.pagado == False
    )
    
    if employee_ids:
        query = query.filter(EmployeeShift.employee_id.in_(employee_ids))
    
    query = query.group_by(
        EmployeeShift.employee_id,
        EmployeeShift.employee_name
    ).order_by(
        func.sum(EmployeeShift.sueldo_turno).desc()
    )
    
    return query.all()


def get_employee_shifts_quincenal_grouped(fecha_desde, fecha_hasta):
    """
    Obtiene turnos agrupados por empleado para un rango de fechas
    Usa SQL GROUP BY en lugar de agrupar en Python
    """
    from app.models.employee_shift_models import EmployeeShift
    
    query = db.session.query(
        EmployeeShift.employee_id,
        EmployeeShift.employee_name,
        func.count(EmployeeShift.id).label('total_turnos'),
        func.sum(EmployeeShift.sueldo_turno).label('total_sueldo'),
        func.min(EmployeeShift.fecha_turno).label('primera_fecha'),
        func.max(EmployeeShift.fecha_turno).label('ultima_fecha')
    ).filter(
        EmployeeShift.fecha_turno >= fecha_desde,
        EmployeeShift.fecha_turno <= fecha_hasta,
        EmployeeShift.pagado == False
    ).group_by(
        EmployeeShift.employee_id,
        EmployeeShift.employee_name
    ).order_by(
        func.sum(EmployeeShift.sueldo_turno).desc()
    )
    
    return query.all()


def get_deliveries_summary_for_shift(shift_opened_at, shift_closed_at=None):
    """
    Obtiene resumen de entregas usando agregaciones SQL
    Optimizado para no cargar todas las entregas en memoria
    """
    from app.models.delivery_models import Delivery
    
    query = db.session.query(
        func.count(Delivery.id).label('total_deliveries'),
        func.sum(Delivery.qty).label('total_qty'),
        func.min(Delivery.timestamp).label('first_delivery'),
        func.max(Delivery.timestamp).label('last_delivery')
    ).filter(
        Delivery.timestamp >= shift_opened_at
    )
    
    if shift_closed_at:
        query = query.filter(Delivery.timestamp <= shift_closed_at)
    
    result = query.first()
    
    return {
        'total_deliveries': result.total_deliveries or 0,
        'total_qty': result.total_qty or 0,
        'first_delivery': result.first_delivery,
        'last_delivery': result.last_delivery
    }


def get_deliveries_by_hour_for_shift(shift_opened_at, shift_closed_at=None):
    """
    Obtiene entregas agrupadas por hora usando SQL
    Más eficiente que agrupar en Python
    """
    from app.models.delivery_models import Delivery
    from datetime import datetime
    
    # Extraer hora del timestamp usando func.strftime o similar
    # SQLite usa strftime
    query = db.session.query(
        func.strftime('%H', Delivery.timestamp).label('hour'),
        func.sum(Delivery.qty).label('total_qty'),
        func.count(Delivery.id).label('count')
    ).filter(
        Delivery.timestamp >= shift_opened_at
    )
    
    if shift_closed_at:
        query = query.filter(Delivery.timestamp <= shift_closed_at)
    
    query = query.group_by(
        func.strftime('%H', Delivery.timestamp)
    ).order_by(
        func.strftime('%H', Delivery.timestamp)
    )
    
    return query.all()


def cache_query_result(cache_key_prefix, ttl=300):
    """
    Decorator para cachear resultados de queries
    """
    def decorator(func):
        cache = {}
        cache_times = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Crear clave de cache única
            import hashlib
            import json
            cache_key = f"{cache_key_prefix}_{hashlib.md5(json.dumps((args, sorted(kwargs.items())), default=str).encode()).hexdigest()}"
            
            # Verificar cache
            import time
            if cache_key in cache:
                cache_time = cache_times.get(cache_key, 0)
                if time.time() - cache_time < ttl:
                    current_app.logger.debug(f"Cache hit: {cache_key}")
                    return cache[cache_key]
            
            # Ejecutar query y cachear
            result = func(*args, **kwargs)
            cache[cache_key] = result
            cache_times[cache_key] = time.time()
            
            return result
        
        return wrapper
    return decorator
