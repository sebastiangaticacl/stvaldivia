#!/usr/bin/env python3
"""
Script para verificar productos de categoría ENTRADAS y diagnosticar por qué no aparecen en el ecommerce
"""
import sys
from app import create_app
from app.models import db
from app.models.product_models import Product

def verificar_productos_ecommerce():
    """Verifica qué productos deberían aparecer en el ecommerce y por qué no"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔍 DIAGNÓSTICO DE PRODUCTOS PARA ECOMMERCE")
        print("=" * 80)
        print()
        
        # Obtener todos los productos de categoría ENTRADAS
        todos_productos = Product.query.filter(
            Product.category == 'ENTRADAS'
        ).order_by(Product.name.asc()).all()
        
        if not todos_productos:
            print("❌ No se encontraron productos con categoría 'ENTRADAS'")
            print()
            print("💡 SOLUCIÓN:")
            print("   1. Ve a /admin/products/create")
            print("   2. Crea un producto con categoría 'ENTRADAS'")
            print("   3. Asegúrate de que 'is_active' esté marcado")
            print("   4. Configura stock_quantity > 0 o déjalo NULL para stock ilimitado")
            return
        
        print(f"📊 Total de productos con categoría 'ENTRADAS': {len(todos_productos)}")
        print()
        
        # Categorizar productos
        productos_visibles = []
        productos_inactivos = []
        productos_sin_stock = []
        productos_ok = []
        
        for producto in todos_productos:
            # Verificar si está activo
            if not producto.is_active:
                productos_inactivos.append(producto)
                continue
            
            # Verificar stock
            stock_qty = producto.stock_quantity
            if stock_qty is not None and stock_qty <= 0:
                productos_sin_stock.append(producto)
                continue
            
            # Producto visible
            productos_visibles.append(producto)
            productos_ok.append(producto)
        
        # Mostrar productos que SÍ aparecerán en el ecommerce
        print("=" * 80)
        print("✅ PRODUCTOS QUE APARECEN EN EL ECOMMERCE")
        print("=" * 80)
        if productos_ok:
            print(f"   Total: {len(productos_ok)} producto(s)")
            print()
            for producto in productos_ok:
                stock_display = "Ilimitado" if producto.stock_quantity is None else f"{producto.stock_quantity} unidad(es)"
                print(f"   🎫 {producto.name}")
                print(f"      - ID: {producto.id}")
                print(f"      - Precio: ${producto.price:,}")
                print(f"      - Stock: {stock_display}")
                print(f"      - Activo: {'✅' if producto.is_active else '❌'}")
                print()
        else:
            print("   ❌ No hay productos que aparezcan en el ecommerce")
            print()
        
        # Mostrar productos que NO aparecerán y por qué
        print("=" * 80)
        print("⚠️  PRODUCTOS QUE NO APARECEN EN EL ECOMMERCE")
        print("=" * 80)
        
        # Productos inactivos
        if productos_inactivos:
            print(f"\n📝 Productos INACTIVOS ({len(productos_inactivos)}):")
            print("   Estos productos tienen is_active = False")
            print()
            for producto in productos_inactivos:
                print(f"   • {producto.name} (ID: {producto.id})")
                print(f"     Precio: ${producto.price:,}")
                print(f"     Stock: {producto.stock_quantity if producto.stock_quantity is not None else 'NULL'}")
                print(f"     💡 Activar el producto para que aparezca")
                print()
        
        # Productos sin stock
        if productos_sin_stock:
            print(f"\n📦 Productos SIN STOCK ({len(productos_sin_stock)}):")
            print("   Estos productos tienen stock_quantity <= 0")
            print()
            for producto in productos_sin_stock:
                print(f"   • {producto.name} (ID: {producto.id})")
                print(f"     Precio: ${producto.price:,}")
                print(f"     Stock actual: {producto.stock_quantity}")
                print(f"     💡 Aumentar stock_quantity o dejarlo NULL para stock ilimitado")
                print()
        
        # Resumen y recomendaciones
        print("=" * 80)
        print("📋 RESUMEN Y RECOMENDACIONES")
        print("=" * 80)
        print()
        
        if productos_ok:
            print(f"✅ {len(productos_ok)} producto(s) visible(s) en el ecommerce")
        else:
            print("❌ No hay productos visibles en el ecommerce")
            print()
            print("🔧 ACCIONES RECOMENDADAS:")
            print()
            
            if productos_inactivos:
                print(f"   1. Activar {len(productos_inactivos)} producto(s) inactivo(s):")
                for producto in productos_inactivos:
                    print(f"      - {producto.name} (ID: {producto.id})")
                    print(f"        Ejecutar: UPDATE products SET is_active=1 WHERE id={producto.id};")
                print()
            
            if productos_sin_stock:
                print(f"   2. Aumentar stock de {len(productos_sin_stock)} producto(s) sin stock:")
                for producto in productos_sin_stock:
                    print(f"      - {producto.name} (ID: {producto.id})")
                    print(f"        Opción A: UPDATE products SET stock_quantity=100 WHERE id={producto.id};")
                    print(f"        Opción B: UPDATE products SET stock_quantity=NULL WHERE id={producto.id}; (stock ilimitado)")
                print()
        
        # Mostrar todos los productos de ENTRADAS
        print("=" * 80)
        print("📋 TODOS LOS PRODUCTOS DE CATEGORÍA 'ENTRADAS'")
        print("=" * 80)
        for producto in todos_productos:
            estado_icon = "✅" if producto in productos_ok else "❌"
            stock_display = "Ilimitado" if producto.stock_quantity is None else f"{producto.stock_quantity}"
            activo_icon = "✅" if producto.is_active else "❌"
            
            print(f"   {estado_icon} {producto.name} (ID: {producto.id})")
            print(f"      - Precio: ${producto.price:,}")
            print(f"      - Stock: {stock_display}")
            print(f"      - Activo: {activo_icon}")
            print()
        
        print("=" * 80)
        print("✅ Diagnóstico completado")
        print("=" * 80)
        print()
        print("💡 Para verificar en el navegador:")
        print("   - Ve a /ecommerce/")
        print("   - Deberías ver los productos marcados con ✅")

if __name__ == '__main__':
    verificar_productos_ecommerce()



