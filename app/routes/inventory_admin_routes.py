"""
Rutas mejoradas para administración completa de inventario
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session, current_app
from app.models import db
from app.models.product_models import Product
from app.models.inventory_stock_models import (
    Ingredient, IngredientCategory, IngredientStock, Recipe, RecipeIngredient,
    InventoryMovement
)
from app.application.services.inventory_stock_service import InventoryStockService
from datetime import datetime, timedelta
from app.helpers.timezone_utils import CHILE_TZ

inventory_admin_bp = Blueprint('inventory_admin', __name__, url_prefix='/admin/inventario')


@inventory_admin_bp.route('/')
def dashboard():
    """Panel principal de inventario con estadísticas y resumen"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = InventoryStockService()
        
        # Estadísticas generales
        total_productos = Product.query.filter_by(is_active=True).count()
        productos_con_receta = Product.query.filter_by(is_kit=True, is_active=True).count()
        productos_sin_receta = Product.query.filter_by(is_kit=False, is_active=True).count()
        
        total_ingredientes = Ingredient.query.filter_by(is_active=True).count()
        total_recetas = Recipe.query.filter_by(is_active=True).count()
        
        # Stock por ubicación
        ubicaciones = ['Barra Pista', 'Terraza']
        stock_por_ubicacion = {}
        alertas_stock_bajo = []
        
        for ubicacion in ubicaciones:
            summary = service.get_stock_summary(ubicacion)
            stock_por_ubicacion[ubicacion] = summary
            
            # MEJORA: Usar método mejorado para obtener alertas de stock
            alerts = service.get_low_stock_alerts(location=ubicacion, include_negative=True)
            for alert in alerts:
                alertas_stock_bajo.append({
                    'ubicacion': alert['location'],
                    'ingrediente': alert['ingredient_name'],
                    'stock': alert['quantity'],
                    'tipo': alert['type'],
                    'severity': alert.get('severity', 'warning'),
                    'message': alert.get('message', '')
                })
        
        # Productos con stock bajo
        productos_stock_bajo = Product.query.filter(
            Product.is_active == True,
            Product.stock_minimum.isnot(None),
            Product.stock_minimum > 0,
            Product.stock_quantity.isnot(None),
            Product.stock_quantity <= Product.stock_minimum
        ).all()
        
        # ALERTAS: Productos is_kit=True sin receta
        from app.helpers.product_validation_helper import check_all_kit_products_have_recipes
        total_kit, productos_sin_receta_list = check_all_kit_products_have_recipes()
        alertas_productos_sin_receta = productos_sin_receta_list
        
        # Movimientos recientes
        movimientos_recientes = InventoryMovement.query.order_by(
            InventoryMovement.created_at.desc()
        ).limit(10).all()
        
        # Estadísticas de consumo del día
        fecha_hoy = datetime.now(CHILE_TZ).date()
        consumo_hoy = db.session.query(
            InventoryMovement.ingredient_id,
            db.func.sum(db.func.abs(InventoryMovement.quantity))
        ).filter(
            InventoryMovement.movement_type == InventoryMovement.TYPE_SALE,
            db.func.date(InventoryMovement.created_at) == fecha_hoy
        ).group_by(InventoryMovement.ingredient_id).all()
        
        # MEJORA: Obtener categorías de productos activos (simple y directo)
        categorias_productos = []
        categorias_con_conteo = {}
        
        try:
            # Consulta simple: obtener todas las categorías distintas de productos activos
            categorias_raw = db.session.query(Product.category).filter(
                Product.is_active == True,
                Product.category.isnot(None),
                Product.category != ''
            ).distinct().order_by(Product.category).all()
            
            # Extraer categorías de la tupla
            categorias_productos = [cat[0] for cat in categorias_raw if cat[0]]
            
            # Contar productos por categoría
            for categoria in categorias_productos:
                count = Product.query.filter_by(
                    category=categoria,
                    is_active=True
                ).count()
                categorias_con_conteo[categoria] = count
            
            current_app.logger.info(f"📂 Categorías encontradas: {len(categorias_productos)} - {categorias_productos}")
                
        except Exception as e:
            current_app.logger.error(f"Error al obtener categorías: {e}", exc_info=True)
            categorias_productos = []
            categorias_con_conteo = {}
        
        return render_template(
            'admin/inventory/dashboard.html',
            total_productos=total_productos,
            productos_con_receta=productos_con_receta,
            productos_sin_receta=productos_sin_receta,
            total_ingredientes=total_ingredientes,
            total_recetas=total_recetas,
            stock_por_ubicacion=stock_por_ubicacion,
            alertas_stock_bajo=alertas_stock_bajo,
            productos_stock_bajo=productos_stock_bajo,
            alertas_productos_sin_receta=alertas_productos_sin_receta,
            movimientos_recientes=movimientos_recientes,
            consumo_hoy=consumo_hoy,
            categorias_productos=categorias_productos,
            categorias_con_conteo=categorias_con_conteo
        )
    except Exception as e:
        current_app.logger.error(f"Error en dashboard de inventario: {e}", exc_info=True)
        flash(f'Error al cargar dashboard: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@inventory_admin_bp.route('/products')
def products_view():
    """Vista mejorada de productos con filtros avanzados"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Filtros
        categoria = request.args.get('categoria', '')
        search = request.args.get('search', '')
        stock_filter = request.args.get('stock', '')  # 'all', 'low', 'out', 'ok'
        has_recipe = request.args.get('has_recipe', '')
        is_active = request.args.get('is_active', 'true')
        
        # Query base
        query = Product.query
        
        if categoria:
            query = query.filter_by(category=categoria)
        
        if search:
            # Búsqueda case-insensitive (compatible MySQL)
            from sqlalchemy import func
            query = query.filter(func.lower(Product.name).like(func.lower(f'%{search}%')))
        
        if stock_filter == 'low':
            query = query.filter(
                Product.stock_minimum.isnot(None),
                Product.stock_minimum > 0,
                Product.stock_quantity.isnot(None),
                Product.stock_quantity <= Product.stock_minimum
            )
        elif stock_filter == 'out':
            query = query.filter(
                db.or_(
                    Product.stock_quantity.is_(None),
                    Product.stock_quantity <= 0
                )
            )
        elif stock_filter == 'ok':
            query = query.filter(
                Product.stock_quantity.isnot(None),
                Product.stock_quantity > 0,
                db.or_(
                    Product.stock_minimum.is_(None),
                    Product.stock_minimum == 0,
                    db.and_(
                        Product.stock_minimum.isnot(None),
                        Product.stock_quantity > Product.stock_minimum
                    )
                )
            )
        
        if has_recipe == 'yes':
            query = query.filter_by(is_kit=True)
        elif has_recipe == 'no':
            query = query.filter_by(is_kit=False)
        
        if is_active == 'true':
            query = query.filter_by(is_active=True)
        elif is_active == 'false':
            query = query.filter_by(is_active=False)
        
        # Ordenar
        query = query.order_by(Product.category, Product.name)
        
        productos = query.all()
        
        # Agrupar por categoría
        productos_por_categoria = {}
        for producto in productos:
            categoria = producto.category or 'Sin Categoría'
            if categoria not in productos_por_categoria:
                productos_por_categoria[categoria] = []
            productos_por_categoria[categoria].append(producto)
        
        # Obtener categorías para filtro
        categorias = db.session.query(Product.category).distinct().order_by(Product.category).all()
        categorias = [c[0] for c in categorias if c[0]]
        
        # Verificar recetas
        productos_con_receta = {r.product_id for r in Recipe.query.filter_by(is_active=True).all()}
        
        def recipe_exists(product_id):
            return product_id in productos_con_receta
        
        return render_template(
            'admin/inventory/products.html',
            productos_por_categoria=productos_por_categoria,
            categorias=categorias,
            categoria_actual=categoria,
            search=search,
            stock_filter=stock_filter,
            has_recipe=has_recipe,
            is_active=is_active,
            recipe_exists=recipe_exists,
            total_productos=len(productos)
        )
    except Exception as e:
        current_app.logger.error(f"Error al listar productos: {e}", exc_info=True)
        flash(f'Error al cargar productos: {str(e)}', 'error')
        return redirect(url_for('routes.admin_dashboard'))


@inventory_admin_bp.route('/ingredients-stock')
def ingredients_stock_view():
    """Vista de stock de ingredientes por ubicación"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        service = InventoryStockService()
        ubicacion_seleccionada = request.args.get('ubicacion', 'Barra Pista')
        
        # Obtener stock de la ubicación seleccionada
        stock_summary = service.get_stock_summary(ubicacion_seleccionada)
        
        # Obtener todos los ingredientes para comparar
        todos_ingredientes = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.name).all()
        
        # Crear mapa de stock por ingrediente
        stock_map = {s['ingredient_id']: s for s in stock_summary['ingredients']}
        
        # Agrupar ingredientes por categoría
        ingredientes_por_categoria = {}
        for ingrediente in todos_ingredientes:
            categoria = ingrediente.category.name if ingrediente.category else 'Sin Categoría'
            if categoria not in ingredientes_por_categoria:
                ingredientes_por_categoria[categoria] = []
            
            stock_info = stock_map.get(ingrediente.id, {
                'quantity': 0.0,
                'is_negative': False
            })
            
            ingredientes_por_categoria[categoria].append({
                'ingrediente': ingrediente,
                'stock': stock_info
            })
        
        # Ubicaciones disponibles
        ubicaciones = ['Barra Pista', 'Terraza']
        
        return render_template(
            'admin/inventory/ingredients_stock.html',
            ingredientes_por_categoria=ingredientes_por_categoria,
            ubicacion_seleccionada=ubicacion_seleccionada,
            ubicaciones=ubicaciones,
            stock_summary=stock_summary
        )
    except Exception as e:
        current_app.logger.error(f"Error al cargar stock de ingredientes: {e}", exc_info=True)
        flash(f'Error al cargar stock: {str(e)}', 'error')
        return redirect(url_for('inventory_admin.dashboard'))


@inventory_admin_bp.route('/stock-entry')
def stock_entry_view():
    """
    MEJORA: Vista para ingresar compras/entradas de stock de ingredientes.
    Permite registrar entradas de stock de manera fácil y rápida.
    """
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Obtener ingredientes activos agrupados por categoría
        ingredientes = Ingredient.query.filter_by(is_active=True).order_by(Ingredient.name).all()
        
        ingredientes_por_categoria = {}
        for ingrediente in ingredientes:
            categoria = ingrediente.category.name if ingrediente.category else 'Sin Categoría'
            if categoria not in ingredientes_por_categoria:
                ingredientes_por_categoria[categoria] = []
            ingredientes_por_categoria[categoria].append(ingrediente)
        
        # Ubicaciones disponibles
        ubicaciones = ['Barra Pista', 'Terraza', 'Bodega']
        
        # Obtener ubicaciones desde PosRegister si están configuradas
        try:
            from app.models.pos_models import PosRegister
            registers = PosRegister.query.filter_by(is_active=True).all()
            for register in registers:
                if register.location and register.location not in ubicaciones:
                    ubicaciones.append(register.location)
        except:
            pass
        
        return render_template(
            'admin/inventory/stock_entry.html',
            ingredientes_por_categoria=ingredientes_por_categoria,
            ubicaciones=ubicaciones
        )
    except Exception as e:
        current_app.logger.error(f"Error al cargar vista de entrada de stock: {e}", exc_info=True)
        flash(f'Error al cargar vista: {str(e)}', 'error')
        return redirect(url_for('inventory_admin.dashboard'))


@inventory_admin_bp.route('/api/toggle-product-active', methods=['POST'])
def api_toggle_product_active():
    """
    MEJORA: API para activar/desactivar productos.
    Útil para desactivar productos automáticamente cuando falta stock.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        product_id = request.json.get('product_id', type=int)
        is_active = request.json.get('is_active', type=bool)
        
        if product_id is None:
            return jsonify({'success': False, 'error': 'ID de producto requerido'}), 400
        
        product = Product.query.get_or_404(product_id)
        product.is_active = is_active
        db.session.commit()
        
        action = 'activado' if is_active else 'desactivado'
        current_app.logger.info(f"✅ Producto {action}: {product.name} (ID: {product_id})")
        
        return jsonify({
            'success': True,
            'message': f'Producto "{product.name}" {action} exitosamente',
            'is_active': is_active
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al cambiar estado de producto: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/api/auto-disable-low-stock', methods=['POST'])
def api_auto_disable_low_stock():
    """
    MEJORA: API para desactivar automáticamente productos con stock bajo o sin stock.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        # Productos sin stock
        productos_sin_stock = Product.query.filter(
            Product.is_active == True,
            db.or_(
                Product.stock_quantity.is_(None),
                Product.stock_quantity <= 0
            )
        ).all()
        
        # Productos con stock bajo (opcional)
        solo_sin_stock = request.json.get('solo_sin_stock', True)
        productos_bajo_stock = []
        
        if not solo_sin_stock:
            productos_bajo_stock = Product.query.filter(
                Product.is_active == True,
                Product.stock_minimum > 0,
                Product.stock_quantity > 0,
                Product.stock_quantity <= Product.stock_minimum
            ).all()
        
        productos_desactivados = []
        
        # Desactivar productos sin stock
        for producto in productos_sin_stock:
            producto.is_active = False
            productos_desactivados.append({
                'id': producto.id,
                'name': producto.name,
                'reason': 'Sin stock'
            })
        
        # Desactivar productos con stock bajo si se solicita
        if not solo_sin_stock:
            for producto in productos_bajo_stock:
                producto.is_active = False
                productos_desactivados.append({
                    'id': producto.id,
                    'name': producto.name,
                    'reason': f'Stock bajo ({producto.stock_quantity}/{producto.stock_minimum})'
                })
        
        db.session.commit()
        
        current_app.logger.info(
            f"✅ {len(productos_desactivados)} productos desactivados automáticamente por falta de stock"
        )
        
        return jsonify({
            'success': True,
            'message': f'{len(productos_desactivados)} productos desactivados',
            'productos_desactivados': productos_desactivados,
            'count': len(productos_desactivados)
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al desactivar productos: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/movements')
def movements_view():
    """Vista de movimientos de inventario"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.login_admin'))
    
    try:
        # Filtros
        ubicacion = request.args.get('ubicacion', '')
        tipo_movimiento = request.args.get('tipo', '')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = InventoryMovement.query
        
        if ubicacion:
            query = query.filter_by(location=ubicacion)
        
        if tipo_movimiento:
            query = query.filter_by(movement_type=tipo_movimiento)
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
                query = query.filter(InventoryMovement.created_at >= fecha_desde_dt)
            except:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(InventoryMovement.created_at < fecha_hasta_dt)
            except:
                pass
        
        query = query.order_by(InventoryMovement.created_at.desc())
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        movimientos = pagination.items
        
        ubicaciones = ['Barra Pista', 'Terraza']
        tipos_movimiento = [
            InventoryMovement.TYPE_ENTRY,
            InventoryMovement.TYPE_SALE,
            InventoryMovement.TYPE_ADJUSTMENT,
            InventoryMovement.TYPE_WASTE,
            InventoryMovement.TYPE_CORRECTION
        ]
        
        return render_template(
            'admin/inventory/movements.html',
            movimientos=movimientos,
            pagination=pagination,
            ubicaciones=ubicaciones,
            tipos_movimiento=tipos_movimiento,
            ubicacion_actual=ubicacion,
            tipo_actual=tipo_movimiento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
    except Exception as e:
        current_app.logger.error(f"Error al cargar movimientos: {e}", exc_info=True)
        flash(f'Error al cargar movimientos: {str(e)}', 'error')
        return redirect(url_for('inventory_admin.dashboard'))


@inventory_admin_bp.route('/api/quick-update-stock', methods=['POST'])
def api_quick_update_stock():
    """API para actualización rápida de stock de producto"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        product_id = request.json.get('product_id')
        stock_quantity = request.json.get('stock_quantity', type=int)
        
        if not product_id:
            return jsonify({'success': False, 'error': 'ID de producto requerido'}), 400
        
        product = Product.query.get_or_404(product_id)
        product.stock_quantity = stock_quantity
        db.session.commit()
        
        current_app.logger.info(f"✅ Stock actualizado: {product.name} -> {stock_quantity}")
        return jsonify({
            'success': True,
            'message': f'Stock de "{product.name}" actualizado a {stock_quantity}',
            'stock_quantity': stock_quantity
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar stock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/api/quick-update-price', methods=['POST'])
def api_quick_update_price():
    """API para actualización rápida de precio"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        product_id = request.json.get('product_id')
        price = request.json.get('price', type=int)
        
        if not product_id or price is None or price < 0:
            return jsonify({'success': False, 'error': 'Datos inválidos'}), 400
        
        product = Product.query.get_or_404(product_id)
        product.price = price
        db.session.commit()
        
        current_app.logger.info(f"✅ Precio actualizado: {product.name} -> ${price}")
        return jsonify({
            'success': True,
            'message': f'Precio de "{product.name}" actualizado a ${price:,}',
            'price': price
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error al actualizar precio: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/api/add-stock-entry', methods=['POST'])
def api_add_stock_entry():
    """API para agregar entrada de stock de ingrediente"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        ingredient_id = request.json.get('ingredient_id', type=int)
        ubicacion = request.json.get('ubicacion')
        quantity = request.json.get('quantity', type=float)
        reason = request.json.get('reason', '')
        
        if not ingredient_id or not ubicacion or not quantity:
            return jsonify({'success': False, 'error': 'Datos incompletos'}), 400
        
        service = InventoryStockService()
        success, message = service.register_stock_entry(
            ingredient_id=ingredient_id,
            location=ubicacion,
            quantity=quantity,
            user_id=session.get('admin_user', 'admin'),
            user_name=session.get('admin_username', 'Admin'),
            reason=reason or 'Entrada manual'
        )
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        current_app.logger.error(f"Error al agregar entrada de stock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/api/alerts', methods=['GET'])
def api_get_alerts():
    """API para obtener alertas del sistema (productos sin receta, stock negativo, etc.)"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        alerts = {
            'productos_sin_receta': [],
            'stock_negativo': [],
            'recetas_duplicadas': []
        }
        
        # Productos is_kit=True sin receta
        from app.helpers.product_validation_helper import check_all_kit_products_have_recipes
        total_kit, productos_sin_receta = check_all_kit_products_have_recipes()
        alerts['productos_sin_receta'] = productos_sin_receta
        
        # Stock negativo
        stock_negativo = IngredientStock.query.filter(
            IngredientStock.quantity < 0
        ).order_by(IngredientStock.quantity.asc()).limit(50).all()
        
        for stock in stock_negativo:
            alerts['stock_negativo'].append({
                'ingredient_id': stock.ingredient_id,
                'ingredient_name': stock.ingredient.name if stock.ingredient else '?',
                'location': stock.location,
                'quantity': float(stock.quantity),
                'unit': stock.ingredient.base_unit if stock.ingredient else '?'
            })
        
        # Recetas duplicadas (nuevo + legacy)
        from app.models.recipe_models import ProductRecipe
        productos_duplicados = db.session.query(Product).join(
            Recipe, (Recipe.product_id == Product.id) & (Recipe.is_active == True)
        ).join(
            ProductRecipe, ProductRecipe.product_id == Product.id
        ).distinct().all()
        
        for p in productos_duplicados:
            alerts['recetas_duplicadas'].append({
                'product_id': p.id,
                'product_name': p.name,
                'category': p.category
            })
        
        total_alertas = (
            len(alerts['productos_sin_receta']) +
            len(alerts['stock_negativo']) +
            len(alerts['recetas_duplicadas'])
        )
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'total_alertas': total_alertas,
            'timestamp': datetime.now(CHILE_TZ).isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener alertas: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_admin_bp.route('/api/stock-alerts', methods=['GET'])
def api_get_stock_alerts():
    """
    MEJORA: API específica para obtener solo alertas de stock bajo.
    Usa el nuevo sistema mejorado de alertas.
    """
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'error': 'No autenticado'}), 401
    
    try:
        location = request.args.get('location')  # Opcional: filtrar por ubicación
        service = InventoryStockService()
        
        alerts = service.get_low_stock_alerts(
            location=location if location else None,
            include_negative=True
        )
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': datetime.now(CHILE_TZ).isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Error al obtener alertas de stock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



