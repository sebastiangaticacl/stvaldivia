#!/usr/bin/env python3
"""
SMOKE TEST: Flujo de pago POS /caja/api/sale/create
(Con impresión QR desactivada/tolerada)

OBJETIVO:
Probar que EFECTIVO (cash/NONE) y TARJETA (debit/GETNET)
FUNCIONAN end-to-end SIN romper el flujo aunque falle impresión.

REGLAS:
- NO tocar frontend
- NO tocar lógica de negocio principal
- NO eliminar impresión QR
- El test DEBE:
  - aceptar warnings de impresión
  - NO fallar si hay errores tipo:
    "No se pudo imprimir ticket"
    "No se encontró impresora"
    "Error al crear estado de entrega"
  - SOLO fallar si la API responde success:false o HTTP != 200

DETECCIÓN DE SESIÓN:
- Usa Flask test client con session_transaction()
- Setea las siguientes session keys (encontradas en app/blueprints/pos/views/):
  - pos_logged_in: True
  - pos_register_id: "5" (caja TEST)
  - pos_employee_id: "TEST0000"
  - pos_employee_name: "Usuario Test"
  - pos_register_name: "CAJA TEST BIMBA"

ENDPOINTS USADOS:
- POST /caja/api/sale/create

ASSERTS:
- HTTP 200
- JSON {success: true}
- Existe sale_id o sale_id_local en respuesta
- NO exigir impresión exitosa (warnings tolerados)

PRODUCTO DE PRUEBA:
- Busca Product.external_id == "TEST100" o Product.name == "TEST PRODUCTO $100"
- Si no existe: abort con mensaje "NO TEST PRODUCT FOUND (run seed-test)"
"""

import sys
import os

# Agregar el directorio raíz al path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.models.product_models import Product
from flask import session

def test_cash_payment(app):
    """Test venta en EFECTIVO (cash/NONE)"""
    print("\n🧪 TEST 1: EFECTIVO (cash/NONE)")
    
    # Buscar producto de prueba
    test_product = Product.query.filter(
        (Product.external_id == "TEST100") | (Product.name == "TEST PRODUCTO $100")
    ).first()
    
    if not test_product:
        print("❌ FAIL: NO TEST PRODUCT FOUND (run seed-test)")
        return False
    
    # Preparar carrito
    cart = [{
        'item_id': str(test_product.id),
        'name': test_product.name,
        'price': float(test_product.price),
        'quantity': 1
    }]
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Setear sesión de caja (keys encontradas en app/blueprints/pos/views/)
            sess['pos_logged_in'] = True
            sess['pos_register_id'] = "5"  # Caja TEST
            sess['pos_employee_id'] = "TEST0000"
            sess['pos_employee_name'] = "Usuario Test"
            sess['pos_register_name'] = "CAJA TEST BIMBA"
            # El endpoint lee el carrito desde session, no del JSON
            sess['pos_cart'] = cart
        
        # Payload para venta en EFECTIVO (el carrito ya está en session)
        payload = {
            'payment_type': 'cash',
            'payment_provider': 'NONE'
        }
        
        # POST /caja/api/sale/create
        response = client.post(
            '/caja/api/sale/create',
            json=payload,
            content_type='application/json'
        )
        
        # Asserts
        status_code = response.status_code
        try:
            data = response.get_json()
        except:
            data = None
        
        if status_code == 200 and data and data.get('success') is True:
            sale_id = data.get('sale_id') or data.get('sale_id_local')
            if sale_id:
                # Verificar si hay warnings de impresión (tolerados)
                ticket_printed = data.get('ticket_printed', '')
                if ticket_printed and ticket_printed not in ['impreso', 'no_intentado']:
                    print(f"⚠️  Printer not available (ignored) - ticket_printed: {ticket_printed}")
                print(f"✅ PASS CASH (venta creada, impresión ignorada) - sale_id: {sale_id}")
                return True
            else:
                print(f"❌ FAIL CASH - success=true pero no hay sale_id. Response: {str(data)[:800]}")
                return False
        else:
            print(f"❌ FAIL CASH - status_code: {status_code}")
            if data:
                print(f"   Response: {str(data)[:800]}")
            else:
                print(f"   Response body: {response.data[:800].decode('utf-8', errors='ignore')}")
            return False


def test_debit_payment(app):
    """Test venta en TARJETA (debit/GETNET)"""
    print("\n🧪 TEST 2: TARJETA (debit/GETNET)")
    
    # Buscar producto de prueba
    test_product = Product.query.filter(
        (Product.external_id == "TEST100") | (Product.name == "TEST PRODUCTO $100")
    ).first()
    
    if not test_product:
        print("❌ FAIL: NO TEST PRODUCT FOUND (run seed-test)")
        return False
    
    # Preparar carrito
    cart = [{
        'item_id': str(test_product.id),
        'name': test_product.name,
        'price': float(test_product.price),
        'quantity': 1
    }]
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Setear sesión de caja
            sess['pos_logged_in'] = True
            sess['pos_register_id'] = "5"  # Caja TEST
            sess['pos_employee_id'] = "TEST0000"
            sess['pos_employee_name'] = "Usuario Test"
            sess['pos_register_name'] = "CAJA TEST BIMBA"
            # El endpoint lee el carrito desde session, no del JSON
            sess['pos_cart'] = cart
        
        # Payload para venta en TARJETA (el carrito ya está en session)
        payload = {
            'payment_type': 'debit',
            'payment_provider': 'GETNET'
        }
        
        # POST /caja/api/sale/create
        response = client.post(
            '/caja/api/sale/create',
            json=payload,
            content_type='application/json'
        )
        
        # Asserts
        status_code = response.status_code
        try:
            data = response.get_json()
        except:
            data = None
        
        if status_code == 200 and data and data.get('success') is True:
            sale_id = data.get('sale_id') or data.get('sale_id_local')
            if sale_id:
                # Verificar si hay warnings de impresión (tolerados)
                ticket_printed = data.get('ticket_printed', '')
                if ticket_printed and ticket_printed not in ['impreso', 'no_intentado']:
                    print(f"⚠️  Printer not available (ignored) - ticket_printed: {ticket_printed}")
                print(f"✅ PASS DEBIT (venta creada, impresión ignorada) - sale_id: {sale_id}")
                return True
            else:
                print(f"❌ FAIL DEBIT - success=true pero no hay sale_id. Response: {str(data)[:800]}")
                return False
        else:
            print(f"❌ FAIL DEBIT - status_code: {status_code}")
            if data:
                print(f"   Response: {str(data)[:800]}")
            else:
                print(f"   Response body: {response.data[:800].decode('utf-8', errors='ignore')}")
            return False


def main():
    """Ejecutar smoke tests"""
    print("=" * 60)
    print("🧪 POS SMOKE TEST")
    print("=" * 60)
    
    # Crear app Flask con testing activado
    app = create_app()
    app.testing = True
    
    with app.app_context():
        # Verificar que existe producto de prueba
        test_product = Product.query.filter(
            (Product.external_id == "TEST100") | (Product.name == "TEST PRODUCTO $100")
        ).first()
        
        if not test_product:
            print("\n❌ ERROR: NO TEST PRODUCT FOUND")
            print("   Ejecuta: python -c 'from app import create_app; from app.helpers.seed_test_data import seed_test_register_and_product; app = create_app(); app.app_context().push(); seed_test_register_and_product()'")
            print("   O desde admin: http://127.0.0.1:5001/admin/cajas/ -> 'Seed Test'")
            sys.exit(1)
        
        print(f"✅ Producto de prueba encontrado: {test_product.name} (ID: {test_product.id}, Precio: ${test_product.price})")
        
        # Ejecutar tests
        result_cash = test_cash_payment(app)
        result_debit = test_debit_payment(app)
        
        # Resumen
        print("\n" + "=" * 60)
        if result_cash and result_debit:
            print("✅ ALL TESTS PASSED")
        else:
            print("❌ SOME TESTS FAILED")
            if not result_cash:
                print("   - EFECTIVO: FAIL")
            if not result_debit:
                print("   - TARJETA: FAIL")
        print("=" * 60)
        
        sys.exit(0 if (result_cash and result_debit) else 1)


if __name__ == '__main__':
    main()

