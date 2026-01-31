#!/usr/bin/env python3
"""
Smoke test para rutas del POS
Valida que /caja y /caja/login respondan correctamente
"""
import requests
import sys
from urllib.parse import urljoin

def test_pos_routes(base_url='https://stvaldivia.cl'):
    """Test de rutas del POS"""
    results = []
    
    # Test 1: GET /caja (debe redirigir o responder 200/302)
    print("Testing GET /caja...")
    try:
        response = requests.get(urljoin(base_url, '/caja'), allow_redirects=False, timeout=10)
        status = response.status_code
        location = response.headers.get('Location', '')
        
        if status == 302 and '/caja/login' in location:
            print(f"✅ GET /caja -> {status} (redirect to /caja/login)")
            results.append(('GET /caja', status, 'PASS', 'Redirects to /caja/login'))
        elif status == 200:
            print(f"✅ GET /caja -> {status} (OK)")
            results.append(('GET /caja', status, 'PASS', 'Returns 200'))
        else:
            print(f"❌ GET /caja -> {status} (expected 200 or 302)")
            results.append(('GET /caja', status, 'FAIL', f'Unexpected status: {status}'))
    except Exception as e:
        print(f"❌ GET /caja -> ERROR: {e}")
        results.append(('GET /caja', 'ERROR', 'FAIL', str(e)))
    
    # Test 2: GET /caja/ (con trailing slash)
    print("\nTesting GET /caja/...")
    try:
        response = requests.get(urljoin(base_url, '/caja/'), allow_redirects=False, timeout=10)
        status = response.status_code
        location = response.headers.get('Location', '')
        
        if status == 302 and '/caja/login' in location:
            print(f"✅ GET /caja/ -> {status} (redirect to /caja/login)")
            results.append(('GET /caja/', status, 'PASS', 'Redirects to /caja/login'))
        elif status == 200:
            print(f"✅ GET /caja/ -> {status} (OK)")
            results.append(('GET /caja/', status, 'PASS', 'Returns 200'))
        else:
            print(f"❌ GET /caja/ -> {status} (expected 200 or 302)")
            results.append(('GET /caja/', status, 'FAIL', f'Unexpected status: {status}'))
    except Exception as e:
        print(f"❌ GET /caja/ -> ERROR: {e}")
        results.append(('GET /caja/', 'ERROR', 'FAIL', str(e)))
    
    # Test 3: GET /caja/login (debe responder 200)
    print("\nTesting GET /caja/login...")
    try:
        response = requests.get(urljoin(base_url, '/caja/login'), allow_redirects=False, timeout=10)
        status = response.status_code
        
        if status == 200:
            print(f"✅ GET /caja/login -> {status} (OK)")
            results.append(('GET /caja/login', status, 'PASS', 'Returns 200'))
        else:
            print(f"❌ GET /caja/login -> {status} (expected 200)")
            results.append(('GET /caja/login', status, 'FAIL', f'Unexpected status: {status}'))
    except Exception as e:
        print(f"❌ GET /caja/login -> ERROR: {e}")
        results.append(('GET /caja/login', 'ERROR', 'FAIL', str(e)))
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)
    for route, status, result, note in results:
        symbol = "✅" if result == 'PASS' else "❌"
        print(f"{symbol} {route:20} -> {str(status):6} ({note})")
    
    # Retornar código de salida
    all_passed = all(r[2] == 'PASS' for r in results)
    return 0 if all_passed else 1

if __name__ == '__main__':
    base_url = sys.argv[1] if len(sys.argv) > 1 else 'https://stvaldivia.cl'
    print(f"Testing POS routes on: {base_url}\n")
    sys.exit(test_pos_routes(base_url))


