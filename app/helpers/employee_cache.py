"""
Cache en memoria para empleados para reducir queries repetitivas
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Cache en memoria
_employee_cache: Dict[str, Dict] = {}
_cache_timestamps: Dict[str, datetime] = {}
CACHE_TTL = 60  # TTL de 60 segundos


def get_cached_employees(only_bartenders: bool = False, only_cashiers: bool = False) -> Optional[List[Dict]]:
    """
    Obtiene empleados desde cache si está disponible y válido
    
    Args:
        only_bartenders: Si es True, cache para solo bartenders
        only_cashiers: Si es True, cache para solo cajeros
        
    Returns:
        Lista de empleados o None si el cache no está disponible
    """
    cache_key = f"employees_{only_bartenders}_{only_cashiers}"
    
    if cache_key not in _employee_cache:
        return None
    
    if cache_key not in _cache_timestamps:
        return None
    
    # Verificar si el cache expiró
    now = datetime.now()
    cache_time = _cache_timestamps[cache_key]
    
    if (now - cache_time).total_seconds() > CACHE_TTL:
        # Cache expirado
        logger.debug(f"Cache de empleados expirado para clave: {cache_key}")
        return None
    
    logger.debug(f"✅ Cache hit para empleados: {cache_key}")
    return _employee_cache[cache_key]


def set_cached_employees(employees: List[Dict], only_bartenders: bool = False, only_cashiers: bool = False):
    """
    Guarda empleados en cache
    
    Args:
        employees: Lista de empleados a cachear
        only_bartenders: Si es True, cache para solo bartenders
        only_cashiers: Si es True, cache para solo cajeros
    """
    cache_key = f"employees_{only_bartenders}_{only_cashiers}"
    _employee_cache[cache_key] = employees
    _cache_timestamps[cache_key] = datetime.now()
    logger.debug(f"💾 Cache actualizado para empleados: {cache_key} ({len(employees)} empleados)")


def get_cached_employee(employee_id: str) -> Optional[Dict]:
    """
    Obtiene un empleado específico desde cache
    
    Args:
        employee_id: ID del empleado
        
    Returns:
        Dict del empleado o None si no está en cache
    """
    # Buscar en todos los caches disponibles
    for cache_key, employees in _employee_cache.items():
        if cache_key not in _cache_timestamps:
            continue
        
        # Verificar si el cache expiró
        now = datetime.now()
        cache_time = _cache_timestamps[cache_key]
        
        if (now - cache_time).total_seconds() > CACHE_TTL:
            continue
        
        # Buscar empleado en este cache
        for emp in employees:
            if str(emp.get('id')) == str(employee_id) or \
               str(emp.get('person_id')) == str(employee_id) or \
               str(emp.get('employee_id')) == str(employee_id):
                logger.debug(f"✅ Cache hit para empleado: {employee_id}")
                return emp
    
    return None


def clear_employee_cache():
    """
    Limpia todo el cache de empleados
    """
    global _employee_cache, _cache_timestamps
    _employee_cache.clear()
    _cache_timestamps.clear()
    logger.info("🗑️  Cache de empleados limpiado")


def get_employees_with_cache(only_bartenders: bool = False, only_cashiers: bool = False, use_cache: bool = True) -> List[Dict]:
    """
    Obtiene empleados con cache automático
    
    Args:
        only_bartenders: Si es True, filtra solo bartenders
        only_cashiers: Si es True, filtra solo cajeros
        use_cache: Si es True, usa cache si está disponible
        
    Returns:
        Lista de empleados
    """
    # Intentar obtener desde cache primero
    if use_cache:
        cached = get_cached_employees(only_bartenders, only_cashiers)
        if cached is not None:
            return cached
    
    # Si no hay cache válido, obtener desde la fuente
    from app.helpers.employee_local import get_employees_local
    employees = get_employees_local(only_bartenders, only_cashiers)
    
    # Guardar en cache
    if use_cache:
        set_cached_employees(employees, only_bartenders, only_cashiers)
    
    return employees


def get_employee_with_cache(employee_id: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Obtiene un empleado específico con cache automático
    
    Args:
        employee_id: ID del empleado
        use_cache: Si es True, usa cache si está disponible
        
    Returns:
        Dict del empleado o None
    """
    # Intentar obtener desde cache primero
    if use_cache:
        cached = get_cached_employee(employee_id)
        if cached is not None:
            return cached
    
    # Si no hay cache válido, obtener desde la fuente
    from app.helpers.employee_local import get_employee_local
    employee = get_employee_local(employee_id)
    
    return employee

