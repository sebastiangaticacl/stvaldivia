"""
Servicio de Gestión de Inventario de Stock
Maneja toda la lógica de negocio para el inventario de ingredientes:
- Entradas de stock (compras/reposición)
- Salidas por ventas (consumo automático)
- Ajustes y mermas
- Control de ubicaciones (barras, bodega)

MEJORAS IMPLEMENTADAS:
- Cache de recetas para mejorar rendimiento
- Optimización de queries (batch loading)
- Mapeo dinámico de ubicaciones desde PosRegister
- Validación previa de stock
- Transacciones atómicas mejoradas
"""
from typing import Optional, Dict, List, Tuple, Any, Set
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from functools import lru_cache
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from app.models import db
from app.models.inventory_stock_models import (
    Ingredient, IngredientStock, Recipe, RecipeIngredient,
    InventoryMovement, IngredientCategory
)
from app.models.product_models import Product
from app.models.pos_models import PosSale, PosSaleItem, PosRegister


class InventoryStockService:
    """
    Servicio principal de gestión de inventario de stock.
    Encapsula toda la lógica de negocio relacionada con ingredientes, recetas y movimientos.
    
    MEJORAS:
    - Cache de recetas (TTL: 5 minutos)
    - Batch loading de productos e ingredientes
    - Mapeo dinámico de ubicaciones
    - Validación previa de stock
    """
    
    # Cache de recetas (se invalida cada 5 minutos)
    _recipe_cache: Dict[int, Tuple[Recipe, datetime]] = {}
    _cache_ttl = timedelta(minutes=5)
    
    def __init__(self):
        """Inicializa el servicio"""
        pass
    
    def _get_recipe_cached(self, product_id: int) -> Optional[Recipe]:
        """
        Obtiene receta con cache para mejorar rendimiento.
        Cache se invalida automáticamente cada 5 minutos.
        """
        now = datetime.utcnow()
        
        # Verificar cache
        if product_id in self._recipe_cache:
            recipe, cached_time = self._recipe_cache[product_id]
            if now - cached_time < self._cache_ttl:
                return recipe
            else:
                # Cache expirado, eliminar
                del self._recipe_cache[product_id]
        
        # Obtener de BD
        recipe = Recipe.query.filter_by(
            product_id=product_id,
            is_active=True
        ).options(
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.ingredient)
        ).first()
        
        # Guardar en cache
        if recipe:
            self._recipe_cache[product_id] = (recipe, now)
        
        return recipe
    
    def _invalidate_recipe_cache(self, product_id: Optional[int] = None):
        """
        Invalida el cache de recetas.
        Si product_id es None, invalida todo el cache.
        """
        if product_id:
            self._recipe_cache.pop(product_id, None)
        else:
            self._recipe_cache.clear()
    
    # ==========================================
    # GESTIÓN DE INGREDIENTES
    # ==========================================
    
    def create_ingredient(
        self,
        name: str,
        base_unit: str = 'ml',
        category_id: Optional[int] = None,
        package_size: Optional[float] = None,
        package_unit: Optional[str] = None,
        cost_per_unit: float = 0.0,
        description: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Ingredient]]:
        """
        Crea un nuevo ingrediente.
        
        Returns:
            Tuple[bool, str, Optional[Ingredient]]: (éxito, mensaje, ingrediente)
        """
        try:
            # Validar que no exista
            existing = Ingredient.query.filter_by(name=name).first()
            if existing:
                return False, f"Ya existe un ingrediente con el nombre '{name}'", None
            
            ingredient = Ingredient(
                name=name,
                base_unit=base_unit,
                category_id=category_id,
                package_size=Decimal(str(package_size)) if package_size else None,
                package_unit=package_unit,
                cost_per_unit=Decimal(str(cost_per_unit)),
                description=description,
                is_active=True
            )
            
            db.session.add(ingredient)
            db.session.commit()
            
            current_app.logger.info(f"✅ Ingrediente creado: {name} ({base_unit})")
            return True, f"Ingrediente '{name}' creado exitosamente", ingredient
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear ingrediente: {e}", exc_info=True)
            return False, f"Error al crear ingrediente: {str(e)}", None
    
    # ==========================================
    # GESTIÓN DE STOCK POR UBICACIÓN
    # ==========================================
    
    def get_stock(self, ingredient_id: int, location: str) -> Optional[IngredientStock]:
        """
        Obtiene el stock de un ingrediente en una ubicación específica.
        Si no existe, retorna None (no crea automáticamente).
        """
        return IngredientStock.query.filter_by(
            ingredient_id=ingredient_id,
            location=location
        ).first()
    
    def get_or_create_stock(self, ingredient_id: int, location: str) -> IngredientStock:
        """
        Obtiene el stock de un ingrediente en una ubicación.
        Si no existe, lo crea con cantidad 0.
        """
        stock = self.get_stock(ingredient_id, location)
        if not stock:
            stock = IngredientStock(
                ingredient_id=ingredient_id,
                location=location,
                quantity=Decimal('0.0')
            )
            db.session.add(stock)
            db.session.flush()
        return stock
    
    def get_all_stock_by_location(self, location: str) -> List[IngredientStock]:
        """Obtiene todo el stock de una ubicación"""
        return IngredientStock.query.filter_by(location=location).all()
    
    # ==========================================
    # ENTRADAS DE STOCK (COMPRAS/REPOSICIÓN)
    # ==========================================
    
    def register_stock_entry(
        self,
        ingredient_id: int,
        location: str,
        quantity: float,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        reason: Optional[str] = None,
        batch_number: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Registra una entrada de stock (compra, reposición).
        
        Args:
            ingredient_id: ID del ingrediente
            location: Ubicación donde entra el stock
            quantity: Cantidad que entra (en unidad base)
            user_id: ID del usuario que registra
            user_name: Nombre del usuario
            reference_type: Tipo de referencia ('purchase', 'transfer', etc.)
            reference_id: ID de la referencia
            reason: Motivo de la entrada
            batch_number: Número de lote/botella (opcional)
        
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            # Validar ingrediente
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return False, f"Ingrediente {ingredient_id} no encontrado"
            
            if quantity <= 0:
                return False, "La cantidad debe ser mayor a 0"
            
            # Obtener o crear stock
            stock = self.get_or_create_stock(ingredient_id, location)
            
            # Actualizar cantidad
            stock.quantity += Decimal(str(quantity))
            if batch_number:
                stock.batch_number = batch_number
            
            # Registrar movimiento
            movement = InventoryMovement(
                ingredient_id=ingredient_id,
                location=location,
                movement_type=InventoryMovement.TYPE_ENTRY,
                quantity=Decimal(str(quantity)),
                reference_type=reference_type,
                reference_id=reference_id,
                user_id=user_id,
                user_name=user_name,
                reason=reason or "Entrada de stock"
            )
            db.session.add(movement)
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Entrada de stock: {ingredient.name} +{quantity} {ingredient.base_unit} @ {location}"
            )
            return True, f"Entrada de {quantity} {ingredient.base_unit} de {ingredient.name} registrada"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar entrada de stock: {e}", exc_info=True)
            return False, f"Error al registrar entrada: {str(e)}"
    
    # ==========================================
    # CONSUMO POR VENTAS (AUTOMÁTICO)
    # ==========================================
    
    def apply_inventory_for_sale(
        self,
        sale: PosSale,
        location: Optional[str] = None
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Aplica el consumo de inventario para una venta.
        Este es el método principal que se llama cuando se confirma una venta.
        
        MEJORAS IMPLEMENTADAS:
        - Cache de recetas para mejorar rendimiento
        - Batch loading de productos e ingredientes (evita N+1 queries)
        - Mapeo dinámico de ubicaciones desde PosRegister
        - Transacciones atómicas mejoradas
        
        Args:
            sale: Objeto PosSale con sus items
            location: Ubicación de donde se descuenta (ej: "barra_principal")
                     Si no se proporciona, se intenta inferir del register_id
        
        Returns:
            Tuple[bool, str, List[Dict]]: (éxito, mensaje, lista de consumos aplicados)
        """
        try:
            # CORRECCIÓN CRÍTICA: Evitar doble descuento
            if sale.inventory_applied:
                current_app.logger.warning(
                    f"⚠️ Inventario ya aplicado para venta #{sale.id} - evitando doble descuento"
                )
                return True, "Inventario ya fue aplicado anteriormente", []
            
            # MEJORA: Mapeo dinámico de ubicación desde PosRegister
            if not location:
                location = self._get_location_from_register(sale.register_id)
            
            if not location:
                return False, "No se pudo determinar la ubicación para descontar inventario", []
            
            # MEJORA: Batch loading de productos (evita N+1 queries)
            product_ids = []
            product_names = []
            for sale_item in sale.items:
                try:
                    product_id_int = int(sale_item.product_id)
                    product_ids.append(product_id_int)
                except (ValueError, TypeError):
                    product_names.append(sale_item.product_name)
            
            # Cargar todos los productos de una vez
            products_dict = {}
            if product_ids:
                products = Product.query.filter(Product.id.in_(product_ids)).all()
                products_dict.update({p.id: p for p in products})
            
            if product_names:
                products_by_name = Product.query.filter(Product.name.in_(product_names)).all()
                products_dict.update({p.name: p for p in products_by_name})
            
            # MEJORA: Pre-cargar todas las recetas necesarias
            recipe_ids_to_load = set()
            for sale_item in sale.items:
                try:
                    product_id_int = int(sale_item.product_id)
                    product = products_dict.get(product_id_int)
                except (ValueError, TypeError):
                    product = products_dict.get(sale_item.product_name)
                
                if product and product.is_kit:
                    recipe = self._get_recipe_cached(product.id)
                    if recipe:
                        recipe_ids_to_load.add(recipe.id)
            
            # Batch loading de ingredientes de recetas
            recipe_ingredients_dict = {}
            if recipe_ids_to_load:
                recipe_ingredients = RecipeIngredient.query.filter(
                    RecipeIngredient.recipe_id.in_(recipe_ids_to_load)
                ).options(
                    joinedload(RecipeIngredient.ingredient)
                ).all()
                
                for ri in recipe_ingredients:
                    if ri.recipe_id not in recipe_ingredients_dict:
                        recipe_ingredients_dict[ri.recipe_id] = []
                    recipe_ingredients_dict[ri.recipe_id].append(ri)
            
            consumos_aplicados = []
            
            # MEJORA: Usar transacción atómica con savepoint para rollback granular
            savepoint = db.session.begin_nested()
            
            try:
                # Procesar cada item de la venta
                for sale_item in sale.items:
                    product_id = sale_item.product_id
                    quantity_sold = sale_item.quantity
                    
                    # Obtener producto del dict pre-cargado
                    try:
                        product_id_int = int(product_id)
                        product = products_dict.get(product_id_int)
                    except (ValueError, TypeError):
                        product = products_dict.get(sale_item.product_name)
                    
                    if not product:
                        current_app.logger.warning(
                            f"⚠️ Producto {product_id} ({sale_item.product_name}) no encontrado - saltando inventario"
                        )
                        continue
                    
                    # Verificar si el producto está marcado como kit
                    from app.helpers.product_validation_helper import validate_product_has_recipe
                    tiene_receta, mensaje_error, recipe_data = validate_product_has_recipe(product)
                    
                    if not product.is_kit:
                        # Producto no usa receta (ej: entradas) - no afecta inventario
                        continue
                    
                    if not tiene_receta:
                        # Producto marcado como kit pero sin receta configurada
                        current_app.logger.warning(
                            f"⚠️ {mensaje_error or f'Producto {product.name} (ID: {product.id}) marcado como kit pero sin receta configurada'}"
                        )
                        continue
                    
                    # MEJORA: Obtener receta del cache
                    recipe = self._get_recipe_cached(product.id)
                    
                    if not recipe:
                        if recipe_data.get('system') == 'legacy':
                            current_app.logger.warning(
                                f"⚠️ Producto {product.name} tiene receta en sistema legacy pero no en sistema nuevo. "
                                f"Por favor, migre la receta usando la interfaz de gestión."
                            )
                        continue
                    
                    # MEJORA: Obtener ingredientes del dict pre-cargado
                    recipe_ingredients = recipe_ingredients_dict.get(recipe.id, [])
                    
                    if not recipe_ingredients:
                        current_app.logger.warning(
                            f"⚠️ Receta {recipe.id} no tiene ingredientes configurados"
                        )
                        continue
                    
                    # Procesar cada ingrediente de la receta
                    for recipe_ingredient in recipe_ingredients:
                        ingredient_id = recipe_ingredient.ingredient_id
                        quantity_per_portion = recipe_ingredient.quantity_per_portion
                        
                        # Calcular consumo total: cantidad por porción * cantidad vendida
                        total_consumption = float(quantity_per_portion) * quantity_sold
                        
                        # Descontar del stock
                        success, message = self._consume_ingredient(
                            ingredient_id=ingredient_id,
                            location=location,
                            quantity=total_consumption,
                            reference_type='sale',
                            reference_id=str(sale.id),
                            user_id=sale.employee_id,
                            user_name=sale.employee_name,
                            reason=f"Venta #{sale.id}: {quantity_sold}x {product.name}"
                        )
                        
                        if success:
                            ingredient = recipe_ingredient.ingredient
                            consumos_aplicados.append({
                                'ingredient_id': ingredient_id,
                                'ingredient_name': ingredient.name if ingredient else '?',
                                'quantity_consumed': total_consumption,
                                'unit': ingredient.base_unit if ingredient else 'ml',
                                'product_name': product.name,
                                'quantity_sold': quantity_sold
                            })
                        else:
                            current_app.logger.warning(
                                f"⚠️ No se pudo descontar {total_consumption} de ingrediente {ingredient_id}: {message}"
                            )
                
                # Si hay consumos aplicados, confirmar savepoint
                if consumos_aplicados:
                    savepoint.commit()
                    
                    # Marcar venta como procesada
                    sale.inventory_applied = True
                    sale.inventory_applied_at = datetime.utcnow()
                    db.session.commit()
                    
                    current_app.logger.info(
                        f"✅ Inventario aplicado para venta #{sale.id}: {len(consumos_aplicados)} consumos"
                    )
                    return True, f"Inventario aplicado: {len(consumos_aplicados)} ingredientes consumidos", consumos_aplicados
                else:
                    # Aunque no haya consumos, marcar como procesado para evitar reintentos
                    savepoint.commit()
                    sale.inventory_applied = True
                    sale.inventory_applied_at = datetime.utcnow()
                    db.session.commit()
                    return True, "Venta procesada (producto sin receta o sin ingredientes)", []
                    
            except Exception as e:
                # Rollback del savepoint en caso de error
                savepoint.rollback()
                raise
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al aplicar inventario para venta: {e}", exc_info=True)
            return False, f"Error al aplicar inventario: {str(e)}", []
    
    def validate_stock_availability(
        self,
        cart: List[Dict[str, Any]],
        location: Optional[str] = None,
        register_id: Optional[str] = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        MEJORA: Valida stock disponible antes de crear una venta.
        
        Args:
            cart: Lista de items del carrito con 'product_id' y 'quantity'
            location: Ubicación donde se va a descontar
            register_id: ID del registro para inferir ubicación si no se proporciona
        
        Returns:
            Tuple[bool, List[Dict]]: (todos_disponibles, lista_de_problemas)
            Problemas incluyen productos con stock insuficiente
        """
        if not location and register_id:
            location = self._get_location_from_register(register_id)
        
        if not location:
            return False, [{'error': 'No se pudo determinar la ubicación'}]
        
        # Obtener todos los productos de una vez
        product_ids = []
        for item in cart:
            try:
                product_ids.append(int(item.get('product_id')))
            except (ValueError, TypeError):
                pass
        
        if not product_ids:
            return True, []  # No hay productos con ID válido
        
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        products_dict = {p.id: p for p in products}
        
        issues = []
        
        for item in cart:
            try:
                product_id = int(item.get('product_id'))
                product = products_dict.get(product_id)
                
                if not product or not product.is_kit:
                    continue
                
                quantity_sold = float(item.get('quantity', 1))
                
                # Obtener receta
                recipe = self._get_recipe_cached(product.id)
                if not recipe:
                    continue
                
                # Obtener ingredientes de la receta
                recipe_ingredients = RecipeIngredient.query.filter_by(
                    recipe_id=recipe.id
                ).options(
                    joinedload(RecipeIngredient.ingredient)
                ).all()
                
                for recipe_ingredient in recipe_ingredients:
                    ingredient_id = recipe_ingredient.ingredient_id
                    quantity_per_portion = float(recipe_ingredient.quantity_per_portion)
                    required = quantity_per_portion * quantity_sold
                    
                    # Obtener stock actual
                    stock = self.get_stock(ingredient_id, location)
                    available = float(stock.quantity) if stock else 0.0
                    
                    if available < required:
                        ingredient = recipe_ingredient.ingredient
                        issues.append({
                            'product_id': product_id,
                            'product_name': product.name,
                            'ingredient_id': ingredient_id,
                            'ingredient_name': ingredient.name if ingredient else '?',
                            'required': required,
                            'available': available,
                            'deficit': required - available,
                            'unit': ingredient.base_unit if ingredient else 'ml'
                        })
            except Exception as e:
                current_app.logger.warning(f"Error al validar stock para item: {e}")
                continue
        
        return len(issues) == 0, issues
    
    def _consume_ingredient(
        self,
        ingredient_id: int,
        location: str,
        quantity: float,
        reference_type: str,
        reference_id: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        MEJORA: Descuenta una cantidad de un ingrediente en una ubicación.
        Usa lock de fila para evitar race conditions.
        
        Método interno usado por apply_inventory_for_sale.
        """
        try:
            # Validar ingrediente
            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                return False, f"Ingrediente {ingredient_id} no encontrado"
            
            if quantity <= 0:
                return False, "La cantidad debe ser mayor a 0"
            
            # MEJORA: Usar lock de fila para evitar race conditions
            from sqlalchemy import select
            from sqlalchemy.orm import with_for_update
            
            # Obtener stock con lock
            stock = db.session.execute(
                select(IngredientStock)
                .filter_by(ingredient_id=ingredient_id, location=location)
                .with_for_update()
            ).scalar_one_or_none()
            
            if not stock:
                # Si no hay stock registrado, crear con cantidad 0 y permitir negativo
                # (esto permite registrar ventas aunque no haya stock inicial)
                stock = IngredientStock(
                    ingredient_id=ingredient_id,
                    location=location,
                    quantity=Decimal('0.0')
                )
                db.session.add(stock)
                db.session.flush()
                current_app.logger.warning(
                    f"⚠️ Stock no existía para {ingredient.name} @ {location}, creado con 0"
                )
            
            # Validar stock antes de descontar
            current_stock = float(stock.quantity)
            quantity_float = float(quantity)
            
            if current_stock < quantity_float:
                # Stock insuficiente - permitir pero alertar
                current_app.logger.warning(
                    f"⚠️ STOCK INSUFICIENTE: {ingredient.name} @ {location} - "
                    f"Disponible: {current_stock:.3f}, Requerido: {quantity_float:.3f}, "
                    f"Déficit: {quantity_float - current_stock:.3f}"
                )
                # Continuar con el descuento (permitir negativo para control de fugas)
                # pero registrar advertencia en el reason
                if reason:
                    reason = f"{reason} [⚠️ STOCK INSUFICIENTE: {current_stock:.3f} disponible]"
                else:
                    reason = f"Consumo por venta [⚠️ STOCK INSUFICIENTE: {current_stock:.3f} disponible]"
            
            # Descontar (permitir negativo para control de fugas)
            stock.quantity -= Decimal(str(quantity))
            
            # Obtener turno_id si existe un turno abierto para esta ubicación
            turno_id_mov = None
            try:
                from app.helpers.turnos_bartender import get_turnos_bartender_helper
                turnos_helper = get_turnos_bartender_helper()
                # Mapear location a formato de ubicación del turno
                ubicacion_turno = location.lower().replace('barra ', 'barra_')
                if user_id:
                    turno_abierto = turnos_helper.get_turno_abierto(user_id, ubicacion_turno)
                    if turno_abierto:
                        turno_id_mov = turno_abierto.id
            except Exception as e:
                current_app.logger.warning(f"Error al obtener turno_id para movimiento: {e}")
            
            # Registrar movimiento negativo
            movement = InventoryMovement(
                ingredient_id=ingredient_id,
                location=location,
                movement_type=InventoryMovement.TYPE_SALE,
                quantity=Decimal(str(-quantity)),  # Negativo = salida
                reference_type=reference_type,
                reference_id=reference_id,
                turno_id=turno_id_mov,  # Asociar con turno si existe
                user_id=user_id,
                user_name=user_name,
                reason=reason or "Consumo por venta"
            )
            db.session.add(movement)
            
            # No hacer commit aquí, se hace en apply_inventory_for_sale
            
            return True, "Consumo registrado"
            
        except Exception as e:
            current_app.logger.error(f"Error al consumir ingrediente: {e}", exc_info=True)
            return False, f"Error: {str(e)}"
    
    def _get_location_from_register(self, register_id: str) -> Optional[str]:
        """
        MEJORA: Obtiene la ubicación desde PosRegister si está configurada.
        Si no está configurada, usa mapeo por defecto.
        
        Args:
            register_id: ID o código del registro/TPV
        
        Returns:
            Ubicación (ej: "Barra Pista", "Terraza") o None
        """
        try:
            # MEJORA: Intentar obtener desde PosRegister
            register = None
            
            # Intentar por ID numérico
            try:
                register_id_int = int(register_id)
                register = PosRegister.query.filter_by(id=register_id_int).first()
            except (ValueError, TypeError):
                pass
            
            # Si no se encontró, intentar por código
            if not register:
                register = PosRegister.query.filter_by(code=register_id).first()
            
            # Si se encontró y tiene location configurada, usarla
            if register and register.location:
                current_app.logger.debug(
                    f"📍 Ubicación obtenida desde PosRegister: {register.location} (TPV: {register.name})"
                )
                return register.location
            
            # MEJORA: Fallback a mapeo por defecto mejorado
            return self._infer_location_from_register(register_id)
            
        except Exception as e:
            current_app.logger.warning(
                f"⚠️ Error al obtener ubicación desde PosRegister: {e}. Usando mapeo por defecto."
            )
            return self._infer_location_from_register(register_id)
    
    def _infer_location_from_register(self, register_id: str) -> Optional[str]:
        """
        Infiere la ubicación (barra) desde el ID de caja usando mapeo por defecto.
        Mapeo: register_id -> location
        Barras disponibles: "Barra Pista" y "Terraza"
        
        Este método se usa como fallback si PosRegister no tiene location configurada.
        """
        # Mapeo de register_id a ubicaciones (fallback)
        location_map = {
            '1': 'Barra Pista',
            '2': 'Terraza',
            # Mapeos alternativos por nombre
            'pista': 'Barra Pista',
            'terraza': 'Terraza',
        }
        
        # Intentar mapeo directo
        register_id_lower = str(register_id).lower().strip()
        if register_id_lower in location_map:
            return location_map[register_id_lower]
        
        # Si el register_id contiene palabras clave
        if 'pista' in register_id_lower or 'principal' in register_id_lower or 'main' in register_id_lower:
            return 'Barra Pista'
        elif 'terraza' in register_id_lower:
            return 'Terraza'
        
        # Por defecto, usar Barra Pista
        current_app.logger.debug(f"📍 Usando ubicación por defecto: Barra Pista (register_id: {register_id})")
        return 'Barra Pista'
    
    # ==========================================
    # AJUSTES Y MERMAS
    # ==========================================
    
    def register_adjustment(
        self,
        ingredient_id: int,
        location: str,
        actual_quantity: float,
        user_id: str,
        user_name: str,
        reason: Optional[str] = None,
        movement_type: str = InventoryMovement.TYPE_ADJUSTMENT
    ) -> Tuple[bool, str]:
        """
        Registra un ajuste de inventario (conteo físico).
        
        Args:
            ingredient_id: ID del ingrediente
            location: Ubicación
            actual_quantity: Cantidad física contada
            user_id: Usuario que hace el ajuste
            user_name: Nombre del usuario
            reason: Motivo del ajuste
            movement_type: Tipo de movimiento ('ajuste' o 'merma')
        
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            # Obtener stock actual
            stock = self.get_or_create_stock(ingredient_id, location)
            theoretical_quantity = float(stock.quantity)
            
            # Calcular diferencia
            difference = actual_quantity - theoretical_quantity
            
            if abs(difference) < 0.001:  # Prácticamente igual
                return True, "No hay diferencia entre teórico y físico"
            
            # Actualizar stock a cantidad física
            stock.quantity = Decimal(str(actual_quantity))
            
            # Registrar movimiento
            movement = InventoryMovement(
                ingredient_id=ingredient_id,
                location=location,
                movement_type=movement_type,
                quantity=Decimal(str(difference)),  # Positivo si sobra, negativo si falta
                reference_type='count',
                reference_id=None,
                user_id=user_id,
                user_name=user_name,
                reason=reason or f"Ajuste: teórico {theoretical_quantity:.3f} → físico {actual_quantity:.3f}"
            )
            db.session.add(movement)
            
            db.session.commit()
            
            ingredient = Ingredient.query.get(ingredient_id)
            current_app.logger.info(
                f"✅ Ajuste registrado: {ingredient.name if ingredient else '?'} "
                f"@ {location}: {difference:+.3f}"
            )
            
            return True, f"Ajuste registrado: diferencia {difference:+.3f}"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al registrar ajuste: {e}", exc_info=True)
            return False, f"Error al registrar ajuste: {str(e)}"
    
    # ==========================================
    # CONSULTAS Y REPORTES
    # ==========================================
    
    def get_theoretical_consumption(
        self,
        ingredient_id: int,
        location: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """
        Calcula el consumo teórico de un ingrediente en un período.
        Suma todos los movimientos de tipo 'venta' (negativos).
        """
        query = db.session.query(
            db.func.sum(InventoryMovement.quantity)
        ).filter_by(
            ingredient_id=ingredient_id,
            location=location,
            movement_type=InventoryMovement.TYPE_SALE
        )
        
        if start_date:
            query = query.filter(InventoryMovement.created_at >= start_date)
        if end_date:
            query = query.filter(InventoryMovement.created_at <= end_date)
        
        result = query.scalar()
        return abs(float(result)) if result else 0.0  # Valor absoluto (son negativos)
    
    def get_stock_summary(self, location: str) -> Dict[str, Any]:
        """
        Obtiene un resumen del stock de una ubicación.
        """
        stocks = self.get_all_stock_by_location(location)
        
        summary = {
            'location': location,
            'total_ingredients': len(stocks),
            'ingredients': []
        }
        
        for stock in stocks:
            ingredient = stock.ingredient
            quantity = float(stock.quantity) if stock.quantity else 0.0
            is_negative = quantity < 0
            
            # MEJORA: Calcular si está bajo umbral (usar 10% del promedio de consumo diario como umbral por defecto)
            is_low = False
            low_threshold = None
            
            if ingredient and not is_negative:
                # Calcular consumo promedio diario de los últimos 7 días
                avg_daily_consumption = self._get_average_daily_consumption(
                    stock.ingredient_id,
                    location,
                    days=7
                )
                
                # Umbral: 10% del consumo diario promedio o mínimo 100 unidades
                low_threshold = max(avg_daily_consumption * 0.1, 100.0)
                is_low = quantity <= low_threshold
            
            summary['ingredients'].append({
                'ingredient_id': stock.ingredient_id,
                'ingredient_name': ingredient.name if ingredient else '?',
                'quantity': quantity,
                'unit': ingredient.base_unit if ingredient else 'ml',
                'is_negative': is_negative,
                'is_low': is_low,
                'low_threshold': low_threshold
            })
        
        return summary
    
    def _get_average_daily_consumption(
        self,
        ingredient_id: int,
        location: str,
        days: int = 7
    ) -> float:
        """
        Calcula el consumo promedio diario de un ingrediente en los últimos N días.
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            total_consumption = self.get_theoretical_consumption(
                ingredient_id=ingredient_id,
                location=location,
                start_date=start_date,
                end_date=end_date
            )
            
            return total_consumption / days if days > 0 else 0.0
        except Exception as e:
            current_app.logger.warning(f"Error al calcular consumo promedio: {e}")
            return 0.0
    
    def get_low_stock_alerts(
        self,
        location: Optional[str] = None,
        include_negative: bool = True
    ) -> List[Dict[str, Any]]:
        """
        MEJORA: Obtiene alertas de stock bajo para una ubicación o todas.
        
        Args:
            location: Ubicación específica o None para todas
            include_negative: Incluir ingredientes con stock negativo
        
        Returns:
            Lista de alertas con información detallada
        """
        alerts = []
        
        # Obtener ubicaciones
        if location:
            locations = [location]
        else:
            # Obtener todas las ubicaciones únicas
            locations = db.session.query(
                IngredientStock.location
            ).distinct().all()
            locations = [loc[0] for loc in locations]
        
        for loc in locations:
            summary = self.get_stock_summary(loc)
            
            for ing in summary['ingredients']:
                if ing['is_negative'] and include_negative:
                    alerts.append({
                        'location': loc,
                        'ingredient_id': ing['ingredient_id'],
                        'ingredient_name': ing['ingredient_name'],
                        'quantity': ing['quantity'],
                        'unit': ing['unit'],
                        'type': 'negative',
                        'severity': 'critical',
                        'message': f"{ing['ingredient_name']} tiene stock negativo ({ing['quantity']:.2f} {ing['unit']})"
                    })
                elif ing.get('is_low', False):
                    alerts.append({
                        'location': loc,
                        'ingredient_id': ing['ingredient_id'],
                        'ingredient_name': ing['ingredient_name'],
                        'quantity': ing['quantity'],
                        'unit': ing['unit'],
                        'low_threshold': ing.get('low_threshold'),
                        'type': 'low',
                        'severity': 'warning',
                        'message': f"{ing['ingredient_name']} está bajo el umbral mínimo ({ing['quantity']:.2f} {ing['unit']} < {ing.get('low_threshold', 0):.2f} {ing['unit']})"
                    })
        
        return alerts
    
    def validate_recipe_completeness(self, recipe_id: int) -> Tuple[bool, List[str]]:
        """
        MEJORA: Valida que una receta esté completa y correcta.
        
        Args:
            recipe_id: ID de la receta a validar
        
        Returns:
            Tuple[bool, List[str]]: (es_válida, lista_de_problemas)
        """
        issues = []
        
        try:
            recipe = Recipe.query.get(recipe_id)
            if not recipe:
                return False, ['Receta no encontrada']
            
            if not recipe.is_active:
                issues.append('Receta está inactiva')
            
            # Validar que tenga ingredientes
            recipe_ingredients = RecipeIngredient.query.filter_by(
                recipe_id=recipe_id
            ).options(
                joinedload(RecipeIngredient.ingredient)
            ).all()
            
            if not recipe_ingredients:
                issues.append('Receta no tiene ingredientes configurados')
                return len(issues) == 0, issues
            
            # Validar cada ingrediente
            for ri in recipe_ingredients:
                if not ri.ingredient:
                    issues.append(f'Ingrediente ID {ri.ingredient_id} no existe')
                    continue
                
                if not ri.ingredient.is_active:
                    issues.append(f'Ingrediente "{ri.ingredient.name}" está inactivo')
                
                if ri.quantity_per_portion <= 0:
                    issues.append(f'Cantidad por porción inválida para "{ri.ingredient.name}" ({ri.quantity_per_portion})')
                
                # Validar unidades de medida (básico: mismo tipo)
                # Esto es una validación básica, se puede mejorar
                if ri.ingredient.base_unit not in ['ml', 'gr', 'unidad', 'g', 'kg', 'l', 'lt']:
                    issues.append(f'Unidad de medida no reconocida para "{ri.ingredient.name}": {ri.ingredient.base_unit}')
            
            # Validar que el producto asociado existe
            if recipe.product_id:
                product = Product.query.get(recipe.product_id)
                if not product:
                    issues.append('Producto asociado no existe')
                elif not product.is_kit:
                    issues.append('Producto asociado no está marcado como kit')
            
            return len(issues) == 0, issues
            
        except Exception as e:
            current_app.logger.error(f"Error al validar receta: {e}", exc_info=True)
            return False, [f'Error al validar receta: {str(e)}']



























