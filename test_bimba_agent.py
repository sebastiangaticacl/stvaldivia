#!/usr/bin/env python3
"""
Script para probar el agente BIMBA con diferentes preguntas
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_bimba_agent():
    """Prueba el agente BIMBA con preguntas sobre el sistema"""
    # Crear contexto de aplicación Flask
    from app import create_app
    app = create_app()
    
    with app.app_context():
        from app.application.services.bimba_bot_engine import BimbaBotEngine
        
        print("=" * 70)
        print("🤖 PRUEBAS DEL AGENTE BIMBA CON CONOCIMIENTO DEL SISTEMA")
        print("=" * 70)
        print()
        
        # Preguntas de prueba
        preguntas = [
            {
                "pregunta": "¿Cómo funciona el sistema de pedidos?",
                "canal": "web",
                "descripcion": "Pregunta sobre el flujo de pedidos"
            },
            {
                "pregunta": "¿Qué es una jornada?",
                "canal": "interno",
                "descripcion": "Concepto básico del sistema"
            },
            {
                "pregunta": "Explícame el flujo de una venta",
                "canal": "instagram",
                "descripcion": "Flujo completo de venta"
            },
            {
                "pregunta": "¿Qué información puedo ver en el dashboard?",
                "canal": "whatsapp",
                "descripcion": "Información del dashboard"
            },
            {
                "pregunta": "¿Cómo se entregan los productos?",
                "canal": "web",
                "descripcion": "Sistema de entregas"
            },
            {
                "pregunta": "¿Qué es un ticket QR?",
                "canal": "instagram",
                "descripcion": "Sistema de tickets"
            }
        ]
        
        for i, test in enumerate(preguntas, 1):
            print(f"\n{'=' * 70}")
            print(f"PRUEBA {i}/{len(preguntas)}")
            print(f"{'=' * 70}")
            print(f"📝 Pregunta: {test['pregunta']}")
            print(f"📱 Canal: {test['canal']}")
            print(f"📋 Descripción: {test['descripcion']}")
            print(f"\n💬 Procesando...\n")
            
            try:
                respuesta, fuente = BimbaBotEngine.generar_respuesta(
                    mensaje_usuario=test['pregunta'],
                    canal=test['canal']
                )
                
                if respuesta:
                    print(f"✅ Respuesta generada (Fuente: {fuente or 'OpenAI'}):")
                    print(f"\n{respuesta}\n")
                else:
                    print("⚠️  No se generó respuesta (probablemente requiere OpenAI)")
                    print("   Para probar con OpenAI, usar la API /api/v1/bot/responder\n")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            print("-" * 70)
        
        print("\n" + "=" * 70)
        print("✅ PRUEBAS COMPLETADAS")
        print("=" * 70)
        print("\n💡 Nota: Si las respuestas muestran 'None', necesitas:")
        print("   1. Configurar la API key de OpenAI en las variables de entorno")
        print("   2. O probar directamente desde el panel web: /admin/bot/logs")
        print()

if __name__ == "__main__":
    test_bimba_agent()
