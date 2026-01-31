#!/usr/bin/env python3
"""
Script para verificar eventos y diagnosticar por qué no aparecen en el ecommerce
"""
import sys
from datetime import date, datetime
from app import create_app
from app.models import db
from app.models.programacion_models import ProgramacionEvento

def verificar_eventos_ecommerce():
    """Verifica qué eventos deberían aparecer en el ecommerce y por qué no"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("🔍 DIAGNÓSTICO DE EVENTOS PARA ECOMMERCE")
        print("=" * 80)
        print()
        
        # Obtener todos los eventos (no eliminados)
        todos_eventos = ProgramacionEvento.query.filter(
            ProgramacionEvento.eliminado_en.is_(None)
        ).order_by(ProgramacionEvento.fecha.desc()).all()
        
        if not todos_eventos:
            print("❌ No se encontraron eventos en la base de datos")
            print()
            print("💡 SOLUCIÓN:")
            print("   1. Ve a /admin/programacion/crear")
            print("   2. Crea un nuevo evento")
            print("   3. Asegúrate de marcar 'Estado público' como 'publicado'")
            return
        
        print(f"📊 Total de eventos encontrados: {len(todos_eventos)}")
        print()
        
        # Fecha de hoy
        hoy = date.today()
        print(f"📅 Fecha de hoy: {hoy.strftime('%d/%m/%Y')}")
        print()
        
        # Categorizar eventos
        eventos_publicados = []
        eventos_borrador = []
        eventos_pasados = []
        eventos_sin_fecha = []
        eventos_eliminados = []
        
        for evento in todos_eventos:
            # Verificar si está eliminado
            if evento.eliminado_en:
                eventos_eliminados.append(evento)
                continue
            
            # Verificar si tiene fecha
            if not evento.fecha:
                eventos_sin_fecha.append(evento)
                continue
            
            # Verificar si es pasado
            if evento.fecha < hoy:
                eventos_pasados.append(evento)
                continue
            
            # Verificar estado público
            if evento.estado_publico == 'publicado':
                eventos_publicados.append(evento)
            else:
                eventos_borrador.append(evento)
        
        # Mostrar eventos que SÍ aparecerán en el ecommerce
        print("=" * 80)
        print("✅ EVENTOS QUE APARECEN EN EL ECOMMERCE")
        print("=" * 80)
        if eventos_publicados:
            print(f"   Total: {len(eventos_publicados)} evento(s)")
            print()
            for evento in eventos_publicados:
                precios = evento.get_tiers_precios()
                precio_min = min([p.get('precio', 0) for p in precios]) if precios else 0
                print(f"   🎫 {evento.nombre_evento}")
                print(f"      - ID: {evento.id}")
                print(f"      - Fecha: {evento.fecha.strftime('%d/%m/%Y')}")
                print(f"      - Estado: {evento.estado_publico}")
                print(f"      - Precio mínimo: ${precio_min:,.0f}" if precio_min > 0 else "      - Precio: No configurado")
                print(f"      - Aforo: {evento.aforo_objetivo or 'Sin límite'}")
                if evento.horario_apertura_publico:
                    print(f"      - Hora: {evento.horario_apertura_publico.strftime('%H:%M')}")
                print()
        else:
            print("   ❌ No hay eventos que aparezcan en el ecommerce")
            print()
        
        # Mostrar eventos que NO aparecerán y por qué
        print("=" * 80)
        print("⚠️  EVENTOS QUE NO APARECEN EN EL ECOMMERCE")
        print("=" * 80)
        
        # Eventos en borrador
        if eventos_borrador:
            print(f"\n📝 Eventos en BORRADOR ({len(eventos_borrador)}):")
            print("   Estos eventos tienen fecha futura pero no están publicados")
            print()
            for evento in eventos_borrador:
                print(f"   • {evento.nombre_evento} (ID: {evento.id})")
                print(f"     Fecha: {evento.fecha.strftime('%d/%m/%Y')}")
                print(f"     Estado actual: {evento.estado_publico}")
                print(f"     💡 Cambiar estado a 'publicado' para que aparezca")
                print()
        
        # Eventos pasados
        if eventos_pasados:
            print(f"\n📅 Eventos PASADOS ({len(eventos_pasados)}):")
            print("   Estos eventos ya pasaron y no aparecerán automáticamente")
            print()
            for evento in eventos_pasados[:5]:  # Mostrar solo los 5 más recientes
                estado_icon = "✅" if evento.estado_publico == 'publicado' else "📝"
                print(f"   {estado_icon} {evento.nombre_evento} (ID: {evento.id})")
                print(f"     Fecha: {evento.fecha.strftime('%d/%m/%Y')} (pasado)")
                print(f"     Estado: {evento.estado_publico}")
                print()
            if len(eventos_pasados) > 5:
                print(f"   ... y {len(eventos_pasados) - 5} evento(s) más")
                print()
        
        # Eventos sin fecha
        if eventos_sin_fecha:
            print(f"\n❌ Eventos SIN FECHA ({len(eventos_sin_fecha)}):")
            print("   Estos eventos no tienen fecha configurada")
            print()
            for evento in eventos_sin_fecha:
                print(f"   • {evento.nombre_evento} (ID: {evento.id})")
                print(f"     Estado: {evento.estado_publico}")
                print(f"     💡 Agregar fecha futura para que aparezca")
                print()
        
        # Resumen y recomendaciones
        print("=" * 80)
        print("📋 RESUMEN Y RECOMENDACIONES")
        print("=" * 80)
        print()
        
        if eventos_publicados:
            print(f"✅ {len(eventos_publicados)} evento(s) visible(s) en el ecommerce")
        else:
            print("❌ No hay eventos visibles en el ecommerce")
            print()
            print("🔧 ACCIONES RECOMENDADAS:")
            print()
            
            if eventos_borrador:
                print(f"   1. Publicar {len(eventos_borrador)} evento(s) en borrador:")
                for evento in eventos_borrador:
                    print(f"      - {evento.nombre_evento} (ID: {evento.id})")
                    print(f"        Ejecutar: UPDATE programacion_eventos SET estado_publico='publicado' WHERE id={evento.id};")
                print()
            
            if not eventos_borrador and not todos_eventos:
                print("   1. Crear un nuevo evento:")
                print("      - Ir a /admin/programacion/crear")
                print("      - Completar el formulario")
                print("      - Marcar 'Estado público' como 'publicado'")
                print("      - Establecer una fecha futura")
                print()
        
        # Mostrar eventos próximos (futuros o de hoy)
        eventos_futuros = [e for e in todos_eventos if e.fecha and e.fecha >= hoy and not e.eliminado_en]
        if eventos_futuros:
            print("📅 PRÓXIMOS EVENTOS (futuros o de hoy):")
            for evento in sorted(eventos_futuros, key=lambda x: x.fecha):
                estado_icon = "✅" if evento.estado_publico == 'publicado' else "📝"
                dias_restantes = (evento.fecha - hoy).days
                if dias_restantes == 0:
                    tiempo = "HOY"
                elif dias_restantes == 1:
                    tiempo = "MAÑANA"
                else:
                    tiempo = f"en {dias_restantes} días"
                
                print(f"   {estado_icon} {evento.fecha.strftime('%d/%m/%Y')} - {evento.nombre_evento} ({tiempo})")
                if evento.estado_publico != 'publicado':
                    print(f"      ⚠️  Estado: {evento.estado_publico} - Cambiar a 'publicado' para que aparezca")
            print()
        
        print("=" * 80)
        print("✅ Diagnóstico completado")
        print("=" * 80)

if __name__ == '__main__':
    verificar_eventos_ecommerce()



