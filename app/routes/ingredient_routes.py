"""
Rutas para gestión de ingredientes y recetas
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from app.models import db
from app.models.product_models import Product
from app.models.inventory_stock_models import (
    Ingredient, IngredientCategory, Recipe, RecipeIngredient
)
from app.application.services.inventory_stock_service import InventoryStockService

ingredient_bp = Blueprint('ingredients', __name__, url_prefix='/admin/ingredients')


@ingredient_bp.route('/')
def list_ingredients():
    """Lista todos los ingredientes organizados por categoría"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener ingredientes agrupados por categoría
        categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
        ingredientes_por_categoria = {}
        ingredientes_sin_categoria = []
        
        for categoria in categorias:
            ingredientes = Ingredient.query.filter_by(
                category_id=categoria.id,
                is_active=True
            ).order_by(Ingredient.name).all()
            if ingredientes:
                ingredientes_por_categoria[categoria.name] = ingredientes
        
        # Ingredientes sin categoría
        ingredientes_sin_cat = Ingredient.query.filter_by(
            category_id=None,
            is_active=True
        ).order_by(Ingredient.name).all()
        if ingredientes_sin_cat:
            ingredientes_por_categoria['Sin Categoría'] = ingredientes_sin_cat
        
        total_ingredientes = Ingredient.query.filter_by(is_active=True).count()
        total_categorias = len(ingredientes_por_categoria)
        
        return render_template(
            'admin/ingredients/list.html',
            ingredientes_por_categoria=ingredientes_por_categoria,
            categorias=categorias,
            total_ingredientes=total_ingredientes,
            total_categorias=total_categorias
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar ingredientes: {e}", exc_info=True)
        flash(f'Error al cargar ingredientes: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@ingredient_bp.route('/categories')
def list_categories():
    """Lista todas las categorías de ingredientes"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        categorias = IngredientCategory.query.order_by(IngredientCategory.name).all()
        return render_template('admin/ingredients/categories.html', categorias=categorias)
    except Exception as e:
        current_app.logger.error(f"Error al listar categorías: {e}", exc_info=True)
        flash(f'Error al cargar categorías: {str(e)}', 'error')
        return redirect(url_for('ingredients.list_ingredients'))


@ingredient_bp.route('/category/create', methods=['POST'])
def create_category():
    """Crear nueva categoría de ingrediente"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'error': 'El nombre es requerido'}), 400
        
        # Verificar si ya existe
        existing = IngredientCategory.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'error': f'Ya existe una categoría con el nombre "{name}"'}), 400
        
        categoria = IngredientCategory(
            name=name,
            description=description or None,
            is_active=True
        )
        
        db.session.add(categoria)
        db.session.commit()
        
        current_app.logger.info(f"✅ Categoría creada: {name}")
        return jsonify({'success': True, 'message': f'Categoría "{name}" creada', 'category': categoria.to_dict()})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al crear categoría: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ingredient_bp.route('/create', methods=['GET', 'POST'])
def create_ingredient():
    """Crear nuevo ingrediente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id', type=int) or None
            base_unit = request.form.get('base_unit', 'ml').strip()
            package_size = request.form.get('package_size', type=float) or None
            package_unit = request.form.get('package_unit', '').strip() or None
            cost_per_unit = request.form.get('cost_per_unit', type=float) or 0.0
            description = request.form.get('description', '').strip() or None
            
            if not name:
                flash('El nombre del ingrediente es requerido', 'error')
                categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
                return render_template('admin/ingredients/form.html', ingredient=None, categorias=categorias)
            
            # Verificar si ya existe
            existing = Ingredient.query.filter_by(name=name).first()
            if existing:
                flash(f'Ya existe un ingrediente con el nombre "{name}"', 'error')
                categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
                return render_template('admin/ingredients/form.html', ingredient=None, categorias=categorias)
            
            service = InventoryStockService()
            success, message, ingredient = service.create_ingredient(
                name=name,
                base_unit=base_unit,
                category_id=category_id,
                package_size=package_size,
                package_unit=package_unit,
                cost_per_unit=cost_per_unit,
                description=description
            )
            
            if success:
                flash(message, 'success')
                return redirect(url_for('ingredients.list_ingredients'))
            else:
                flash(message, 'error')
        except Exception as e:
            current_app.logger.error(f"Error al crear ingrediente: {e}", exc_info=True)
            flash(f'Error al crear ingrediente: {str(e)}', 'error')
    
    categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
    return render_template('admin/ingredients/form.html', ingredient=None, categorias=categorias)


@ingredient_bp.route('/<int:ingredient_id>/edit', methods=['GET', 'POST'])
def edit_ingredient(ingredient_id):
    """Editar ingrediente existente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    ingredient = Ingredient.query.get_or_404(ingredient_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category_id = request.form.get('category_id', type=int) or None
            base_unit = request.form.get('base_unit', 'ml').strip()
            package_size = request.form.get('package_size', type=float) or None
            package_unit = request.form.get('package_unit', '').strip() or None
            cost_per_unit = request.form.get('cost_per_unit', type=float) or 0.0
            description = request.form.get('description', '').strip() or None
            is_active = request.form.get('is_active') == 'on'
            
            if not name:
                flash('El nombre del ingrediente es requerido', 'error')
                categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
                return render_template('admin/ingredients/form.html', ingredient=ingredient, categorias=categorias)
            
            # Verificar si el nombre ya existe en otro ingrediente
            existing = Ingredient.query.filter(Ingredient.name == name, Ingredient.id != ingredient_id).first()
            if existing:
                flash(f'Ya existe otro ingrediente con el nombre "{name}"', 'error')
                categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
                return render_template('admin/ingredients/form.html', ingredient=ingredient, categorias=categorias)
            
            # Actualizar ingrediente
            ingredient.name = name
            ingredient.category_id = category_id
            ingredient.base_unit = base_unit
            ingredient.package_size = package_size
            ingredient.package_unit = package_unit
            ingredient.cost_per_unit = cost_per_unit
            ingredient.description = description
            ingredient.is_active = is_active
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Ingrediente actualizado: {name} (ID: {ingredient_id})")
            flash(f'Ingrediente "{name}" actualizado exitosamente', 'success')
            return redirect(url_for('ingredients.list_ingredients'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar ingrediente: {e}", exc_info=True)
            flash(f'Error al actualizar ingrediente: {str(e)}', 'error')
    
    categorias = IngredientCategory.query.filter_by(is_active=True).order_by(IngredientCategory.name).all()
    return render_template('admin/ingredients/form.html', ingredient=ingredient, categorias=categorias)


@ingredient_bp.route('/recipes')
def list_recipes():
    """Lista todas las recetas (productos con ingredientes)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener productos que tienen recetas
        recipes = Recipe.query.filter_by(is_active=True).order_by(Recipe.id).all()
        
        # Obtener productos sin receta pero que son kits
        products_without_recipe = Product.query.filter_by(
            is_kit=True,
            is_active=True
        ).all()
        products_without_recipe_ids = {r.product_id for r in recipes}
        products_without_recipe = [p for p in products_without_recipe if p.id not in products_without_recipe_ids]
        
        return render_template(
            'admin/ingredients/recipes.html',
            recipes=recipes,
            products_without_recipe=products_without_recipe
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar recetas: {e}", exc_info=True)
        flash(f'Error al cargar recetas: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@ingredient_bp.route('/recipe/<int:product_id>', methods=['GET', 'POST'])
def manage_recipe(product_id):
    """Gestionar receta de un producto"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    product = Product.query.get_or_404(product_id)
    recipe = Recipe.query.filter_by(product_id=product_id).first()
    
    if request.method == 'POST':
        try:
            # Obtener ingredientes de la receta
            ingredient_ids = request.form.getlist('ingredient_id[]')
            quantities = request.form.getlist('quantity_per_portion[]')
            
            # Crear o actualizar receta
            if not recipe:
                recipe = Recipe(
                    product_id=product_id,
                    is_active=True
                )
                db.session.add(recipe)
                db.session.flush()
            else:
                # Eliminar ingredientes existentes
                RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
            
            # Agregar ingredientes
            for ingredient_id_str, quantity_str in zip(ingredient_ids, quantities):
                if not ingredient_id_str or not quantity_str:
                    continue
                
                try:
                    ingredient_id = int(ingredient_id_str)
                    quantity = float(quantity_str)
                    
                    if quantity > 0:
                        recipe_ingredient = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ingredient_id,
                            quantity_per_portion=quantity
                        )
                        db.session.add(recipe_ingredient)
                except (ValueError, TypeError):
                    continue
            
            # Marcar producto como kit
            product.is_kit = True
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Receta actualizada para producto: {product.name}")
            flash(f'Receta de "{product.name}" guardada exitosamente', 'success')
            return redirect(url_for('ingredients.list_recipes'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al guardar receta: {e}", exc_info=True)
            flash(f'Error al guardar receta: {str(e)}', 'error')
    
    # Obtener ingredientes disponibles
    ingredients = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.name).all()
    
    # Obtener ingredientes actuales de la receta
    recipe_ingredients = []
    if recipe:
        recipe_ingredients = RecipeIngredient.query.filter_by(recipe_id=recipe.id).all()
    
    return render_template(
        'admin/ingredients/recipe_form.html',
        product=product,
        recipe=recipe,
        ingredients=ingredients,
        recipe_ingredients=recipe_ingredients
    )





