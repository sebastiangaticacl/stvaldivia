#!/usr/bin/env python3
"""
Script para debuggear por qué un producto no pasa la validación del checkout
"""
from app import create_app
from app.models import db
from app.models.product_models import Product

def debug_checkout_producto(product_id=None):
    """Debug del producto para checkout"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔍 DEBUG CHECKOUT PRODUCTO")
        print("=" * 80)
        print()
        
        # Si no se especifica ID, buscar todos los productos ENTRADAS
        if product_id:
            productos = [Product.query.get(product_id)]
        else:
            productos = Product.query.filter(
                Product.category.isnot(None)
            ).all()
        
        productos = [p for p in productos if p]
        
        if not productos:
            print("❌ No se encontraron productos")
            return
        
        for producto in productos:
            print(f"📦 Producto: {producto.name} (ID: {producto.id})")
            print(f"   Categoría: '{producto.category}'")
            print(f"   Categoría (upper): '{producto.category.upper() if producto.category else None}'")
            print(f"   is_active: {producto.is_active}")
            print(f"   stock_quantity: {producto.stock_quantity}")
            print()
            
            # Validar paso a paso
            print("   🔍 VALIDACIONES:")
            
            # 1. Producto existe
            existe = producto is not None
            print(f"   1. Producto existe: {'✅' if existe else '❌'}")
            
            # 2. Categoría existe
            categoria_existe = producto.category is not None
            print(f"   2. Categoría existe: {'✅' if categoria_existe else '❌'}")
            
            # 3. Categoría es ENTRADAS (case-insensitive)
            if categoria_existe:
                categoria_ok = producto.category.upper() == 'ENTRADAS'
                print(f"   3. Categoría es 'ENTRADAS' (case-insensitive): {'✅' if categoria_ok else '❌'}")
                if not categoria_ok:
                    print(f"      - Categoría actual: '{producto.category}'")
                    print(f"      - Categoría upper: '{producto.category.upper()}'")
                    print(f"      - Esperado: 'ENTRADAS'")
            else:
                categoria_ok = False
                print(f"   3. Categoría es 'ENTRADAS': ❌ (no hay categoría)")
            
            # 4. Producto activo
            activo_ok = producto.is_active
            print(f"   4. Producto activo: {'✅' if activo_ok else '❌'}")
            
            # 5. Stock disponible
            stock_ok = producto.stock_quantity is None or producto.stock_quantity > 0
            print(f"   5. Stock disponible: {'✅' if stock_ok else '❌'}")
            if producto.stock_quantity is not None:
                print(f"      - Stock actual: {producto.stock_quantity}")
            
            # Resultado final
            print()
            print("   📊 RESULTADO:")
            categoria_ok_final = categoria_existe and producto.category.upper() == 'ENTRADAS'
            pasa_validacion = existe and categoria_ok_final and activo_ok
            
            if pasa_validacion:
                print("   ✅ El producto PASARÍA la validación del checkout")
            else:
                print("   ❌ El producto NO PASARÍA la validación del checkout")
                problemas = []
                if not existe:
                    problemas.append("producto no existe")
                if not categoria_ok_final:
                    problemas.append(f"categoría incorrecta: '{producto.category}'")
                if not activo_ok:
                    problemas.append("producto inactivo")
                print(f"      Problemas: {', '.join(problemas)}")
            
            print()
            print("=" * 80)
            print()

if __name__ == '__main__':
    import sys
    product_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    debug_checkout_producto(product_id)



