"""
Script para migrar recetas del sistema legacy (ProductRecipe) al sistema nuevo (Recipe)
Este script migra todas las recetas existentes y valida la migración.
"""
from app import create_app
from app.models import db
from app.models.product_models import Product
from app.models.recipe_models import ProductRecipe, LegacyIngredient
from app.models.inventory_stock_models import Recipe, RecipeIngredient, Ingredient
from flask import current_app
from decimal import Decimal

def migrar_ingrediente_legacy(legacy_ingredient: LegacyIngredient) -> Ingredient:
    """
    Migra un ingrediente legacy al sistema nuevo.
    Si ya existe, lo retorna. Si no, lo crea.
    """
    # Buscar si ya existe en el sistema nuevo
    existing = Ingredient.query.filter_by(name=legacy_ingredient.name).first()
    if existing:
        return existing
    
    # Crear nuevo ingrediente
    new_ingredient = Ingredient(
        name=legacy_ingredient.name,
        base_unit=legacy_ingredient.unit or 'ml',
        cost_per_unit=Decimal(str(legacy_ingredient.cost)) if legacy_ingredient.cost else Decimal('0.0'),
        is_active=True
    )
    
    # Si tiene volumen, usar como package_size
    if legacy_ingredient.volume_ml:
        new_ingredient.package_size = Decimal(str(legacy_ingredient.volume_ml))
        new_ingredient.package_unit = 'botella'
    
    db.session.add(new_ingredient)
    db.session.flush()
    
    current_app.logger.info(f"✅ Ingrediente migrado: {legacy_ingredient.name}")
    return new_ingredient

def migrar_receta_producto(product_id: int) -> tuple[bool, str]:
    """
    Migra la receta de un producto del sistema legacy al nuevo.
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        # Buscar producto
        product = Product.query.get(product_id)
        if not product:
            return False, f"Producto {product_id} no encontrado"
        
        # Buscar recetas legacy
        legacy_recipes = ProductRecipe.query.filter_by(product_id=product_id).all()
        if not legacy_recipes:
            return False, f"Producto {product.name} no tiene recetas legacy"
        
        # Verificar si ya tiene receta en sistema nuevo
        existing_recipe = Recipe.query.filter_by(product_id=product_id, is_active=True).first()
        if existing_recipe:
            return False, f"Producto {product.name} ya tiene receta en sistema nuevo (ID: {existing_recipe.id})"
        
        # Crear receta nueva
        new_recipe = Recipe(
            product_id=product_id,
            is_active=True,
            name=f"Receta migrada de {product.name}"
        )
        db.session.add(new_recipe)
        db.session.flush()
        
        # Migrar ingredientes
        ingredientes_migrados = 0
        for legacy_recipe_item in legacy_recipes:
            legacy_ingredient = legacy_recipe_item.ingredient
            if not legacy_ingredient:
                current_app.logger.warning(f"⚠️ Ingrediente legacy no encontrado para receta {legacy_recipe_item.id}")
                continue
            
            # Migrar ingrediente si es necesario
            new_ingredient = migrar_ingrediente_legacy(legacy_ingredient)
            
            # Crear RecipeIngredient
            recipe_ingredient = RecipeIngredient(
                recipe_id=new_recipe.id,
                ingredient_id=new_ingredient.id,
                quantity_per_portion=Decimal(str(legacy_recipe_item.quantity))
            )
            db.session.add(recipe_ingredient)
            ingredientes_migrados += 1
        
        # Asegurar que el producto esté marcado como kit
        if not product.is_kit:
            product.is_kit = True
            current_app.logger.info(f"✅ Producto {product.name} marcado como kit")
        
        db.session.commit()
        
        return True, f"Receta migrada: {ingredientes_migrados} ingredientes"
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Error al migrar receta de producto {product_id}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"

def migrar_todas_las_recetas():
    """
    Migra todas las recetas legacy al sistema nuevo.
    """
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("🔄 MIGRACIÓN DE RECETAS LEGACY A SISTEMA NUEVO")
        print("=" * 70)
        print()
        
        # Obtener todos los productos con recetas legacy
        productos_con_receta_legacy = db.session.query(Product).join(
            ProductRecipe, Product.id == ProductRecipe.product_id
        ).distinct().all()
        
        print(f"📊 Productos con recetas legacy encontrados: {len(productos_con_receta_legacy)}")
        print()
        
        migrados = 0
        ya_migrados = 0
        errores = 0
        errores_detalle = []
        
        for product in productos_con_receta_legacy:
            print(f"🔄 Migrando: {product.name} (ID: {product.id})...", end=" ")
            
            success, message = migrar_receta_producto(product.id)
            
            if success:
                print(f"✅ {message}")
                migrados += 1
            elif "ya tiene receta" in message.lower():
                print(f"⏭️  {message}")
                ya_migrados += 1
            else:
                print(f"❌ {message}")
                errores += 1
                errores_detalle.append(f"{product.name}: {message}")
        
        print()
        print("=" * 70)
        print("📊 RESUMEN DE MIGRACIÓN")
        print("=" * 70)
        print(f"✅ Migrados exitosamente: {migrados}")
        print(f"⏭️  Ya migrados (saltados): {ya_migrados}")
        print(f"❌ Errores: {errores}")
        print()
        
        if errores > 0:
            print("⚠️  ERRORES DETALLADOS:")
            for error in errores_detalle:
                print(f"   - {error}")
            print()
        
        # Validación post-migración
        print("🔍 VALIDACIÓN POST-MIGRACIÓN")
        print("-" * 70)
        
        # Verificar productos con recetas legacy que aún existen
        productos_sin_migrar = db.session.query(Product).join(
            ProductRecipe, Product.id == ProductRecipe.product_id
        ).outerjoin(
            Recipe, (Recipe.product_id == Product.id) & (Recipe.is_active == True)
        ).filter(Recipe.id == None).distinct().all()
        
        if productos_sin_migrar:
            print(f"⚠️  Productos con recetas legacy que NO fueron migrados: {len(productos_sin_migrar)}")
            for p in productos_sin_migrar:
                print(f"   - {p.name} (ID: {p.id})")
        else:
            print("✅ Todos los productos con recetas legacy fueron migrados o ya tenían receta nueva")
        
        print()
        print("=" * 70)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 70)

if __name__ == '__main__':
    migrar_todas_las_recetas()


