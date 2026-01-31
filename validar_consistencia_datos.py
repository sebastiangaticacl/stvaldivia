"""
Script de validación de consistencia de datos del sistema.
Verifica:
1. Productos con is_kit=True pero sin receta
2. Stock negativo
3. Ventas antiguas con inventory_applied=False
4. Recetas sin ingredientes
"""
from app import create_app
from app.models import db
from app.models.product_models import Product
from app.models.inventory_stock_models import Recipe, RecipeIngredient, IngredientStock
from app.models.recipe_models import ProductRecipe
from app.models.pos_models import PosSale
from datetime import datetime, timedelta
from flask import current_app

def validar_productos_sin_receta():
    """
    Valida productos marcados como kit pero sin receta configurada.
    """
    print("=" * 70)
    print("🔍 VALIDACIÓN: Productos con is_kit=True pero sin receta")
    print("=" * 70)
    
    # Buscar productos is_kit=True sin receta en sistema nuevo
    productos_sin_receta = db.session.query(Product).filter(
        Product.is_kit == True,
        Product.is_active == True
    ).outerjoin(
        Recipe, (Recipe.product_id == Product.id) & (Recipe.is_active == True)
    ).outerjoin(
        ProductRecipe, ProductRecipe.product_id == Product.id
    ).filter(
        Recipe.id == None,
        ProductRecipe.id == None
    ).all()
    
    if productos_sin_receta:
        print(f"⚠️  ENCONTRADOS: {len(productos_sin_receta)} productos")
        print()
        for p in productos_sin_receta:
            print(f"   ❌ {p.name} (ID: {p.id}, Categoría: {p.category})")
        print()
        return productos_sin_receta
    else:
        print("✅ Todos los productos is_kit=True tienen receta configurada")
        print()
        return []

def validar_stock_negativo():
    """
    Valida ingredientes con stock negativo.
    """
    print("=" * 70)
    print("🔍 VALIDACIÓN: Stock negativo de ingredientes")
    print("=" * 70)
    
    stock_negativo = IngredientStock.query.filter(
        IngredientStock.quantity < 0
    ).order_by(IngredientStock.quantity.asc()).all()
    
    if stock_negativo:
        print(f"⚠️  ENCONTRADOS: {len(stock_negativo)} ubicaciones con stock negativo")
        print()
        for stock in stock_negativo:
            ingredient_name = stock.ingredient.name if stock.ingredient else "?"
            print(f"   ❌ {ingredient_name} @ {stock.location}: {float(stock.quantity):.3f} {stock.ingredient.base_unit if stock.ingredient else '?'}")
        print()
        return stock_negativo
    else:
        print("✅ No hay stock negativo")
        print()
        return []

def validar_ventas_sin_inventario():
    """
    Valida ventas antiguas con inventory_applied=False que deberían tenerlo en True.
    """
    print("=" * 70)
    print("🔍 VALIDACIÓN: Ventas antiguas con inventory_applied=False")
    print("=" * 70)
    
    # Verificar si la columna existe
    try:
        # Intentar acceder a la columna para verificar si existe
        has_column = hasattr(PosSale, 'inventory_applied')
        if not has_column:
            print("⏭️  Columna inventory_applied no existe en la base de datos")
            print("   Ejecuta la migración: migracion_inventory_applied.sql")
            print()
            return []
    except Exception as e:
        print(f"⏭️  No se puede verificar columna inventory_applied: {e}")
        print("   Ejecuta la migración: migracion_inventory_applied.sql")
        print()
        return []
    
    # Ventas de hace más de 7 días sin inventario aplicado
    fecha_limite = datetime.utcnow() - timedelta(days=7)
    
    try:
        ventas_sin_inventario = PosSale.query.filter(
            PosSale.inventory_applied == False,
            PosSale.created_at < fecha_limite,
            PosSale.is_cancelled == False
        ).order_by(PosSale.created_at.desc()).limit(50).all()
    except Exception as e:
        # Si falla, probablemente la columna no existe
        db.session.rollback()  # Limpiar transacción fallida
        print(f"⏭️  Error al consultar ventas: {e}")
        print("   Ejecuta la migración: migracion_inventory_applied.sql")
        print()
        return []
    
    if ventas_sin_inventario:
        print(f"⚠️  ENCONTRADAS: {len(ventas_sin_inventario)} ventas (mostrando últimas 50)")
        print()
        for sale in ventas_sin_inventario[:10]:  # Mostrar solo las primeras 10
            print(f"   ⚠️  Venta #{sale.id} - {sale.created_at.strftime('%Y-%m-%d %H:%M')} - Total: ${sale.total_amount}")
        if len(ventas_sin_inventario) > 10:
            print(f"   ... y {len(ventas_sin_inventario) - 10} más")
        print()
        return ventas_sin_inventario
    else:
        print("✅ No hay ventas antiguas sin inventario aplicado")
        print()
        return []

def validar_recetas_sin_ingredientes():
    """
    Valida recetas que no tienen ingredientes configurados.
    """
    print("=" * 70)
    print("🔍 VALIDACIÓN: Recetas sin ingredientes")
    print("=" * 70)
    
    try:
        recetas_sin_ingredientes = db.session.query(Recipe).filter(
            Recipe.is_active == True
        ).outerjoin(
            RecipeIngredient, RecipeIngredient.recipe_id == Recipe.id
        ).filter(
            RecipeIngredient.id == None
        ).all()
    except Exception as e:
        db.session.rollback()  # Limpiar transacción fallida
        print(f"⏭️  Error al consultar recetas: {e}")
        print()
        return []
    
    if recetas_sin_ingredientes:
        print(f"⚠️  ENCONTRADAS: {len(recetas_sin_ingredientes)} recetas")
        print()
        for recipe in recetas_sin_ingredientes:
            product_name = recipe.product.name if recipe.product else "?"
            print(f"   ❌ Receta ID {recipe.id} - Producto: {product_name}")
        print()
        return recetas_sin_ingredientes
    else:
        print("✅ Todas las recetas tienen ingredientes configurados")
        print()
        return []

def validar_recetas_duplicadas():
    """
    Valida productos que tienen receta en ambos sistemas (nuevo y legacy).
    """
    print("=" * 70)
    print("🔍 VALIDACIÓN: Recetas duplicadas (nuevo + legacy)")
    print("=" * 70)
    
    try:
        productos_duplicados = db.session.query(Product).join(
            Recipe, (Recipe.product_id == Product.id) & (Recipe.is_active == True)
        ).join(
            ProductRecipe, ProductRecipe.product_id == Product.id
        ).distinct().all()
    except Exception as e:
        db.session.rollback()  # Limpiar transacción fallida
        print(f"⏭️  Error al consultar recetas duplicadas: {e}")
        print()
        return []
    
    if productos_duplicados:
        print(f"⚠️  ENCONTRADOS: {len(productos_duplicados)} productos con recetas en ambos sistemas")
        print()
        for p in productos_duplicados:
            print(f"   ⚠️  {p.name} (ID: {p.id})")
            print(f"      → Tiene receta nueva Y legacy (debe migrarse)")
        print()
        return productos_duplicados
    else:
        print("✅ No hay productos con recetas duplicadas")
        print()
        return []

def generar_reporte_completo():
    """
    Genera un reporte completo de validación.
    """
    app = create_app()
    
    with app.app_context():
        print()
        print("=" * 70)
        print("📋 REPORTE DE VALIDACIÓN DE CONSISTENCIA DE DATOS")
        print("=" * 70)
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        resultados = {
            'productos_sin_receta': validar_productos_sin_receta(),
            'stock_negativo': validar_stock_negativo(),
            'ventas_sin_inventario': validar_ventas_sin_inventario(),
            'recetas_sin_ingredientes': validar_recetas_sin_ingredientes(),
            'recetas_duplicadas': validar_recetas_duplicadas()
        }
        
        print()
        print("=" * 70)
        print("📊 RESUMEN")
        print("=" * 70)
        
        total_problemas = sum(len(v) for v in resultados.values())
        
        print(f"✅ Productos sin receta: {len(resultados['productos_sin_receta'])}")
        print(f"✅ Stock negativo: {len(resultados['stock_negativo'])}")
        print(f"✅ Ventas sin inventario: {len(resultados['ventas_sin_inventario'])}")
        print(f"✅ Recetas sin ingredientes: {len(resultados['recetas_sin_ingredientes'])}")
        print(f"✅ Recetas duplicadas: {len(resultados['recetas_duplicadas'])}")
        print()
        print(f"📊 TOTAL DE PROBLEMAS ENCONTRADOS: {total_problemas}")
        print()
        
        if total_problemas == 0:
            print("🎉 ¡Excelente! No se encontraron problemas de consistencia.")
        else:
            print("⚠️  Se encontraron problemas que requieren atención.")
            print("   Revisa los detalles arriba y corrige según sea necesario.")
        
        print()
        print("=" * 70)
        
        return resultados

if __name__ == '__main__':
    generar_reporte_completo()

