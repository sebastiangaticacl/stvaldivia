"""
Rutas para gestión de productos
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from sqlalchemy import func
from app.models import db
from app.models.product_models import Product

product_bp = Blueprint('products', __name__, url_prefix='/admin/products')


@product_bp.route('/')
def list_products():
    """Lista todos los productos"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener parámetros de filtro
        categoria = request.args.get('categoria', '')
        search = request.args.get('search', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Construir query
        query = Product.query
        
        if categoria:
            query = query.filter_by(category=categoria)
        
        if search:
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(func.lower(Product.name).like(func.lower(f'%{search}%')))
        
        # Ordenar por categoría y nombre
        query = query.order_by(Product.category, Product.name)
        
        # Paginación
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        products = pagination.items
        
        # Obtener todas las categorías para el filtro
        categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
        categorias = [c[0] for c in categorias if c[0]]
        
        return render_template(
            'admin/products/list.html',
            products=products,
            pagination=pagination,
            categorias=categorias,
            categoria_actual=categoria,
            search=search
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar productos: {e}", exc_info=True)
        flash(f'Error al cargar productos: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@product_bp.route('/create', methods=['GET', 'POST'])
def create_product():
    """Crear nuevo producto"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            category = request.form.get('category', '').strip()
            price = request.form.get('price', type=int)
            cost_price = request.form.get('cost_price', type=int) or 0
            stock_quantity = request.form.get('stock_quantity', type=int) or 0
            stock_minimum = request.form.get('stock_minimum', type=int) or 0
            is_active = request.form.get('is_active') == 'on'
            is_kit = request.form.get('is_kit') == 'on'
            
            # Validaciones
            if not name:
                flash('El nombre del producto es requerido', 'error')
                categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
                categorias = [c[0] for c in categorias if c[0]]
                return render_template('admin/products/form.html', product=None, categorias=categorias)
            
            if price is None or price < 0:
                flash('El precio debe ser un número positivo', 'error')
                categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
                categorias = [c[0] for c in categorias if c[0]]
                return render_template('admin/products/form.html', product=None, categorias=categorias)
            
            # Verificar si ya existe
            existing = Product.query.filter_by(name=name).first()
            if existing:
                flash(f'Ya existe un producto con el nombre "{name}"', 'error')
                categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
                categorias = [c[0] for c in categorias if c[0]]
                return render_template('admin/products/form.html', product=None, categorias=categorias)
            
            # Crear producto
            product = Product(
                name=name,
                category=category or None,
                price=price,
                cost_price=cost_price,
                stock_quantity=stock_quantity,
                stock_minimum=stock_minimum,
                is_active=is_active,
                is_kit=is_kit
            )
            
            db.session.add(product)
            db.session.commit()
            
            current_app.logger.info(f"✅ Producto creado: {name} (ID: {product.id})")
            flash(f'Producto "{name}" creado exitosamente', 'success')
            
            # Si el producto usa receta, redirigir a la página de gestión de receta
            if is_kit:
                flash('Ahora puedes configurar los ingredientes de la receta', 'info')
                return redirect(url_for('ingredients.manage_recipe', product_id=product.id))
            
            return redirect(url_for('products.list_products'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear producto: {e}", exc_info=True)
            flash(f'Error al crear producto: {str(e)}', 'error')
    
    # Obtener categorías existentes para el select
    categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
    categorias = [c[0] for c in categorias if c[0]]
    
    return render_template('admin/products/form.html', product=None, categorias=categorias, has_recipe=False)


@product_bp.route('/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    """Editar producto existente"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            # Si hay nueva categoría, usar esa; sino usar la seleccionada
            category = request.form.get('new_category', '').strip() or request.form.get('category', '').strip()
            # Limpiar si es el valor especial "__new__"
            if category == '__new__':
                category = request.form.get('new_category', '').strip()
            price = request.form.get('price', type=int)
            cost_price = request.form.get('cost_price', type=int) or 0
            stock_quantity = request.form.get('stock_quantity', type=int) or 0
            stock_minimum = request.form.get('stock_minimum', type=int) or 0
            is_active = request.form.get('is_active') == 'on'
            is_kit = request.form.get('is_kit') == 'on'
            
            # Validaciones
            if not name:
                flash('El nombre del producto es requerido', 'error')
                categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
                categorias = [c[0] for c in categorias if c[0]]
                return render_template('admin/products/form.html', product=product, categorias=categorias)
            
            if price is None or price < 0:
                flash('El precio debe ser un número positivo', 'error')
                return render_template('admin/products/form.html', product=product, categorias=categorias)
            
            # Verificar si el nombre ya existe en otro producto
            existing = Product.query.filter(Product.name == name, Product.id != product_id).first()
            if existing:
                flash(f'Ya existe otro producto con el nombre "{name}"', 'error')
                return render_template('admin/products/form.html', product=product, categorias=categorias)
            
            # Actualizar producto
            product.name = name
            product.category = category or None
            product.price = price
            product.cost_price = cost_price
            product.stock_quantity = stock_quantity
            product.stock_minimum = stock_minimum
            product.is_active = is_active
            product.is_kit = is_kit
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Producto actualizado: {name} (ID: {product_id})")
            flash(f'Producto "{name}" actualizado exitosamente', 'success')
            
            # Si el producto usa receta, redirigir a la página de gestión de receta
            if is_kit:
                # Verificar si ya tiene receta
                from app.models.inventory_stock_models import Recipe
                recipe = Recipe.query.filter_by(product_id=product_id).first()
                if not recipe:
                    flash('Ahora puedes configurar los ingredientes de la receta', 'info')
                    return redirect(url_for('ingredients.manage_recipe', product_id=product_id))
                else:
                    flash('Puedes actualizar la receta si es necesario', 'info')
                    return redirect(url_for('ingredients.manage_recipe', product_id=product_id))
            
            return redirect(url_for('products.list_products'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar producto: {e}", exc_info=True)
            flash(f'Error al actualizar producto: {str(e)}', 'error')
    
    # Obtener categorías existentes
    categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
    categorias = [c[0] for c in categorias if c[0]]
    
    # Verificar si el producto tiene receta configurada
    has_recipe = False
    if product and product.is_kit:
        from app.models.inventory_stock_models import Recipe
        recipe = Recipe.query.filter_by(product_id=product_id, is_active=True).first()
        has_recipe = recipe is not None
    
    return render_template('admin/products/form.html', product=product, categorias=categorias, has_recipe=has_recipe)


@product_bp.route('/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    """Eliminar producto (soft delete - desactivar)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        product = Product.query.get_or_404(product_id)
        product.is_active = False
        db.session.commit()
        
        current_app.logger.info(f"✅ Producto desactivado: {product.name} (ID: {product_id})")
        return jsonify({'success': True, 'message': f'Producto "{product.name}" desactivado'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al eliminar producto: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@product_bp.route('/<int:product_id>/toggle-status', methods=['POST'])
def toggle_product_status(product_id):
    """Activar/desactivar producto rápidamente"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        product = Product.query.get_or_404(product_id)
        product.is_active = not product.is_active
        status = 'activado' if product.is_active else 'desactivado'
        db.session.commit()
        
        current_app.logger.info(f"✅ Producto {status}: {product.name} (ID: {product_id})")
        return jsonify({
            'success': True, 
            'message': f'Producto "{product.name}" {status}',
            'is_active': product.is_active
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cambiar estado del producto: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@product_bp.route('/api/search')
def api_search():
    """API para buscar productos (para autocompletado)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        search = request.args.get('q', '').strip()
        categoria = request.args.get('categoria', '')
        limit = request.args.get('limit', 20, type=int)
        
        query = Product.query.filter_by(is_active=True)
        
        if categoria:
            query = query.filter_by(category=categoria)
        
        if search:
            # Búsqueda case-insensitive (compatible MySQL)
            query = query.filter(func.lower(Product.name).like(func.lower(f'%{search}%')))
        
        products = query.limit(limit).all()
        
        return jsonify({
            'success': True,
            'products': [p.to_dict() for p in products]
        })
    except Exception as e:
        current_app.logger.error(f"Error en búsqueda de productos: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500





