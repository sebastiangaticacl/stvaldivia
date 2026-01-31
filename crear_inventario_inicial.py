#!/usr/bin/env python3
"""
Script para crear datos iniciales de inventario en producción
"""
import sys
import os

# Configuración de conexión
PROD_DB_URL = "postgresql://bimba_user:<PASSWORD>@<HOST>:5432/bimba"

def crear_datos_iniciales():
    """Crea datos iniciales de inventario"""
    from sqlalchemy import create_engine, text
    
    engine = create_engine(PROD_DB_URL)
    
    print("=" * 60)
    print("🔄 CREANDO DATOS INICIALES DE INVENTARIO")
    print("=" * 60)
    print()
    
    with engine.connect() as conn:
        # Verificar qué existe
        result = conn.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM ingredient_categories) as categories,
                (SELECT COUNT(*) FROM ingredients) as ingredients,
                (SELECT COUNT(*) FROM products) as products,
                (SELECT COUNT(*) FROM recipes) as recipes
        """))
        row = result.fetchone()
        print(f"📊 Estado actual:")
        print(f"   - Categorías: {row[0]}")
        print(f"   - Ingredientes: {row[1]}")
        print(f"   - Productos: {row[2]}")
        print(f"   - Recetas: {row[3]}")
        print()
        
        if row[0] > 0 or row[1] > 0:
            print("⚠️  Ya existen datos de inventario")
            response = input("¿Desea continuar y agregar más datos? (s/N): ").strip().lower()
            if response != 's':
                print("❌ Cancelado")
                return
        
        # Crear categorías básicas
        print("📦 Creando categorías de ingredientes...")
        conn.execute(text("""
            INSERT INTO ingredient_categories (name, description, created_at, updated_at)
            VALUES 
                ('Bebidas', 'Bebidas alcohólicas y no alcohólicas', NOW(), NOW()),
                ('Frutas', 'Frutas frescas', NOW(), NOW()),
                ('Verduras', 'Verduras frescas', NOW(), NOW()),
                ('Lácteos', 'Productos lácteos', NOW(), NOW()),
                ('Carnes', 'Carnes y proteínas', NOW(), NOW()),
                ('Granos', 'Granos y cereales', NOW(), NOW()),
                ('Condimentos', 'Condimentos y especias', NOW(), NOW()),
                ('Otros', 'Otros ingredientes', NOW(), NOW())
            ON CONFLICT DO NOTHING;
        """))
        conn.commit()
        print("   ✅ Categorías creadas")
        
        # Crear ingredientes básicos
        print("🥤 Creando ingredientes básicos...")
        conn.execute(text("""
            INSERT INTO ingredients (name, base_unit, category_id, created_at, updated_at)
            SELECT 
                name,
                base_unit,
                (SELECT id FROM ingredient_categories WHERE name = category_name LIMIT 1),
                NOW(),
                NOW()
            FROM (VALUES
                ('Vodka', 'ml', 'Bebidas'),
                ('Ron', 'ml', 'Bebidas'),
                ('Whisky', 'ml', 'Bebidas'),
                ('Gin', 'ml', 'Bebidas'),
                ('Tequila', 'ml', 'Bebidas'),
                ('Cerveza', 'ml', 'Bebidas'),
                ('Vino', 'ml', 'Bebidas'),
                ('Jugo de limón', 'ml', 'Bebidas'),
                ('Jugo de naranja', 'ml', 'Bebidas'),
                ('Soda', 'ml', 'Bebidas'),
                ('Agua tónica', 'ml', 'Bebidas'),
                ('Hielo', 'unidades', 'Otros'),
                ('Azúcar', 'g', 'Condimentos'),
                ('Sal', 'g', 'Condimentos'),
                ('Pimienta', 'g', 'Condimentos')
            ) AS v(name, base_unit, category_name)
            WHERE NOT EXISTS (SELECT 1 FROM ingredients WHERE ingredients.name = v.name)
        """))
        conn.commit()
        print("   ✅ Ingredientes básicos creados")
        
        # Crear productos básicos
        print("🍹 Creando productos básicos...")
        conn.execute(text("""
            INSERT INTO products (name, description, price, category, created_at, updated_at)
            VALUES 
                ('Cerveza', 'Cerveza artesanal', 3000, 'Bebidas', NOW(), NOW()),
                ('Vino', 'Vino tinto/blanco', 5000, 'Bebidas', NOW(), NOW()),
                ('Cuba Libre', 'Ron con cola', 4000, 'Cocteles', NOW(), NOW()),
                ('Mojito', 'Ron, menta, limón', 4500, 'Cocteles', NOW(), NOW()),
                ('Piña Colada', 'Ron, piña, coco', 5000, 'Cocteles', NOW(), NOW()),
                ('Margarita', 'Tequila, limón, sal', 5000, 'Cocteles', NOW(), NOW())
            ON CONFLICT DO NOTHING;
        """))
        conn.commit()
        print("   ✅ Productos básicos creados")
        
        print()
        print("=" * 60)
        print("✅ DATOS INICIALES DE INVENTARIO CREADOS")
        print("=" * 60)
        
        # Mostrar resumen
        result = conn.execute(text("""
            SELECT 
                (SELECT COUNT(*) FROM ingredient_categories) as categories,
                (SELECT COUNT(*) FROM ingredients) as ingredients,
                (SELECT COUNT(*) FROM products) as products
        """))
        row = result.fetchone()
        print()
        print(f"📊 Estado final:")
        print(f"   - Categorías: {row[0]}")
        print(f"   - Ingredientes: {row[1]}")
        print(f"   - Productos: {row[2]}")

if __name__ == '__main__':
    try:
        crear_datos_iniciales()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

