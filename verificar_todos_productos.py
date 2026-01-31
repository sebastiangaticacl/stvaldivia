#!/usr/bin/env python3
"""
Script para verificar TODOS los productos y sus categorías
"""
from app import create_app
from app.models import db
from app.models.product_models import Product
from collections import Counter

def verificar_todos_productos():
    """Verifica todos los productos y sus categorías"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔍 VERIFICACIÓN DE TODOS LOS PRODUCTOS")
        print("=" * 80)
        print()
        
        # Obtener todos los productos
        todos_productos = Product.query.order_by(Product.name.asc()).all()
        
        if not todos_productos:
            print("❌ No hay productos en la base de datos")
            return
        
        print(f"📊 Total de productos: {len(todos_productos)}")
        print()
        
        # Agrupar por categoría
        categorias = {}
        productos_sin_categoria = []
        
        for producto in todos_productos:
            categoria = producto.category if producto.category else "Sin Categoría"
            if categoria not in categorias:
                categorias[categoria] = []
            categorias[categoria].append(producto)
        
        # Mostrar por categoría
        print("=" * 80)
        print("📋 PRODUCTOS POR CATEGORÍA")
        print("=" * 80)
        print()
        
        for categoria, productos in sorted(categorias.items()):
            print(f"📁 {categoria} ({len(productos)} producto(s))")
            print()
            
            for producto in productos:
                estado_icon = "✅" if producto.is_active else "❌"
                stock_display = "Ilimitado" if producto.stock_quantity is None else f"{producto.stock_quantity}"
                
                # Verificar si aparecería en ecommerce
                aparece_ecommerce = (
                    categoria.upper() == 'ENTRADAS' and
                    producto.is_active and
                    (producto.stock_quantity is None or producto.stock_quantity > 0)
                )
                ecommerce_icon = "🛒" if aparece_ecommerce else "  "
                
                print(f"   {ecommerce_icon} {estado_icon} {producto.name} (ID: {producto.id})")
                print(f"      - Precio: ${producto.price:,}")
                print(f"      - Stock: {stock_display}")
                print(f"      - Activo: {'Sí' if producto.is_active else 'No'}")
                if categoria.upper() == 'ENTRADAS':
                    if not producto.is_active:
                        print(f"      ⚠️  No aparece: Producto inactivo")
                    elif producto.stock_quantity is not None and producto.stock_quantity <= 0:
                        print(f"      ⚠️  No aparece: Stock = {producto.stock_quantity}")
                    elif aparece_ecommerce:
                        print(f"      ✅ Aparece en ecommerce")
                print()
        
        # Verificar categorías similares a ENTRADAS
        print("=" * 80)
        print("🔍 BÚSQUEDA DE CATEGORÍAS SIMILARES A 'ENTRADAS'")
        print("=" * 80)
        print()
        
        categorias_similares = []
        for categoria in categorias.keys():
            if categoria and 'ENTRADA' in categoria.upper():
                categorias_similares.append(categoria)
        
        if categorias_similares:
            print("⚠️  Se encontraron categorías similares a 'ENTRADAS':")
            for cat in categorias_similares:
                print(f"   - '{cat}' ({len(categorias[cat])} producto(s))")
                print(f"     💡 Considera cambiar a 'ENTRADAS' exactamente")
            print()
        else:
            print("✅ No se encontraron categorías similares")
            print()
        
        # Resumen
        print("=" * 80)
        print("📊 RESUMEN")
        print("=" * 80)
        print()
        print(f"Total de productos: {len(todos_productos)}")
        print(f"Total de categorías: {len(categorias)}")
        print()
        
        productos_entradas = [p for p in todos_productos if p.category and p.category.upper() == 'ENTRADAS']
        productos_entradas_visibles = [
            p for p in productos_entradas 
            if p.is_active and (p.stock_quantity is None or p.stock_quantity > 0)
        ]
        
        print(f"Productos con categoría 'ENTRADAS': {len(productos_entradas)}")
        print(f"Productos 'ENTRADAS' visibles en ecommerce: {len(productos_entradas_visibles)}")
        print()
        
        if len(productos_entradas) == 0:
            print("❌ PROBLEMA: No hay productos con categoría 'ENTRADAS'")
            print()
            print("💡 SOLUCIÓN:")
            print("   1. Ve a /admin/products")
            print("   2. Edita el producto que creaste")
            print("   3. Asegúrate de que la categoría sea exactamente 'ENTRADAS' (en mayúsculas)")
            print("   4. Marca 'is_active' como activo")
            print("   5. Configura stock_quantity > 0 o déjalo vacío para stock ilimitado")
        elif len(productos_entradas_visibles) == 0:
            print("❌ PROBLEMA: Hay productos 'ENTRADAS' pero ninguno es visible")
            print()
            print("💡 REVISAR:")
            for p in productos_entradas:
                problemas = []
                if not p.is_active:
                    problemas.append("inactivo")
                if p.stock_quantity is not None and p.stock_quantity <= 0:
                    problemas.append(f"stock={p.stock_quantity}")
                if problemas:
                    print(f"   - {p.name}: {', '.join(problemas)}")
        
        print()
        print("=" * 80)

if __name__ == '__main__':
    verificar_todos_productos()



