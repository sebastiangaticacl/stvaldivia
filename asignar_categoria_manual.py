"""
Script para asignar categorías manualmente a productos específicos
Útil cuando el script automático no puede inferir la categoría
"""
from app import create_app
from app.models.product_models import Product
from app.models import db

app = create_app()

# Mapeo manual de productos específicos a categorías
# Formato: 'nombre_producto': 'CATEGORIA'
MAPEO_MANUAL = {
    # Ejemplos - agregar aquí productos específicos que necesiten categoría manual
    # 'Producto Ejemplo': 'ENTRADAS',
    # 'Otro Producto': 'COCTELES',
}

def main():
    with app.app_context():
        print("="*60)
        print("🔧 ASIGNACIÓN MANUAL DE CATEGORÍAS")
        print("="*60)
        
        if not MAPEO_MANUAL:
            print("\n⚠️  No hay productos configurados para asignación manual")
            print("   Edita este script y agrega productos en MAPEO_MANUAL")
            return
        
        asignados = 0
        no_encontrados = []
        
        for nombre_producto, categoria in MAPEO_MANUAL.items():
            # Buscar producto por nombre (case-insensitive)
            producto = Product.query.filter(
                Product.name.ilike(f'%{nombre_producto}%'),
                Product.is_active == True
            ).first()
            
            if producto:
                producto.category = categoria
                asignados += 1
                print(f"   ✅ {producto.name} → {categoria}")
            else:
                no_encontrados.append(nombre_producto)
                print(f"   ⚠️  No se encontró: {nombre_producto}")
        
        if asignados > 0:
            try:
                db.session.commit()
                print(f"\n✅ {asignados} producto(s) actualizado(s)")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error al guardar: {e}")
        
        if no_encontrados:
            print(f"\n⚠️  {len(no_encontrados)} producto(s) no encontrado(s):")
            for nombre in no_encontrados:
                print(f"   • {nombre}")
        
        print("\n" + "="*60)

if __name__ == '__main__':
    main()

