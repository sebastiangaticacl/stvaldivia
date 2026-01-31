"""
Helper para filtros y búsqueda en el dashboard
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def filter_sales_by_date_range(
    sales_data: Dict[str, Any],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Filtra ventas por rango de fechas
    
    Args:
        sales_data: Datos de ventas
        start_date: Fecha de inicio (ISO format)
        end_date: Fecha de fin (ISO format)
        
    Returns:
        Datos filtrados
    """
    try:
        if not start_date and not end_date:
            return sales_data
        
        registers = sales_data.get('registers', {})
        filtered_registers = {}
        
        for register_id, reg_data in registers.items():
            filtered_sales = []
            
            for sale in reg_data.get('sales', []):
                sale_time = sale.get('sale_time', '')
                if not sale_time:
                    continue
                
                try:
                    # Parsear fecha de venta
                    if isinstance(sale_time, str):
                        if 'T' in sale_time:
                            sale_dt = datetime.fromisoformat(sale_time.replace('Z', '+00:00'))
                        else:
                            sale_dt = datetime.strptime(sale_time[:19], '%Y-%m-%d %H:%M:%S')
                    else:
                        sale_dt = sale_time
                    
                    if sale_dt.tzinfo:
                        sale_dt = sale_dt.replace(tzinfo=None)
                    
                    # Aplicar filtros
                    if start_date:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        if start_dt.tzinfo:
                            start_dt = start_dt.replace(tzinfo=None)
                        if sale_dt < start_dt:
                            continue
                    
                    if end_date:
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        if end_dt.tzinfo:
                            end_dt = end_dt.replace(tzinfo=None)
                        if sale_dt > end_dt:
                            continue
                    
                    filtered_sales.append(sale)
                except:
                    # Si no se puede parsear, incluir la venta
                    filtered_sales.append(sale)
            
            if filtered_sales:
                filtered_reg_data = reg_data.copy()
                filtered_reg_data['sales'] = filtered_sales
                filtered_reg_data['total_sales'] = len(filtered_sales)
                # Recalcular totales
                filtered_reg_data['total_amount'] = sum(float(s.get('total', 0) or 0) for s in filtered_sales)
                filtered_registers[register_id] = filtered_reg_data
        
        # Recalcular resumen
        summary = {
            'total_registers': len(filtered_registers),
            'total_sales': sum(r.get('total_sales', 0) for r in filtered_registers.values()),
            'total_amount': sum(float(r.get('total_amount', 0) or 0) for r in filtered_registers.values()),
            'total_cash': sum(float(r.get('total_cash', 0) or 0) for r in filtered_registers.values()),
            'total_debit': sum(float(r.get('total_debit', 0) or 0) for r in filtered_registers.values()),
            'total_credit': sum(float(r.get('total_credit', 0) or 0) for r in filtered_registers.values())
        }
        
        return {
            'registers': filtered_registers,
            'summary': summary
        }
        
    except Exception as e:
        logger.error(f"Error al filtrar ventas por fecha: {e}", exc_info=True)
        return sales_data


def filter_sales_by_register(
    sales_data: Dict[str, Any],
    register_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Filtra ventas por caja
    
    Args:
        sales_data: Datos de ventas
        register_id: ID de la caja
        
    Returns:
        Datos filtrados
    """
    if not register_id:
        return sales_data
    
    registers = sales_data.get('registers', {})
    if register_id in registers:
        return {
            'registers': {register_id: registers[register_id]},
            'summary': sales_data.get('summary', {})
        }
    
    return {'registers': {}, 'summary': {}}


def search_sales_by_product(
    sales_data: Dict[str, Any],
    search_term: str
) -> Dict[str, Any]:
    """
    Busca ventas que contengan un producto específico
    
    Args:
        sales_data: Datos de ventas
        search_term: Término de búsqueda
        
    Returns:
        Datos filtrados
    """
    if not search_term:
        return sales_data
    
    search_term_lower = search_term.lower()
    registers = sales_data.get('registers', {})
    filtered_registers = {}
    
    for register_id, reg_data in registers.items():
        filtered_sales = []
        
        for sale in reg_data.get('sales', []):
            items = sale.get('items', sale.get('cart_items', []))
            
            # Buscar en items
            for item in items:
                item_name = str(item.get('name', item.get('item_name', ''))).lower()
                if search_term_lower in item_name:
                    filtered_sales.append(sale)
                    break
        
        if filtered_sales:
            filtered_reg_data = reg_data.copy()
            filtered_reg_data['sales'] = filtered_sales
            filtered_reg_data['total_sales'] = len(filtered_sales)
            filtered_reg_data['total_amount'] = sum(float(s.get('total', 0) or 0) for s in filtered_sales)
            filtered_registers[register_id] = filtered_reg_data
    
    summary = {
        'total_registers': len(filtered_registers),
        'total_sales': sum(r.get('total_sales', 0) for r in filtered_registers.values()),
        'total_amount': sum(float(r.get('total_amount', 0) or 0) for r in filtered_registers.values())
    }
    
    return {
        'registers': filtered_registers,
        'summary': summary
    }







