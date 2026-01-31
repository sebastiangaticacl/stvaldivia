"""
Script para verificar y mostrar categorías de productos en la base de datos
"""
from app import create_app
from app.models.product_models import Product
from app.models import db
from collections import Counter

app = create_app()

with app.app_context():
    print("="*60)
    print("🔍 VERIFICACIÓN DE CATEGORÍAS DE PRODUCTOS")
    print("="*60)
    
    # Obtener todos los productos
    productos = Product.query.all()
    total_productos = len(productos)
    productos_activos = Product.query.filter_by(is_active=True).all()
    total_activos = len(productos_activos)
    
    print(f"\n📦 Total de productos: {total_productos}")
    print(f"✅ Productos activos: {total_activos}")
    
    # Analizar categorías
    categorias_todas = []
    categorias_activos = []
    
    for producto in productos:
        if producto.category:
            categorias_todas.append(producto.category.strip())
    
    for producto in productos_activos:
        if producto.category:
            categorias_activos.append(producto.category.strip())
    
    # Contar categorías
    counter_todas = Counter(categorias_todas)
    counter_activos = Counter(categorias_activos)
    
    print(f"\n📊 CATEGORÍAS EN TODOS LOS PRODUCTOS:")
    if counter_todas:
        for categoria, count in counter_todas.most_common():
            print(f"   • {categoria}: {count} producto(s)")
    else:
        print("   ⚠️  No hay categorías asignadas")
    
    print(f"\n📊 CATEGORÍAS EN PRODUCTOS ACTIVOS:")
    if counter_activos:
        categorias_unicas = sorted(set(categorias_activos))
        print(f"   Total de categorías únicas: {len(categorias_unicas)}")
        for categoria in categorias_unicas:
            count = counter_activos[categoria]
            print(f"   • {categoria}: {count} producto(s)")
    else:
        print("   ⚠️  No hay categorías asignadas en productos activos")
    
    # Productos sin categoría
    productos_sin_categoria = [p for p in productos_activos if not p.category or not p.category.strip()]
    if productos_sin_categoria:
        print(f"\n⚠️  PRODUCTOS ACTIVOS SIN CATEGORÍA: {len(productos_sin_categoria)}")
        for producto in productos_sin_categoria[:10]:
            print(f"   • {producto.name} (ID: {producto.id})")
        if len(productos_sin_categoria) > 10:
            print(f"   ... y {len(productos_sin_categoria) - 10} más")
    
    # Resumen para TPV
    print(f"\n" + "="*60)
    print("📋 RESUMEN PARA TPV")
    print("="*60)
    if categorias_unicas:
        print(f"✅ Categorías disponibles para asignar a TPV: {len(categorias_unicas)}")
        print(f"   {', '.join(categorias_unicas)}")
    else:
        print("❌ No hay categorías disponibles para asignar a TPV")
        print("   Necesitas crear productos con categorías primero")
    
    print("\n" + "="*60)

