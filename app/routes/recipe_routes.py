"""
Rutas para mostrar recetas en la app de validación (bartender)
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from app.services.recipe_service import get_recipe_service

recipe_bp = Blueprint('recipes', __name__, url_prefix='/api/recipes')


@recipe_bp.route('/<product_name>')
def get_recipe(product_name):
    """API para obtener receta de un producto (para mostrar en app de validación)"""
    try:
        recipe_service = get_recipe_service()
        receta = recipe_service.get_recipe_for_display(product_name)
        
        if not receta:
            return jsonify({
                'success': False,
                'message': f'Producto "{product_name}" no tiene receta definida'
            }), 404
        
        return jsonify({
            'success': True,
            'receta': receta
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener receta: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@recipe_bp.route('/all')
def get_all_recipes():
    """API para obtener todas las recetas (para sincronización)"""
    try:
        recipe_service = get_recipe_service()
        return jsonify({
            'success': True,
            'recetas': recipe_service.recipes_data
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener todas las recetas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500





