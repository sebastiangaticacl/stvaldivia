"""
Script para agregar categorías de ejemplo a productos existentes
Útil cuando no hay categorías asignadas
"""
from app import create_app
from app.models.product_models import Product
from app.models import db

app = create_app()

# Mapeo de palabras clave a categorías (ordenado por especificidad)
CATEGORIAS_MAP = {
    # Categorías específicas primero (más específicas primero)
    'ENTRADAS': ['entrada', 'ticket', 'acceso', 'admisión', 'ingreso', 'pase', 'entrada general', 'entrada vip'],
    'COCTELES': ['coctel', 'cocktail', 'mojito', 'margarita', 'daiquiri', 'piña colada', 'cuba libre', 'caipirinha', 'pisco sour', 'moscow mule', 'negroni', 'old fashioned', 'martini', 'cosmopolitan'],
    'CERVEZAS': ['cerveza', 'beer', 'lager', 'ipa', 'stout', 'pilsen', 'ale', 'porter', 'weiss', 'heineken', 'corona', 'stella', 'budweiser', 'cristal', 'escudo', 'kuntsmann'],
    'VINOS': ['vino', 'wine', 'tinto', 'blanco', 'rosado', 'champagne', 'espumante', 'cava', 'prosecco', 'sauvignon', 'cabernet', 'merlot', 'pinot', 'chardonnay', 'riesling'],
    'WHISKY': ['whisky', 'whiskey', 'scotch', 'bourbon', 'jack daniels', 'johnnie walker', 'chivas', 'jameson', 'jim beam'],
    'RON': ['ron', 'rum', 'bacardi', 'captain morgan', 'havana club'],
    'VODKA': ['vodka', 'absolut', 'smirnoff', 'grey goose', 'ketel one'],
    'GIN': ['gin', 'bombay', 'tanqueray', 'hendricks', 'beefeater'],
    'TEQUILA': ['tequila', 'patron', 'jose cuervo', 'don julio', 'herradura'],
    'PISCO': ['pisco', 'pisco sour', 'pisco peruano', 'pisco chileno'],
    'BEBIDAS': ['bebida', 'refresco', 'agua', 'jugo', 'gaseosa', 'coca cola', 'pepsi', 'sprite', 'fanta', 'seven up', 'agua mineral', 'agua con gas', 'agua sin gas'],
    'ENERGIZANTES': ['energizante', 'red bull', 'monster', 'rockstar', 'burn'],
    'COMIDA': ['comida', 'plato', 'menu', 'food', 'almuerzo', 'cena', 'desayuno', 'sandwich', 'hamburguesa', 'pizza', 'pasta', 'ensalada'],
    'SNACKS': ['snack', 'papas', 'chips', 'maní', 'nueces', 'almendras', 'palomitas', 'popcorn', 'doritos', 'lays'],
    'POSTRES': ['postre', 'dessert', 'torta', 'tarta', 'helado', 'ice cream', 'flan', 'mousse', 'cheesecake', 'brownie'],
    'CAFÉ': ['café', 'coffee', 'espresso', 'cappuccino', 'latte', 'americano', 'mocha', 'macchiato'],
    'TÉ': ['té', 'tea', 'infusión', 'herbal tea', 'green tea', 'black tea'],
    'JUGOS': ['jugo', 'juice', 'naranja', 'manzana', 'piña', 'frutilla', 'mango', 'maracuyá'],
    'SMOOTHIES': ['smoothie', 'batido', 'licuado', 'frappé'],
}

def asignar_categoria_por_nombre(producto):
    """
    Asigna categoría basándose en el nombre del producto.
    Usa coincidencias exactas primero, luego parciales.
    """
    nombre_lower = producto.name.lower().strip()
    
    # Primero buscar coincidencias exactas (más específicas)
    for categoria, keywords in CATEGORIAS_MAP.items():
        for keyword in keywords:
            # Coincidencia exacta (palabra completa)
            if f' {keyword} ' in f' {nombre_lower} ' or nombre_lower.startswith(keyword + ' ') or nombre_lower.endswith(' ' + keyword):
                return categoria
    
    # Luego buscar coincidencias parciales
    for categoria, keywords in CATEGORIAS_MAP.items():
        for keyword in keywords:
            if keyword in nombre_lower:
                return categoria
    
    return None

def main():
    with app.app_context():
        print("="*60)
        print("🔧 ASIGNACIÓN DE CATEGORÍAS A PRODUCTOS")
        print("="*60)
        
        # Obtener productos activos sin categoría
        productos_sin_categoria = Product.query.filter(
            Product.is_active == True,
            db.or_(
                Product.category.is_(None),
                Product.category == '',
                Product.category == ' '
            )
        ).all()
        
        print(f"\n📦 Productos activos sin categoría: {len(productos_sin_categoria)}")
        
        if not productos_sin_categoria:
            print("✅ Todos los productos ya tienen categoría asignada")
            return
        
        # Asignar categorías
        asignados = 0
        no_asignados = []
        categorias_asignadas = {}
        
        print("\n🔄 Asignando categorías...")
        for producto in productos_sin_categoria:
            categoria = asignar_categoria_por_nombre(producto)
            if categoria:
                producto.category = categoria
                asignados += 1
                categorias_asignadas[categoria] = categorias_asignadas.get(categoria, 0) + 1
                print(f"   ✅ {producto.name} → {categoria}")
            else:
                no_asignados.append(producto)
                print(f"   ⚠️  {producto.name} → Sin categoría (no se pudo inferir)")
        
        # Mostrar resumen de asignaciones por categoría
        if categorias_asignadas:
            print(f"\n📊 Resumen de asignaciones por categoría:")
            for categoria, count in sorted(categorias_asignadas.items()):
                print(f"   • {categoria}: {count} producto(s)")
        
        # Guardar cambios
        if asignados > 0:
            try:
                db.session.commit()
                print(f"\n✅ {asignados} producto(s) actualizado(s) con categorías")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error al guardar: {e}")
                return
        
        # Mostrar productos que no se pudieron asignar
        if no_asignados:
            print(f"\n⚠️  {len(no_asignados)} producto(s) sin categoría asignada:")
            print("   Puedes asignarles categorías manualmente desde el panel de administración")
            for producto in no_asignados[:10]:
                print(f"   • {producto.name} (ID: {producto.id})")
            if len(no_asignados) > 10:
                print(f"   ... y {len(no_asignados) - 10} más")
        
        # Verificar resultado
        print("\n" + "="*60)
        print("📊 VERIFICACIÓN FINAL")
        print("="*60)
        
        categorias = db.session.query(Product.category).distinct().filter(
            Product.category.isnot(None),
            Product.category != '',
            Product.is_active == True
        ).order_by(Product.category).all()
        
        categorias_unicas = [cat[0].strip() for cat in categorias if cat[0] and cat[0].strip()]
        categorias_unicas = sorted(set(categorias_unicas))
        
        print(f"✅ Categorías disponibles ahora: {len(categorias_unicas)}")
        for cat in categorias_unicas:
            count = Product.query.filter_by(category=cat, is_active=True).count()
            print(f"   • {cat}: {count} producto(s)")
        
        print("\n" + "="*60)
        print("✅ PROCESO COMPLETADO")
        print("="*60)

if __name__ == '__main__':
    main()

