"""
Helper para unificar acceso a recetas
Elimina la duplicación entre sistema legacy y nuevo
"""
from typing import Optional, List, Dict, Any
from flask import current_app

def get_product_recipe(product) -> Optional[Dict[str, Any]]:
    """
    Obtiene la receta de un producto, buscando en ambos sistemas (legacy y nuevo).
    Prioriza el sistema nuevo.
    
    Args:
        product: Objeto Product
        
    Returns:
        Dict con la receta o None si no tiene receta
    """
    if not product:
        return None
    
    # PRIORIDAD 1: Sistema nuevo (Recipe y RecipeIngredient)
    try:
        from app.models.inventory_stock_models import Recipe, RecipeIngredient
        
        recipe = Recipe.query.filter_by(
            product_id=product.id,
            is_active=True
        ).first()
        
        if recipe:
            ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
            return {
                'system': 'new',
                'recipe_id': recipe.id,
                'product_id': product.id,
                'ingredients': [
                    {
                        'ingredient_id': ri.ingredient_id,
                        'ingredient_name': ri.ingredient.name if ri.ingredient else '?',
                        'quantity_per_portion': float(ri.quantity_per_portion),
                        'unit': ri.ingredient.base_unit if ri.ingredient else 'ml'
                    }
                    for ri in ingredients
                ]
            }
    except Exception as e:
        current_app.logger.warning(f"Error al buscar receta en sistema nuevo: {e}")
    
    # PRIORIDAD 2: Sistema legacy (ProductRecipe)
    try:
        from app.models.recipe_models import ProductRecipe
        
        recipe_items = ProductRecipe.query.filter_by(product_id=product.id).all()
        
        if recipe_items:
            return {
                'system': 'legacy',
                'product_id': product.id,
                'ingredients': [
                    {
                        'ingredient_id': ri.ingredient_id,
                        'ingredient_name': ri.ingredient.name if ri.ingredient else '?',
                        'quantity': float(ri.quantity),
                        'unit': ri.ingredient.unit if hasattr(ri.ingredient, 'unit') else 'ml'
                    }
                    for ri in recipe_items
                ]
            }
    except Exception as e:
        current_app.logger.warning(f"Error al buscar receta en sistema legacy: {e}")
    
    return None


def has_recipe(product) -> bool:
    """
    Verifica si un producto tiene receta (en cualquier sistema).
    
    Args:
        product: Objeto Product
        
    Returns:
        bool: True si tiene receta, False si no
    """
    return get_product_recipe(product) is not None


def get_recipe_ingredients(product) -> List[Dict[str, Any]]:
    """
    Obtiene la lista de ingredientes de la receta de un producto.
    
    Args:
        product: Objeto Product
        
    Returns:
        List[Dict]: Lista de ingredientes con sus cantidades
    """
    recipe = get_product_recipe(product)
    if not recipe:
        return []
    
    if recipe['system'] == 'new':
        return recipe['ingredients']
    else:
        # Convertir formato legacy a formato nuevo
        return [
            {
                'ingredient_id': ing['ingredient_id'],
                'ingredient_name': ing['ingredient_name'],
                'quantity_per_portion': ing['quantity'],  # En legacy se llama 'quantity'
                'unit': ing['unit']
            }
            for ing in recipe['ingredients']
        ]




