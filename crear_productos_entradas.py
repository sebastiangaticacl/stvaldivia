"""
Script para crear productos de ejemplo con categoría "ENTRADAS"
Estos productos serán visibles solo en la caja "Puerta"
"""
from app import create_app
from app.models import db
from app.models.product_models import Product
from datetime import datetime

# Productos de ejemplo para la categoría ENTRADAS
# Estos son productos típicos que se venden en la entrada del local
PRODUCTOS_ENTRADAS = [
    {'nombre': 'Entrada General', 'precio': 5000},
    {'nombre': 'Entrada VIP', 'precio': 10000},
    {'nombre': 'Entrada Pre-Venta', 'precio': 4000},
    {'nombre': 'Entrada Estudiante', 'precio': 3000},
    {'nombre': 'Entrada Mujer', 'precio': 4000},
    {'nombre': 'Entrada Hombre', 'precio': 5000},
    {'nombre': 'Entrada Pareja', 'precio': 8000},
    {'nombre': 'Entrada Grupal (5 personas)', 'precio': 20000},
    {'nombre': 'Entrada Grupal (10 personas)', 'precio': 35000},
    {'nombre': 'Mesa VIP', 'precio': 50000},
    {'nombre': 'Mesa Premium', 'precio': 80000},
    {'nombre': 'Reserva Mesa', 'precio': 10000},
]

def create_entradas_products():
    """Crea los productos de ENTRADAS en la base de datos"""
    app = create_app()
    with app.app_context():
        try:
            productos_creados = 0
            productos_existentes = 0
            productos_actualizados = 0
            errores = []
            
            print("\n" + "="*60)
            print("🎫 CREACIÓN DE PRODUCTOS DE ENTRADAS")
            print("="*60)
            print(f"\nTotal de productos a procesar: {len(PRODUCTOS_ENTRADAS)}")
            print("Categoría: ENTRADAS")
            print("Estos productos serán visibles solo en la caja 'Puerta'\n")
            
            for producto_data in PRODUCTOS_ENTRADAS:
                nombre = producto_data['nombre']
                precio = producto_data['precio']
                categoria = 'ENTRADAS'  # Categoría fija para todos
                
                try:
                    # Buscar si ya existe un producto con ese nombre
                    producto_existente = Product.query.filter_by(name=nombre).first()
                    
                    if producto_existente:
                        # Actualizar si es necesario
                        actualizado = False
                        if producto_existente.category != categoria:
                            producto_existente.category = categoria
                            actualizado = True
                        if producto_existente.price != precio:
                            producto_existente.price = precio
                            actualizado = True
                        if not producto_existente.is_active:
                            producto_existente.is_active = True
                            actualizado = True
                        
                        if actualizado:
                            producto_existente.updated_at = datetime.utcnow()
                            db.session.commit()
                            productos_actualizados += 1
                            print(f"  ✏️  Actualizado: {nombre} - ${precio:,} ({categoria})")
                        else:
                            productos_existentes += 1
                            print(f"  ⏭️  Ya existe: {nombre}")
                    else:
                        # Crear nuevo producto
                        nuevo_producto = Product(
                            name=nombre,
                            category=categoria,
                            price=precio,
                            cost_price=0,  # No tiene costo (es un servicio)
                            stock_quantity=0,  # No es stockeable
                            stock_minimum=0,
                            is_active=True,  # Disponible en POS
                            is_kit=False,  # No consume ingredientes
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        db.session.add(nuevo_producto)
                        db.session.commit()
                        productos_creados += 1
                        print(f"  ✅ Creado: {nombre} - ${precio:,} ({categoria})")
                        
                except Exception as e:
                    errores.append({'producto': nombre, 'error': str(e)})
                    db.session.rollback()
                    print(f"  ❌ Error al procesar '{nombre}': {e}")
            
            print("\n" + "="*60)
            print("📊 RESUMEN")
            print("="*60)
            print(f"  ✅ Productos creados: {productos_creados}")
            print(f"  ✏️  Productos actualizados: {productos_actualizados}")
            print(f"  ⏭️  Productos existentes (sin cambios): {productos_existentes}")
            if errores:
                print(f"  ❌ Errores: {len(errores)}")
                for error in errores:
                    print(f"     - {error['producto']}: {error['error']}")
            print("="*60)
            
            # Verificar productos con categoría ENTRADAS
            productos_entradas = Product.query.filter_by(category='ENTRADAS', is_active=True).all()
            print(f"\n🎫 Total de productos activos con categoría 'ENTRADAS': {len(productos_entradas)}")
            
            if productos_entradas:
                print("\n📋 Lista de productos ENTRADAS:")
                for p in productos_entradas:
                    print(f"   • {p.name} - ${p.price:,}")
            
            print("\n✅ Proceso completado!")
            print("\n💡 Próximos pasos:")
            print("   1. Ve a /admin/cajas/ y edita la caja 'Puerta'")
            print("   2. Asegúrate de que solo 'ENTRADAS' esté seleccionada en las categorías permitidas")
            print("   3. Abre la caja 'Puerta' en el POS y verifica que solo aparezcan estos productos")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    create_entradas_products()


