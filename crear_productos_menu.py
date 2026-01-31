#!/usr/bin/env python3
"""
Script para crear productos del menú y eliminar productos existentes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db
from app.models.product_models import Product

def crear_productos_menu():
    """Crea todos los productos del menú según las categorías"""
    
    app = create_app()
    with app.app_context():
        try:
            # 1. ELIMINAR TODOS LOS PRODUCTOS EXISTENTES
            print("🗑️  Eliminando productos existentes...")
            productos_existentes = Product.query.all()
            for producto in productos_existentes:
                db.session.delete(producto)
            db.session.commit()
            print(f"✅ {len(productos_existentes)} productos eliminados")
            
            # 2. CREAR PRODUCTOS DEL MENÚ
            print("\n📦 Creando productos del menú...")
            
            productos = [
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
            
            productos_creados = []
            for prod_data in productos:
                producto = Product(
                    name=prod_data["name"],
                    category=prod_data["category"],
                    price=prod_data["price"],
                    is_active=True,
                    is_kit=False,  # Por defecto no son kits (no consumen ingredientes)
                    stock_quantity=0,
                    stock_minimum=0
                )
                db.session.add(producto)
                productos_creados.append(prod_data["name"])
            
            db.session.commit()
            
            print(f"✅ {len(productos_creados)} productos creados exitosamente")
            
            # Mostrar resumen por categoría
            print("\n📊 Resumen por categoría:")
            categorias = {}
            for prod_data in productos:
                cat = prod_data["category"]
                if cat not in categorias:
                    categorias[cat] = 0
                categorias[cat] += 1
            
            for categoria, count in sorted(categorias.items()):
                print(f"  {categoria}: {count} producto(s)")
            
            print("\n✅ Proceso completado exitosamente!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == "__main__":
    crear_productos_menu()
