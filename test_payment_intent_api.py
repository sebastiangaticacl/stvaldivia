#!/usr/bin/env python3
"""
Script de prueba para la API de PaymentIntent
Prueba POST /caja/api/payment/intents
"""
import requests
import json
import sys
from urllib.parse import urljoin

# Configuración
BASE_URL = 'http://127.0.0.1:5001'
# BASE_URL = 'https://stvaldivia.cl'  # Para probar en producción

def test_create_payment_intent(base_url=BASE_URL):
    """Prueba crear un PaymentIntent"""
    
    print("=" * 60)
    print("PRUEBA: POST /caja/api/payment/intents")
    print("=" * 60)
    
    # URL del endpoint
    url = urljoin(base_url, '/caja/api/payment/intents')
    
    # Payload de prueba
    payload = {
        "register_id": "1",  # TEST001
        "provider": "GETNET",
        "amount_total": 1500.0
    }
    
    print(f"\n📤 URL: {url}")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # IMPORTANTE: Esta ruta requiere sesión POS activa
        # Para probar completamente necesitas:
        # 1. Hacer login en /caja/login primero
        # 2. Obtener la cookie de sesión
        # 3. Usar esa cookie en esta request
        
        print("\n⚠️  NOTA: Esta ruta requiere autenticación POS.")
        print("   Opciones para probar:")
        print("   1. Usar sesión de navegador (copiar cookies)")
        print("   2. Hacer login programático primero")
        print("   3. Probar desde el frontend (sales.html)")
        
        # Intentar la request (fallará sin auth, pero vemos el error)
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"\n📥 Status Code: {response.status_code}")
        print(f"📥 Headers: {dict(response.headers)}")
        
        try:
            result = response.json()
            print(f"📥 Response JSON:\n{json.dumps(result, indent=2)}")
        except:
            print(f"📥 Response Text: {response.text[:500]}")
        
        # Interpretar resultado
        if response.status_code == 401:
            print("\n❌ Error 401: No autenticado")
            print("   Esto es esperado si no hay sesión activa.")
            print("   Para probar correctamente, necesitas hacer login primero.")
        elif response.status_code == 400:
            print(f"\n⚠️  Error 400: {result.get('error', 'Bad Request')}")
        elif response.status_code == 201:
            intent_id = result.get('intent_id')
            print(f"\n✅ SUCCESS! PaymentIntent creado:")
            print(f"   Intent ID: {intent_id}")
            print(f"   Verifica logs para: [PAYMENT_INTENT] READY→")
        else:
            print(f"\n❓ Status inesperado: {response.status_code}")
        
        return response.status_code == 201
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: No se pudo conectar a {base_url}")
        print("   Verifica que el servidor esté corriendo:")
        print(f"   - Local: python run_local.py")
        print(f"   - Producción: Verifica que stvaldivia.cl esté disponible")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_session(base_url=BASE_URL, session_cookie=None):
    """
    Prueba con cookie de sesión (opcional)
    
    Para obtener la cookie:
    1. Abre el navegador
    2. Ve a /caja/login y haz login
    3. Abre DevTools → Application → Cookies
    4. Copia el valor de 'session'
    5. Pásalo como session_cookie
    """
    if not session_cookie:
        print("\n⚠️  No se proporcionó cookie de sesión")
        return False
    
    url = urljoin(base_url, '/caja/api/payment/intents')
    payload = {
        "register_id": "1",
        "provider": "GETNET",
        "amount_total": 2500.0
    }
    
    cookies = {'session': session_cookie}
    
    print(f"\n🔐 Probando con cookie de sesión...")
    response = requests.post(url, json=payload, cookies=cookies, timeout=10)
    
    print(f"Status: {response.status_code}")
    try:
        result = response.json()
        print(json.dumps(result, indent=2))
        return response.status_code == 201
    except:
        print(response.text)
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test PaymentIntent API')
    parser.add_argument('--url', default=BASE_URL, help='Base URL (default: http://127.0.0.1:5001)')
    parser.add_argument('--session', help='Session cookie value (opcional)')
    args = parser.parse_args()
    
    # Test básico (sin auth - veremos el error)
    print("\n" + "=" * 60)
    print("TEST 1: Crear PaymentIntent (sin autenticación)")
    print("=" * 60)
    success1 = test_create_payment_intent(args.url)
    
    # Test con sesión si se proporciona
    if args.session:
        print("\n" + "=" * 60)
        print("TEST 2: Crear PaymentIntent (con autenticación)")
        print("=" * 60)
        success2 = test_with_session(args.url, args.session)
        sys.exit(0 if success2 else 1)
    else:
        print("\n" + "=" * 60)
        print("💡 Para probar con autenticación:")
        print("=" * 60)
        print("python test_payment_intent_api.py --url <URL> --session '<cookie_value>'")
        sys.exit(0 if success1 else 1)














