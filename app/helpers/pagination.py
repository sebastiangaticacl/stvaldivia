"""
Helper para paginación consistente en toda la aplicación
"""
from flask import request
from sqlalchemy.orm import Query
from typing import Tuple, Dict, Any, List


def paginate_query(
    query: Query,
    per_page: int = 20,
    max_per_page: int = 100,
    page_param: str = 'page',
    per_page_param: str = 'per_page'
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Pagina una query de SQLAlchemy de forma consistente
    
    Args:
        query: Query de SQLAlchemy a paginar
        per_page: Items por página por defecto
        max_per_page: Máximo de items por página
        page_param: Nombre del parámetro de página en request
        per_page_param: Nombre del parámetro de items por página
        
    Returns:
        tuple: (items_list, metadata_dict)
    """
    page = request.args.get(page_param, 1, type=int)
    per_page = min(request.args.get(per_page_param, per_page, type=int), max_per_page)
    
    # Calcular offset
    offset = (page - 1) * per_page
    
    # Obtener total de items
    total = query.count()
    
    # Calcular número de páginas
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    
    # Obtener items para la página actual
    items = query.offset(offset).limit(per_page).all()
    
    metadata = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < pages else None
    }
    
    return items, metadata





