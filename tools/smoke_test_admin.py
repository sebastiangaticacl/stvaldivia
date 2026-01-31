#!/usr/bin/env python3
"""
Smoke Test para rutas admin - Navega rutas clave y captura errores
Requiere: requests, selenium (opcional para JS errors)
"""

import sys
import os
import json
import time
import requests
from urllib.parse import urljoin
from typing import List, Dict, Optional

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración
BASE_URL = os.environ.get('SMOKE_TEST_URL', 'http://localhost:5001')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# Lista de rutas admin clave (extraídas de routes.py y blueprints)
ADMIN_ROUTES = [
    '/admin',
    '/admin/dashboard',
    '/admin/logs',
    '/admin/turnos',
    '/admin/panel_control',
    '/admin/scanner',
    '/admin/equipo/listar',
    '/admin/inventario',
    '/admin/guardarropia',
    '/encuesta/admin',
    '/admin/programacion',
]

class SmokeTestRunner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.results = {
            'routes_tested': [],
            'errors': [],
            'network_errors': [],
            'start_time': time.time(),
            'end_time': None
        }
    
    def login(self) -> bool:
        """Login como admin"""
        try:
            login_url = urljoin(self.base_url, '/login_admin')
            response = self.session.post(login_url, data={
                'username': ADMIN_USERNAME,
                'password': ADMIN_PASSWORD
            }, allow_redirects=False, timeout=10)
            
            if response.status_code in [302, 200]:
                # Verificar que la sesión está activa
                dashboard_url = urljoin(self.base_url, '/admin/dashboard')
                check_response = self.session.get(dashboard_url, timeout=10)
                return check_response.status_code == 200
            return False
        except Exception as e:
            print(f"❌ Error en login: {e}")
            return False
    
    def test_route(self, route: str) -> Dict:
        """Probar una ruta específica"""
        url = urljoin(self.base_url, route)
        result = {
            'route': route,
            'url': url,
            'status_code': None,
            'error': None,
            'duration_ms': None,
            'content_type': None,
            'has_errors': False
        }
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=15, allow_redirects=True)
            duration = (time.time() - start_time) * 1000
            
            result['status_code'] = response.status_code
            result['duration_ms'] = round(duration, 2)
            result['content_type'] = response.headers.get('Content-Type', '')
            
            # Detectar errores
            if response.status_code >= 500:
                result['has_errors'] = True
                result['error'] = f"Server error {response.status_code}"
                self.results['network_errors'].append({
                    'route': route,
                    'status': response.status_code,
                    'url': url
                })
            elif response.status_code == 404:
                result['has_errors'] = True
                result['error'] = "Not found"
            elif response.status_code >= 400:
                result['has_errors'] = True
                result['error'] = f"Client error {response.status_code}"
            
            # Verificar contenido básico
            if 'text/html' in result['content_type']:
                content = response.text[:1000]  # Primeros 1000 chars
                if 'error' in content.lower() and 'traceback' in content.lower():
                    result['has_errors'] = True
                    result['error'] = "Traceback detected in HTML"
            
        except requests.exceptions.Timeout:
            result['error'] = "Timeout"
            result['has_errors'] = True
        except requests.exceptions.ConnectionError:
            result['error'] = "Connection error"
            result['has_errors'] = True
        except Exception as e:
            result['error'] = str(e)
            result['has_errors'] = True
        
        return result
    
    def run(self) -> Dict:
        """Ejecutar smoke test completo"""
        print(f"🚀 Iniciando smoke test en {self.base_url}")
        
        # Login
        print("🔐 Intentando login...")
        if not self.login():
            print("❌ No se pudo hacer login. Verifica credenciales.")
            return self.results
        
        print("✅ Login exitoso")
        
        # Probar rutas
        print(f"\n📋 Probando {len(ADMIN_ROUTES)} rutas...")
        for route in ADMIN_ROUTES:
            print(f"  → {route}", end=' ... ', flush=True)
            result = self.test_route(route)
            self.results['routes_tested'].append(result)
            
            if result['has_errors']:
                print(f"❌ {result.get('error', 'Error')}")
            else:
                print(f"✅ {result['status_code']} ({result['duration_ms']:.0f}ms)")
            
            time.sleep(0.5)  # Pequeña pausa entre requests
        
        self.results['end_time'] = time.time()
        self.results['total_duration'] = round(self.results['end_time'] - self.results['start_time'], 2)
        
        # Resumen
        total = len(self.results['routes_tested'])
        errors = sum(1 for r in self.results['routes_tested'] if r['has_errors'])
        success = total - errors
        
        print(f"\n📊 Resumen:")
        print(f"  Total: {total}")
        print(f"  ✅ Exitosas: {success}")
        print(f"  ❌ Errores: {errors}")
        print(f"  ⏱️  Duración: {self.results['total_duration']:.2f}s")
        
        return self.results
    
    def export_json(self, filename: Optional[str] = None) -> str:
        """Exportar resultados a JSON"""
        if filename is None:
            filename = f"smoke_test_results_{int(time.time())}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        return filename


def main():
    """Función principal"""
    runner = SmokeTestRunner(BASE_URL)
    results = runner.run()
    
    # Exportar JSON
    output_file = runner.export_json()
    print(f"\n💾 Resultados exportados a: {output_file}")
    
    # Retornar código de salida según errores
    errors = sum(1 for r in results['routes_tested'] if r['has_errors'])
    sys.exit(0 if errors == 0 else 1)


if __name__ == '__main__':
    main()

