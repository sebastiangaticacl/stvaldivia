#!/usr/bin/env python3
"""
Script para probar el chatbot BIMBA con la nueva configuración minimalista
Verifica que las respuestas sean cortas (máx 12 palabras, 2 líneas)
"""
import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.application.services.intent_router import IntentRouter
from app.application.services.bot_rule_engine import BotRuleEngine
from app.application.services.programacion_service import ProgramacionService
from app.application.services.operational_insights_service import OperationalInsightsService

def contar_palabras(texto):
    """Cuenta las palabras en un texto"""
    return len(texto.split())

def contar_lineas(texto):
    """Cuenta las líneas en un texto"""
    return len(texto.split('\n'))

def probar_respuestas_reglas():
    """Prueba las respuestas del motor de reglas"""
    print("=" * 60)
    print("🧪 PRUEBA: Motor de Reglas (Respuestas Minimalistas)")
    print("=" * 60)
    print()
    
    # Obtener contexto
    programacion_service = ProgramacionService()
    evento_info = programacion_service.get_public_info_for_today()
    operational = OperationalInsightsService.get_daily_summary()
    
    # Preguntas de prueba
    preguntas = [
        ("¿Qué hay hoy?", IntentRouter.INTENT_EVENTO_HOY),
        ("¿Cómo va la noche?", IntentRouter.INTENT_ESTADO_NOCHE),
        ("¿Qué eventos vienen?", IntentRouter.INTENT_PROXIMOS_EVENTOS),
        ("¿Cuánto cuesta la entrada?", IntentRouter.INTENT_PRECIOS),
        ("¿A qué hora abren?", IntentRouter.INTENT_HORARIO),
        ("¿Hay lista?", IntentRouter.INTENT_LISTA),
        ("¿Quién toca hoy?", IntentRouter.INTENT_DJS),
        ("¿Cómo funciona el sistema?", IntentRouter.INTENT_COMO_FUNCIONA),
    ]
    
    resultados = []
    
    for pregunta, intent_esperado in preguntas:
        # Detectar intención
        intent_detectado = IntentRouter.detectar_intent(pregunta)
        
        # Generar respuesta
        respuesta = BotRuleEngine.generar_respuesta(intent_detectado, evento_info, operational)
        
        if respuesta:
            palabras = contar_palabras(respuesta)
            lineas = contar_lineas(respuesta)
            
            # Verificar límites
            cumple_palabras = palabras <= 12
            cumple_lineas = lineas <= 2
            
            estado = "✅" if (cumple_palabras and cumple_lineas) else "⚠️"
            
            resultados.append({
                'pregunta': pregunta,
                'intent': intent_detectado,
                'respuesta': respuesta,
                'palabras': palabras,
                'lineas': lineas,
                'cumple': cumple_palabras and cumple_lineas
            })
            
            print(f"{estado} {pregunta}")
            print(f"   Intent: {intent_detectado}")
            print(f"   Respuesta: {respuesta[:80]}{'...' if len(respuesta) > 80 else ''}")
            print(f"   Palabras: {palabras}/12 | Líneas: {lineas}/2")
            print()
        else:
            print(f"⚠️  {pregunta}")
            print(f"   Intent: {intent_detectado}")
            print(f"   Respuesta: None (pasa a OpenAI)")
            print()
    
    # Resumen
    print("=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)
    
    total = len(resultados)
    cumplen = sum(1 for r in resultados if r['cumple'])
    
    print(f"Total de respuestas: {total}")
    print(f"Cumplen límites (≤12 palabras, ≤2 líneas): {cumplen}/{total}")
    
    if cumplen == total:
        print("✅ Todas las respuestas cumplen los límites minimalistas")
    else:
        print("⚠️  Algunas respuestas exceden los límites:")
        for r in resultados:
            if not r['cumple']:
                print(f"   - {r['pregunta']}: {r['palabras']} palabras, {r['lineas']} líneas")
    
    print()
    
    # Verificar que no hay emojis (excepto en casos especiales)
    print("🔍 Verificación de Emojis:")
    emojis_encontrados = []
    for r in resultados:
        emojis = [c for c in r['respuesta'] if ord(c) > 127 and c not in 'áéíóúñÁÉÍÓÚÑ']
        if emojis:
            emojis_encontrados.append((r['pregunta'], emojis))
    
    if emojis_encontrados:
        print("⚠️  Se encontraron emojis en las respuestas:")
        for pregunta, emojis in emojis_encontrados:
            print(f"   - {pregunta}: {emojis}")
    else:
        print("✅ No se encontraron emojis en las respuestas de reglas")
    
    print()
    return resultados

def probar_temperatura():
    """Verifica que la temperatura esté configurada en 0.3"""
    print("=" * 60)
    print("🌡️  VERIFICACIÓN: Configuración de Temperatura")
    print("=" * 60)
    print()
    
    # Leer archivos para verificar temperatura
    archivos = [
        'app/routes/api_bimba.py',
        'app/blueprints/api/api_v1.py'
    ]
    
    for archivo in archivos:
        if os.path.exists(archivo):
            with open(archivo, 'r') as f:
                contenido = f.read()
                if 'temperature=0.3' in contenido:
                    print(f"✅ {archivo}: temperature=0.3")
                elif 'temperature=0.7' in contenido:
                    print(f"⚠️  {archivo}: Aún tiene temperature=0.7")
                else:
                    print(f"❓ {archivo}: No se encontró configuración de temperature")
        else:
            print(f"❌ {archivo}: Archivo no encontrado")
    
    print()

if __name__ == '__main__':
    try:
        app = create_app()
        
        with app.app_context():
            print("🚀 Iniciando pruebas del chatbot minimalista...")
            print()
            
            # Probar respuestas de reglas
            resultados = probar_respuestas_reglas()
            
            # Verificar temperatura
            probar_temperatura()
            
            print("=" * 60)
            print("✅ PRUEBAS COMPLETADAS")
            print("=" * 60)
            print()
            print("💡 Próximos pasos:")
            print("   1. Prueba el chatbot en vivo: http://127.0.0.1:5001/chat_bimba")
            print("   2. Verifica que las respuestas sean cortas y directas")
            print("   3. Ajusta los límites si es necesario")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

