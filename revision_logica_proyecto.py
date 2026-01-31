"""
Script de revisión lógica completa del proyecto BIMBA
Analiza arquitectura, modelos, flujos de negocio y consistencia lógica
"""
from app import create_app
from app.models import db
from app.models.pos_models import PosSale, PosSaleItem, PosRegister
from app.models.product_models import Product
from app.models.inventory_stock_models import (
    Ingredient, IngredientStock, Recipe, RecipeIngredient, InventoryMovement
)
from app.models.delivery_models import Delivery
from app.models.sale_delivery_models import SaleDeliveryStatus
from sqlalchemy import inspect, text
from collections import defaultdict
import json

def revisar_modelos_y_relaciones():
    """Revisa la estructura de modelos y sus relaciones"""
    print("\n" + "="*80)
    print("1️⃣ REVISIÓN DE MODELOS Y RELACIONES")
    print("="*80)
    
    issues = []
    warnings = []
    
    # Verificar modelos principales
    modelos_principales = {
        'PosSale': PosSale,
        'PosSaleItem': PosSaleItem,
        'Product': Product,
        'Ingredient': Ingredient,
        'Recipe': Recipe,
        'PosRegister': PosRegister
    }
    
    print("\n📦 Modelos principales:")
    for nombre, modelo in modelos_principales.items():
        inspector = inspect(modelo)
        print(f"   ✅ {nombre}: {len(inspector.columns)} columnas")
        
        # Verificar relaciones
        relaciones = inspector.relationships
        if relaciones:
            print(f"      Relaciones: {len(relaciones)}")
            for rel in relaciones:
                print(f"         • {rel.key} -> {rel.mapper.class_.__name__}")
    
    # Verificar campos críticos
    print("\n🔍 Campos críticos:")
    
    # PosSale - campos de inventario
    sale_columns = [c.name for c in inspect(PosSale).columns]
    if 'inventory_applied' not in sale_columns:
        issues.append("❌ PosSale no tiene campo 'inventory_applied' - riesgo de doble descuento")
    else:
        print("   ✅ PosSale.inventory_applied existe")
    
    if 'inventory_applied_at' not in sale_columns:
        warnings.append("⚠️  PosSale no tiene campo 'inventory_applied_at' - falta trazabilidad")
    else:
        print("   ✅ PosSale.inventory_applied_at existe")
    
    # PosRegister - categorías permitidas
    register_columns = [c.name for c in inspect(PosRegister).columns]
    if 'allowed_categories' not in register_columns:
        issues.append("❌ PosRegister no tiene campo 'allowed_categories' - no se puede filtrar productos")
    else:
        print("   ✅ PosRegister.allowed_categories existe")
    
    # Product - campos de receta
    product_columns = [c.name for c in inspect(Product).columns]
    if 'is_kit' not in product_columns:
        issues.append("❌ Product no tiene campo 'is_kit' - no se puede identificar productos con receta")
    else:
        print("   ✅ Product.is_kit existe")
    
    if 'category' not in product_columns:
        issues.append("❌ Product no tiene campo 'category' - no se puede filtrar por categoría")
    else:
        print("   ✅ Product.category existe")
    
    return issues, warnings

def revisar_flujos_negocio():
    """Revisa los flujos de negocio principales"""
    print("\n" + "="*80)
    print("2️⃣ REVISIÓN DE FLUJOS DE NEGOCIO")
    print("="*80)
    
    issues = []
    warnings = []
    
    # Flujo 1: Creación de venta -> Aplicación de inventario
    print("\n🛒 Flujo: Creación de Venta -> Aplicación de Inventario")
    
    # Verificar ventas sin inventario aplicado (solo ventas recientes)
    ventas_sin_inventario = PosSale.query.filter(
        PosSale.inventory_applied == False,
        PosSale.is_cancelled == False
    ).count()
    
    if ventas_sin_inventario > 0:
        print(f"   ⚠️  {ventas_sin_inventario} ventas sin inventario aplicado")
        warnings.append(f"⚠️  {ventas_sin_inventario} ventas activas sin inventario aplicado")
    else:
        print("   ✅ Todas las ventas activas tienen inventario aplicado")
    
    # Flujo 2: Productos con receta pero sin receta configurada
    print("\n🥤 Flujo: Productos con receta -> Configuración de ingredientes")
    
    productos_kit_sin_receta = db.session.query(Product).filter(
        Product.is_kit == True,
        Product.is_active == True
    ).all()
    
    productos_sin_receta_list = []
    for producto in productos_kit_sin_receta:
        receta = Recipe.query.filter_by(product_id=producto.id, is_active=True).first()
        if not receta:
            productos_sin_receta_list.append(producto.name)
    
    if productos_sin_receta_list:
        print(f"   ⚠️  {len(productos_sin_receta_list)} productos marcados como kit sin receta:")
        for nombre in productos_sin_receta_list[:5]:
            print(f"      • {nombre}")
        if len(productos_sin_receta_list) > 5:
            print(f"      ... y {len(productos_sin_receta_list) - 5} más")
        warnings.append(f"⚠️  {len(productos_sin_receta_list)} productos is_kit=True sin receta configurada")
    else:
        print("   ✅ Todos los productos kit tienen receta configurada")
    
    # Flujo 3: Cajas con restricciones de categorías
    print("\n🏪 Flujo: Cajas -> Filtrado de productos por categoría")
    
    cajas_con_restriccion = PosRegister.query.filter(
        PosRegister.allowed_categories.isnot(None),
        PosRegister.is_active == True
    ).all()
    
    if cajas_con_restriccion:
        print(f"   ✅ {len(cajas_con_restriccion)} caja(s) con restricciones de categorías:")
        for caja in cajas_con_restriccion:
            categorias = json.loads(caja.allowed_categories) if caja.allowed_categories else []
            print(f"      • {caja.name}: {categorias}")
    else:
        print("   ℹ️  No hay cajas con restricciones de categorías")
    
    # Flujo 4: Stock negativo
    print("\n📊 Flujo: Stock de ingredientes")
    
    stock_negativo = IngredientStock.query.filter(
        IngredientStock.quantity < 0
    ).all()
    
    if stock_negativo:
        print(f"   ⚠️  {len(stock_negativo)} ubicación(es) con stock negativo:")
        for stock in stock_negativo[:5]:
            print(f"      • {stock.ingredient.name} @ {stock.location}: {stock.quantity:.2f}")
        if len(stock_negativo) > 5:
            print(f"      ... y {len(stock_negativo) - 5} más")
        warnings.append(f"⚠️  {len(stock_negativo)} ubicaciones con stock negativo")
    else:
        print("   ✅ No hay stock negativo")
    
    return issues, warnings

def revisar_consistencia_datos():
    """Revisa la consistencia lógica de los datos"""
    print("\n" + "="*80)
    print("3️⃣ REVISIÓN DE CONSISTENCIA DE DATOS")
    print("="*80)
    
    issues = []
    warnings = []
    
    # Consistencia 1: Ventas con items pero sin total
    print("\n💰 Consistencia: Ventas y totales")
    
    ventas_inconsistentes = db.session.query(PosSale).filter(
        PosSale.total_amount <= 0,
        PosSale.is_cancelled == False,
        PosSale.is_courtesy == False
    ).count()
    
    if ventas_inconsistentes > 0:
        print(f"   ⚠️  {ventas_inconsistentes} ventas con total <= 0 (no canceladas ni cortesía)")
        warnings.append(f"⚠️  {ventas_inconsistentes} ventas con total <= 0")
    else:
        print("   ✅ Todas las ventas tienen total válido")
    
    # Consistencia 2: Items sin venta asociada
    items_huérfanos = db.session.query(PosSaleItem).outerjoin(
        PosSale, PosSaleItem.sale_id == PosSale.id
    ).filter(PosSale.id == None).count()
    
    if items_huérfanos > 0:
        issues.append(f"❌ {items_huérfanos} items de venta sin venta asociada (datos corruptos)")
        print(f"   ❌ {items_huérfanos} items huérfanos")
    else:
        print("   ✅ Todos los items tienen venta asociada")
    
    # Consistencia 3: Recetas sin ingredientes
    recetas_vacias = db.session.query(Recipe).outerjoin(
        RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
    ).filter(RecipeIngredient.id == None, Recipe.is_active == True).count()
    
    if recetas_vacias > 0:
        print(f"   ⚠️  {recetas_vacias} recetas activas sin ingredientes")
        warnings.append(f"⚠️  {recetas_vacias} recetas activas sin ingredientes")
    else:
        print("   ✅ Todas las recetas activas tienen ingredientes")
    
    # Consistencia 4: Ingredientes sin stock en ninguna ubicación
    ingredientes_sin_stock = db.session.query(Ingredient).outerjoin(
        IngredientStock, Ingredient.id == IngredientStock.ingredient_id
    ).filter(IngredientStock.id == None, Ingredient.is_active == True).count()
    
    if ingredientes_sin_stock > 0:
        print(f"   ⚠️  {ingredientes_sin_stock} ingredientes activos sin stock en ninguna ubicación")
        warnings.append(f"⚠️  {ingredientes_sin_stock} ingredientes activos sin stock")
    else:
        print("   ✅ Todos los ingredientes activos tienen stock")
    
    return issues, warnings

def revisar_validaciones_seguridad():
    """Revisa validaciones y seguridad"""
    print("\n" + "="*80)
    print("4️⃣ REVISIÓN DE VALIDACIONES Y SEGURIDAD")
    print("="*80)
    
    issues = []
    warnings = []
    
    # Validación 1: Ventas duplicadas (mismo idempotency_key)
    print("\n🔐 Validación: Idempotencia de ventas")
    
    try:
        ventas_duplicadas = db.session.query(
            PosSale.idempotency_key,
            db.func.count(PosSale.id).label('count')
        ).filter(
            PosSale.idempotency_key.isnot(None)
        ).group_by(PosSale.idempotency_key).having(
            db.func.count(PosSale.id) > 1
        ).all()
        
        if ventas_duplicadas:
            print(f"   ❌ {len(ventas_duplicadas)} idempotency_keys duplicados (violación de integridad)")
            issues.append(f"❌ {len(ventas_duplicadas)} ventas con idempotency_key duplicado")
        else:
            print("   ✅ No hay idempotency_keys duplicados")
    except Exception as e:
        warnings.append(f"⚠️  No se pudo verificar idempotencia: {e}")
    
    # Validación 2: Cajas activas sin código único
    print("\n🏪 Validación: Cajas registradoras")
    
    cajas_duplicadas = db.session.query(
        PosRegister.code,
        db.func.count(PosRegister.id).label('count')
    ).group_by(PosRegister.code).having(
        db.func.count(PosRegister.id) > 1
    ).all()
    
    if cajas_duplicadas:
        print(f"   ❌ {len(cajas_duplicadas)} códigos de caja duplicados")
        issues.append(f"❌ {len(cajas_duplicadas)} códigos de caja duplicados")
    else:
        print("   ✅ Todos los códigos de caja son únicos")
    
    # Validación 3: Productos con nombres duplicados
    print("\n📦 Validación: Productos")
    
    productos_duplicados = db.session.query(
        Product.name,
        db.func.count(Product.id).label('count')
    ).group_by(Product.name).having(
        db.func.count(Product.id) > 1
    ).all()
    
    if productos_duplicados:
        print(f"   ⚠️  {len(productos_duplicados)} nombres de producto duplicados:")
        for nombre, count in productos_duplicados[:5]:
            print(f"      • {nombre}: {count} productos")
        warnings.append(f"⚠️  {len(productos_duplicados)} nombres de producto duplicados")
    else:
        print("   ✅ Todos los nombres de producto son únicos")
    
    return issues, warnings

def revisar_estadisticas():
    """Muestra estadísticas generales del sistema"""
    print("\n" + "="*80)
    print("5️⃣ ESTADÍSTICAS GENERALES")
    print("="*80)
    
    total_ventas = PosSale.query.filter(PosSale.is_cancelled == False).count()
    ventas_canceladas = PosSale.query.filter(PosSale.is_cancelled == True).count()
    total_productos = Product.query.filter(Product.is_active == True).count()
    productos_kit = Product.query.filter(Product.is_kit == True, Product.is_active == True).count()
    total_ingredientes = Ingredient.query.filter(Ingredient.is_active == True).count()
    total_recetas = Recipe.query.filter(Recipe.is_active == True).count()
    total_cajas = PosRegister.query.filter(PosRegister.is_active == True).count()
    
    print(f"\n📊 Resumen:")
    print(f"   • Ventas activas: {total_ventas}")
    print(f"   • Ventas canceladas: {ventas_canceladas}")
    print(f"   • Productos activos: {total_productos}")
    print(f"   • Productos con receta (kit): {productos_kit}")
    print(f"   • Ingredientes activos: {total_ingredientes}")
    print(f"   • Recetas activas: {total_recetas}")
    print(f"   • Cajas activas: {total_cajas}")

def generar_reporte(issues, warnings):
    """Genera reporte final"""
    print("\n" + "="*80)
    print("📋 REPORTE FINAL")
    print("="*80)
    
    print(f"\n❌ Problemas críticos encontrados: {len(issues)}")
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("   ✅ No se encontraron problemas críticos")
    
    print(f"\n⚠️  Advertencias encontradas: {len(warnings)}")
    if warnings:
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    else:
        print("   ✅ No se encontraron advertencias")
    
    print("\n" + "="*80)
    print("✅ REVISIÓN COMPLETADA")
    print("="*80)

def main():
    """Función principal"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("🔍 REVISIÓN LÓGICA COMPLETA DEL PROYECTO BIMBA")
        print("="*80)
        
        all_issues = []
        all_warnings = []
        
        # Ejecutar revisiones
        issues, warnings = revisar_modelos_y_relaciones()
        all_issues.extend(issues)
        all_warnings.extend(warnings)
        
        issues, warnings = revisar_flujos_negocio()
        all_issues.extend(issues)
        all_warnings.extend(warnings)
        
        issues, warnings = revisar_consistencia_datos()
        all_issues.extend(issues)
        all_warnings.extend(warnings)
        
        issues, warnings = revisar_validaciones_seguridad()
        all_issues.extend(issues)
        all_warnings.extend(warnings)
        
        revisar_estadisticas()
        
        generar_reporte(all_issues, all_warnings)

if __name__ == '__main__':
    main()


