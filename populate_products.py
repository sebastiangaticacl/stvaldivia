#!/usr/bin/env python3
"""
Script para poblar productos finales del menú en la base de datos.
Productos disponibles en POS, sin recetas (is_kit=False).
"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from app.models.product_models import Product

# Datos del menú - Productos finales
PRODUCTOS_MENU = [
    # CERVEZA
    {"name": "Royal Guard 470cc", "category": "CERVEZA", "price": 3500},
    {"name": "Heineken 470cc", "category": "CERVEZA", "price": 3500},
    {"name": "Corona", "category": "CERVEZA", "price": 3000},
    
    # PISCO
    {"name": "El Gobernador 40°", "category": "PISCO", "price": 6500},
    {"name": "Mistral Apple", "category": "PISCO", "price": 6500},
    {"name": "Alto del Carmen 35°", "category": "PISCO", "price": 5000},
    {"name": "Mistral 35°", "category": "PISCO", "price": 5000},
    {"name": "Capel", "category": "PISCO", "price": 4000},
    
    # RON
    {"name": "Havana Reserva", "category": "RON", "price": 6000},
    {"name": "Barceló", "category": "RON", "price": 6000},
    {"name": "Havana Especial", "category": "RON", "price": 5500},
    
    # VODKA
    {"name": "Absolut Blue", "category": "VODKA", "price": 6000},
    {"name": "Stolichnaya", "category": "VODKA", "price": 5500},
    {"name": "Eristoff", "category": "VODKA", "price": 4000},
    
    # GIN
    {"name": "Tanqueray", "category": "GIN", "price": 7500},
    {"name": "Beefeater", "category": "GIN", "price": 6500},
    {"name": "Bombay", "category": "GIN", "price": 6500},
    {"name": "Tropical Gin", "category": "GIN", "price": 7000},
    
    # WHISKY
    {"name": "Jack Daniel's No. 7", "category": "WHISKY", "price": 7500},
    {"name": "J. Walker Red Label", "category": "WHISKY", "price": 6500},
    {"name": "Fireball", "category": "WHISKY", "price": 6500},
    
    # SHOTS
    {"name": "Tequila Olmeca", "category": "SHOTS", "price": 3500},
    {"name": "Tequila corriente", "category": "SHOTS", "price": 2500},
    {"name": "Araucanito", "category": "SHOTS", "price": 2000},
    {"name": "Fireballito", "category": "SHOTS", "price": 3000},
    
    # OTROS
    {"name": "Araucano", "category": "OTROS", "price": 4000},
    {"name": "Fernet", "category": "OTROS", "price": 5000},
    {"name": "Jagermeister", "category": "OTROS", "price": 5500},
    
    # COCTELERÍA
    {"name": "Campari Naranja", "category": "COCTELERÍA", "price": 7000},
    {"name": "Negroni", "category": "COCTELERÍA", "price": 6500},
    {"name": "Jhon Collins", "category": "COCTELERÍA", "price": 6000},
    {"name": "Tom Collins", "category": "COCTELERÍA", "price": 6000},
    {"name": "Daiquiri", "category": "COCTELERÍA", "price": 5500},
    {"name": "Mojito", "category": "COCTELERÍA", "price": 5000},
    {"name": "Sangria", "category": "COCTELERÍA", "price": 3000},
    
    # SIN ALCOHOL
    {"name": "Agua Mineral", "category": "SIN ALCOHOL", "price": 2000},
    {"name": "Lata bebida 350cc", "category": "SIN ALCOHOL", "price": 2500},
    {"name": "Mojito Sin Alcohol", "category": "SIN ALCOHOL", "price": 3500},
]


def populate_products():
    """Pobla la base de datos con productos del menú"""
    app = create_app()
    
    with app.app_context():
        creados = 0
        actualizados = 0
        errores = []
        
        print("=" * 60)
        print("🍺 Poblando productos del menú en la base de datos")
        print("=" * 60)
        print()
        
        for producto_data in PRODUCTOS_MENU:
            try:
                name = producto_data["name"]
                category = producto_data["category"]
                price = producto_data["price"]
                
                # Buscar si ya existe
                existing = Product.query.filter_by(name=name).first()
                
                if existing:
                    # Actualizar si el precio cambió
                    if existing.price != price:
                        existing.price = price
                        existing.category = category
                        db.session.commit()
                        actualizados += 1
                        print(f"  ✏️  Actualizado: {name} - ${price:,}")
                    else:
                        print(f"  ⏭️  Ya existe: {name}")
                else:
                    # Crear nuevo producto
                    product = Product(
                        name=name,
                        category=category,
                        price=price,
                        cost_price=0,  # Se configurará después
                        stock_quantity=0,  # Stock inicial 0
                        stock_minimum=0,
                        is_active=True,  # Disponible en POS
                        is_kit=False  # Producto final, no tiene receta aún
                    )
                    db.session.add(product)
                    db.session.commit()
                    creados += 1
                    print(f"  ✅ Creado: {name} - ${price:,} ({category})")
                    
            except Exception as e:
                errores.append(f"{name}: {str(e)}")
                db.session.rollback()
                print(f"  ❌ Error con {name}: {str(e)}")
        
        print()
        print("=" * 60)
        print("📊 Resumen:")
        print(f"  ✅ Productos creados: {creados}")
        print(f"  ✏️  Productos actualizados: {actualizados}")
        if errores:
            print(f"  ❌ Errores: {len(errores)}")
            for error in errores:
                print(f"     - {error}")
        print("=" * 60)
        
        # Mostrar estadísticas por categoría
        print()
        print("📦 Productos por categoría:")
        categorias = db.session.query(Product.category, db.func.count(Product.id)).group_by(Product.category).all()
        for cat, count in categorias:
            if cat:
                print(f"  {cat}: {count} productos")
        
        return creados, actualizados, errores


if __name__ == '__main__':
    try:
        creados, actualizados, errores = populate_products()
        sys.exit(0 if not errores else 1)
    except Exception as e:
        print(f"❌ Error fatal: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)











