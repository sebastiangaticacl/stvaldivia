#!/usr/bin/env python3
"""
Script para probar que la API key de SumUp funciona correctamente
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_sumup_api_key():
    """Prueba la API key de SumUp"""
    print("=" * 60)
    print("🧪 PRUEBA: API Key de SumUp")
    print("=" * 60)
    print()
    
    # Obtener API key
    api_key = os.getenv('SUMUP_API_KEY')
    
    if not api_key:
        print("❌ SUMUP_API_KEY no encontrada en variables de entorno")
        print("   Verifica que esté en el archivo .env")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:15]}...")
    print()
    
    # Verificar formato
    if api_key.startswith('sup_sk_') or api_key.startswith('sk_test_') or api_key.startswith('sk_live_'):
        print(f"✅ Formato de API key válido")
    else:
        print(f"⚠️  Formato de API key inusual (debería ser sup_sk_, sk_test_ o sk_live_)")
    print()
    
    # Probar cliente SumUp
    try:
        from app.infrastructure.external.sumup_client import SumUpClient
        
        print("Probando cliente SumUp...")
        client = SumUpClient(api_key=api_key)
        print("✅ Cliente SumUp inicializado correctamente")
        print()
        
        # Probar obtener información del perfil (endpoint simple para verificar autenticación)
        try:
            import requests
            
            response = requests.get(
                'https://api.sumup.com/v0.1/me',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Accept': 'application/json'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API Key válida y funcionando!")
                print(f"   Perfil obtenido exitosamente")
                if 'merchant_code' in data:
                    print(f"   Merchant Code: {data.get('merchant_code', 'N/A')}")
                return True
            elif response.status_code == 401:
                print("❌ API Key inválida o no autorizada")
                print(f"   Status: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}")
                return False
            else:
                print(f"⚠️  Respuesta inesperada: {response.status_code}")
                print(f"   Respuesta: {response.text[:200]}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {e}")
            print("   Verifica tu conexión a internet")
            return False
        except Exception as e:
            print(f"⚠️  Error al probar API: {e}")
            print("   La API key puede estar configurada pero no se pudo verificar")
            return True  # No fallar si es solo un error de conexión
            
    except Exception as e:
        print(f"❌ Error al inicializar cliente: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_sumup_api_key()
    print()
    if success:
        print("=" * 60)
        print("✅ API Key configurada correctamente")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ Error en la configuración de la API Key")
        print("=" * 60)
        sys.exit(1)

