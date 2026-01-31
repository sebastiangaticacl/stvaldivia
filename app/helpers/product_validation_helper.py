"""
Helper centralizado para validación de productos y recetas.
Unifica la lógica de verificación de is_kit y recetas.
"""
from typing import Optional, Tuple, Dict, Any
from flask import current_app

def validate_product_has_recipe(product) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Valida si un producto tiene receta configurada correctamente.
    
    Args:
        product: Objeto Product
        
    Returns:
        Tuple[bool, Optional[str], Optional[Dict]]:
        (tiene_receta, mensaje_error, datos_receta)
        - tiene_receta: True si tiene receta válida
        - mensaje_error: Mensaje si no tiene receta o hay problema
        - datos_receta: Datos de la receta si existe
    """
    if not product:
        return False, "Producto no encontrado", None
    
    # Si no es kit, no necesita receta
    if not product.is_kit:
        return True, None, None  # No es kit, no necesita receta
    
    # Es kit, debe tener receta
    from app.helpers.recipe_helper import get_product_recipe
    recipe_data = get_product_recipe(product)
    
    if not recipe_data:
        return False, f"Producto '{product.name}' está marcado como kit pero no tiene receta configurada", None
    
    # Verificar que la receta tenga ingredientes
    ingredients = recipe_data.get('ingredients', [])
    if not ingredients:
        return False, f"Producto '{product.name}' tiene receta pero sin ingredientes configurados", None
    
    return True, None, recipe_data

def can_sell_product(product) -> Tuple[bool, Optional[str]]:
    """
    Verifica si un producto puede venderse (tiene receta si es kit).
    
    Args:
        product: Objeto Product
        
    Returns:
        Tuple[bool, Optional[str]]: (puede_venderse, mensaje_error)
    """
    tiene_receta, mensaje_error, _ = validate_product_has_recipe(product)
    
    if not tiene_receta and product and product.is_kit:
        return False, mensaje_error or "Producto requiere receta para venderse"
    
    return True, None

def get_product_recipe_safely(product) -> Optional[Dict[str, Any]]:
    """
    Obtiene la receta de un producto de forma segura, validando primero.
    
    Args:
        product: Objeto Product
        
    Returns:
        Dict con datos de receta o None si no tiene o no es válida
    """
    tiene_receta, _, recipe_data = validate_product_has_recipe(product)
    
    if tiene_receta:
        return recipe_data
    
    return None

def check_all_kit_products_have_recipes() -> Tuple[int, list]:
    """
    Verifica todos los productos is_kit=True y retorna los que no tienen receta.
    
    Returns:
        Tuple[int, list]: (total_kit_products, productos_sin_receta)
    """
    from app.models.product_models import Product
    
    kit_products = Product.query.filter_by(is_kit=True, is_active=True).all()
    productos_sin_receta = []
    
    for product in kit_products:
        tiene_receta, mensaje, _ = validate_product_has_recipe(product)
        if not tiene_receta:
            productos_sin_receta.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'error': mensaje
            })
    
    return len(kit_products), productos_sin_receta


