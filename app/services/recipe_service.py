"""
Servicio de gestión de recetas centralizado
Carga recetas desde archivo central y las sincroniza con la base de datos
"""
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app

from app.models import db
from app.models.product_models import Product
from app.models.inventory_stock_models import Recipe, RecipeIngredient, Ingredient


class RecipeService:
    """
    Servicio para gestionar recetas desde archivo central.
    Sincroniza recetas con la base de datos y maneja el consumo por porciones.
    """
    
    def __init__(self):
        """Inicializa el servicio y carga recetas desde archivo"""
        self.recipes_file_path = self._get_recipes_file_path()
        self.recipes_data = self._load_recipes()
    
    def _get_recipes_file_path(self) -> str:
        """Obtiene la ruta del archivo de recetas"""
        # Intentar desde data/recipes.json primero
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        json_path = os.path.join(base_path, 'data', 'recipes.json')
        
        if os.path.exists(json_path):
            return json_path
        
        # Fallback a recipes.py
        py_path = os.path.join(base_path, 'data', 'recipes.py')
        if os.path.exists(py_path):
            return py_path
        
        # Si no existe, crear en data/
        data_dir = os.path.join(base_path, 'data')
        os.makedirs(data_dir, exist_ok=True)
        return json_path
    
    def _load_recipes(self) -> List[Dict[str, Any]]:
        """Carga recetas desde archivo JSON o Python"""
        try:
            if self.recipes_file_path.endswith('.json'):
                with open(self.recipes_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('recetas', [])
            elif self.recipes_file_path.endswith('.py'):
                # Importar dinámicamente desde recipes.py
                import importlib.util
                spec = importlib.util.spec_from_file_location("recipes", self.recipes_file_path)
                recipes_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(recipes_module)
                return getattr(recipes_module, 'RECETAS', [])
        except Exception as e:
            current_app.logger.error(f"Error al cargar recetas: {e}", exc_info=True)
            return []
    
    def save_recipes(self, recipes: List[Dict[str, Any]]) -> bool:
        """Guarda recetas en el archivo JSON"""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "recetas": recipes
            }
            
            with open(self.recipes_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.recipes_data = recipes
            return True
        except Exception as e:
            current_app.logger.error(f"Error al guardar recetas: {e}", exc_info=True)
            return False
    
    def get_recipe(self, product_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la receta de un producto por nombre.
        Primero busca en archivo, luego en base de datos.
        """
        # Buscar en archivo primero
        for receta in self.recipes_data:
            if receta.get('producto', '').lower() == product_name.lower():
                return receta
        
        # Si no está en archivo, buscar en base de datos
        try:
            from app.models.product_models import Product
            from app.models.inventory_stock_models import Recipe, RecipeIngredient
            
            producto = Product.query.filter_by(name=product_name).first()
            if producto:
                receta_db = Recipe.query.filter_by(product_id=producto.id, is_active=True).first()
                if receta_db:
                    # Convertir receta de BD a formato de archivo
                    ingredientes = RecipeIngredient.query.filter_by(recipe_id=receta_db.id).all()
                    insumos_receta = []
                    
                    for rec_ing in ingredientes:
                        ingrediente = rec_ing.ingredient
                        if ingrediente:
                            insumos_receta.append({
                                'insumo': ingrediente.name,
                                'cantidad': float(rec_ing.quantity_per_portion),
                                'unidad': ingrediente.base_unit,
                                'opcional': False
                            })
                    
                    return {
                        'producto': product_name,
                        'categoria': producto.category or '',
                        'precio': float(producto.price) if producto.price else 0.0,
                        'receta': insumos_receta
                    }
        except Exception as e:
            current_app.logger.warning(f"Error al buscar receta en BD: {e}")
        
        return None
    
    def sync_recipes_to_database(self) -> Tuple[int, int, List[str]]:
        """
        Sincroniza recetas del archivo central con la base de datos.
        
        Returns:
            Tuple[int, int, List[str]]: (creadas, actualizadas, errores)
        """
        creadas = 0
        actualizadas = 0
        errores = []
        
        try:
            for receta_data in self.recipes_data:
                producto_nombre = receta_data.get('producto', '').strip()
                categoria = receta_data.get('categoria', '')
                precio = receta_data.get('precio', 0)
                insumos_receta = receta_data.get('receta', [])
                
                if not producto_nombre:
                    continue
                
                # Buscar o crear producto
                product = Product.query.filter_by(name=producto_nombre).first()
                if not product:
                    # Crear producto si no existe
                    product = Product(
                        name=producto_nombre,
                        category=categoria,
                        price=precio,
                        is_active=True,
                        is_kit=len(insumos_receta) > 0  # Tiene receta si tiene insumos
                    )
                    db.session.add(product)
                    db.session.flush()
                    creadas += 1
                else:
                    # Actualizar precio y categoría si cambió
                    if product.price != precio:
                        product.price = precio
                    if product.category != categoria:
                        product.category = categoria
                    product.is_kit = len(insumos_receta) > 0
                    actualizadas += 1
                
                # Si tiene receta, crear/actualizar Recipe
                if insumos_receta:
                    recipe = Recipe.query.filter_by(product_id=product.id).first()
                    
                    if not recipe:
                        recipe = Recipe(
                            product_id=product.id,
                            is_active=True
                        )
                        db.session.add(recipe)
                        db.session.flush()
                    
                    # Eliminar ingredientes existentes
                    RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
                    
                    # Agregar ingredientes de la receta
                    for insumo_data in insumos_receta:
                        insumo_nombre = insumo_data.get('insumo', '').strip()
                        cantidad = insumo_data.get('cantidad', 0)
                        unidad = insumo_data.get('unidad', 'ml')
                        
                        if not insumo_nombre or cantidad <= 0:
                            continue
                        
                        # Buscar ingrediente por nombre
                        ingredient = Ingredient.query.filter_by(name=insumo_nombre).first()
                        if not ingredient:
                            # Crear ingrediente si no existe
                            ingredient = Ingredient(
                                name=insumo_nombre,
                                base_unit=unidad,
                                is_active=True
                            )
                            db.session.add(ingredient)
                            db.session.flush()
                            current_app.logger.info(f"✅ Ingrediente creado automáticamente: {insumo_nombre}")
                        
                        # Crear RecipeIngredient
                        recipe_ingredient = RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ingredient.id,
                            quantity_per_portion=cantidad
                        )
                        db.session.add(recipe_ingredient)
                else:
                    # Si no tiene receta, eliminar Recipe si existe
                    recipe = Recipe.query.filter_by(product_id=product.id).first()
                    if recipe:
                        RecipeIngredient.query.filter_by(recipe_id=recipe.id).delete()
                        db.session.delete(recipe)
                        product.is_kit = False
            
            db.session.commit()
            return creadas, actualizadas, errores
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al sincronizar recetas: {e}", exc_info=True)
            errores.append(str(e))
            return creadas, actualizadas, errores
    
    def apply_recipe_consumption(
        self,
        product_name: str,
        quantity: int,
        location: str,
        bartender_id: Optional[str] = None,
        bartender_name: Optional[str] = None,
        sale_id: Optional[str] = None
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Aplica el consumo de inventario según la receta del producto.
        
        Args:
            product_name: Nombre del producto entregado
            quantity: Cantidad de porciones entregadas
            location: Ubicación (Barra Pista o Terraza)
            bartender_id: ID del bartender que entregó
            bartender_name: Nombre del bartender
            sale_id: ID de la venta (opcional)
        
        Returns:
            Tuple[bool, str, List[Dict]]: (éxito, mensaje, lista de consumos)
        """
        from app.application.services.inventory_stock_service import InventoryStockService
        
        # Obtener receta
        receta_data = self.get_recipe(product_name)
        if not receta_data:
            # Producto sin receta (ej: cerveza) - descontar 1 unidad del producto mismo
            return self._consume_product_unit(product_name, quantity, location, bartender_id, bartender_name, sale_id)
        
        insumos = receta_data.get('receta', [])
        if not insumos:
            # Producto sin receta definida - descontar 1 unidad del producto
            return self._consume_product_unit(product_name, quantity, location, bartender_id, bartender_name, sale_id)
        
        # Aplicar consumo de cada insumo según la receta
        service = InventoryStockService()
        consumos_aplicados = []
        errores = []
        
        for insumo_data in insumos:
            insumo_nombre = insumo_data.get('insumo', '').strip()
            cantidad_por_porcion = insumo_data.get('cantidad', 0)
            opcional = insumo_data.get('opcional', False)
            
            if not insumo_nombre or cantidad_por_porcion <= 0:
                continue
            
            # Buscar ingrediente
            ingredient = Ingredient.query.filter_by(name=insumo_nombre).first()
            if not ingredient:
                if not opcional:
                    errores.append(f"Ingrediente '{insumo_nombre}' no encontrado")
                continue
            
            # Calcular consumo total
            consumo_total = cantidad_por_porcion * quantity
            
            # Obtener turno_id si existe un turno abierto para esta ubicación
            turno_id = None
            try:
                from app.helpers.turnos_bartender import get_turnos_bartender_helper
                turnos_helper = get_turnos_bartender_helper()
                # Mapear location a formato de ubicación del turno
                ubicacion_turno = location.lower().replace('barra ', 'barra_')
                if bartender_id:
                    turno_abierto = turnos_helper.get_turno_abierto(bartender_id, ubicacion_turno)
                    if turno_abierto:
                        turno_id = turno_abierto.id
            except Exception as e:
                current_app.logger.warning(f"Error al obtener turno_id: {e}")
            
            # Descontar del stock
            success, message = service._consume_ingredient(
                ingredient_id=ingredient.id,
                location=location,
                quantity=consumo_total,
                reference_type='delivery',
                reference_id=sale_id or '',
                user_id=bartender_id,
                user_name=bartender_name,
                reason=f"Entrega: {quantity}x {product_name}",
                turno_id=turno_id
            )
            
            if success:
                consumos_aplicados.append({
                    'ingrediente': insumo_nombre,
                    'cantidad': consumo_total,
                    'unidad': ingredient.base_unit,
                    'por_porcion': cantidad_por_porcion,
                    'porciones': quantity
                })
            else:
                errores.append(f"Error al consumir {insumo_nombre}: {message}")
        
        if errores:
            return False, f"Errores: {', '.join(errores)}", consumos_aplicados
        
        mensaje = f"Consumo aplicado: {len(consumos_aplicados)} ingredientes para {quantity}x {product_name}"
        return True, mensaje, consumos_aplicados
    
    def _consume_product_unit(
        self,
        product_name: str,
        quantity: int,
        location: str,
        bartender_id: Optional[str],
        bartender_name: Optional[str],
        sale_id: Optional[str]
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Descuenta unidades del producto mismo (para productos sin receta como cervezas).
        """
        product = Product.query.filter_by(name=product_name).first()
        if not product:
            return False, f"Producto '{product_name}' no encontrado", []
        
        # Descontar stock del producto
        if product.stock_quantity >= quantity:
            product.stock_quantity -= quantity
            db.session.commit()
            return True, f"Stock de {product_name} actualizado: -{quantity}", [{
                'producto': product_name,
                'cantidad': quantity,
                'unidad': 'unidad'
            }]
        else:
            # Permitir negativo para control
            product.stock_quantity -= quantity
            db.session.commit()
            return True, f"Stock de {product_name} actualizado: {product.stock_quantity} (negativo permitido)", [{
                'producto': product_name,
                'cantidad': quantity,
                'unidad': 'unidad'
            }]
    
    def get_recipe_for_display(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene receta formateada para mostrar en la app de validación"""
        receta_data = self.get_recipe(product_name)
        if not receta_data:
            return None
        
        insumos = receta_data.get('receta', [])
        if not insumos:
            return None
        
        return {
            'producto': receta_data.get('producto'),
            'categoria': receta_data.get('categoria'),
            'insumos': [
                {
                    'nombre': insumo.get('insumo'),
                    'cantidad': insumo.get('cantidad'),
                    'unidad': insumo.get('unidad', 'ml'),
                    'opcional': insumo.get('opcional', False)
                }
                for insumo in insumos
            ]
        }


# Instancia global del servicio
_recipe_service_instance: Optional[RecipeService] = None

def get_recipe_service() -> RecipeService:
    """Obtiene la instancia global del servicio de recetas"""
    global _recipe_service_instance
    if _recipe_service_instance is None:
        _recipe_service_instance = RecipeService()
    return _recipe_service_instance





