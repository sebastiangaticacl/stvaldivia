#!/usr/bin/env python3
"""
Script para publicar eventos y hacerlos visibles en el ecommerce
"""
import sys
from datetime import date
from app import create_app
from app.models import db
from app.models.programacion_models import ProgramacionEvento

def publicar_eventos():
    """Publica eventos que están en borrador y tienen fecha futura"""
    app = create_app()
    
    with app.app_context():
        print("=" * 80)
        print("📢 PUBLICAR EVENTOS PARA ECOMMERCE")
        print("=" * 80)
        print()
        
        hoy = date.today()
        
        # Buscar eventos en borrador con fecha futura
        eventos_borrador = ProgramacionEvento.query.filter(
            ProgramacionEvento.estado_publico == 'borrador',
            ProgramacionEvento.fecha >= hoy,
            ProgramacionEvento.eliminado_en.is_(None)
        ).order_by(ProgramacionEvento.fecha.asc()).all()
        
        if not eventos_borrador:
            print("✅ No hay eventos en borrador con fecha futura para publicar")
            print()
            
            # Mostrar todos los eventos futuros
            eventos_futuros = ProgramacionEvento.query.filter(
                ProgramacionEvento.fecha >= hoy,
                ProgramacionEvento.eliminado_en.is_(None)
            ).order_by(ProgramacionEvento.fecha.asc()).all()
            
            if eventos_futuros:
                print("📋 Eventos futuros encontrados:")
                for evento in eventos_futuros:
                    estado_icon = "✅" if evento.estado_publico == 'publicado' else "📝"
                    print(f"   {estado_icon} {evento.fecha.strftime('%d/%m/%Y')} - {evento.nombre_evento}")
                    print(f"      Estado: {evento.estado_publico}")
                print()
            return
        
        print(f"📝 Encontrados {len(eventos_borrador)} evento(s) en borrador con fecha futura:")
        print()
        
        for evento in eventos_borrador:
            print(f"   • {evento.nombre_evento}")
            print(f"     ID: {evento.id}")
            print(f"     Fecha: {evento.fecha.strftime('%d/%m/%Y')}")
            print(f"     Estado actual: {evento.estado_publico}")
            print()
        
        # Preguntar confirmación
        respuesta = input("¿Publicar todos estos eventos? (s/n): ").strip().lower()
        
        if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
            print("❌ Operación cancelada")
            return
        
        # Publicar eventos
        publicados = 0
        for evento in eventos_borrador:
            try:
                evento.estado_publico = 'publicado'
                evento.actualizado_en = db.session.query(db.func.now()).scalar()
                db.session.commit()
                publicados += 1
                print(f"✅ Publicado: {evento.nombre_evento} (ID: {evento.id})")
            except Exception as e:
                db.session.rollback()
                print(f"❌ Error al publicar {evento.nombre_evento}: {e}")
        
        print()
        print("=" * 80)
        print(f"✅ {publicados} evento(s) publicado(s) exitosamente")
        print("=" * 80)
        print()
        print("💡 Los eventos ahora deberían aparecer en el ecommerce")
        print("   Verifica en: /ecommerce/")

def publicar_evento_por_id(evento_id):
    """Publica un evento específico por su ID"""
    app = create_app()
    
    with app.app_context():
        evento = ProgramacionEvento.query.get(evento_id)
        
        if not evento:
            print(f"❌ Evento con ID {evento_id} no encontrado")
            return False
        
        if evento.eliminado_en:
            print(f"❌ El evento '{evento.nombre_evento}' está eliminado")
            return False
        
        if evento.estado_publico == 'publicado':
            print(f"ℹ️  El evento '{evento.nombre_evento}' ya está publicado")
            return True
        
        hoy = date.today()
        if evento.fecha and evento.fecha < hoy:
            print(f"⚠️  El evento '{evento.nombre_evento}' tiene fecha pasada ({evento.fecha})")
            respuesta = input("¿Publicar de todas formas? (s/n): ").strip().lower()
            if respuesta not in ['s', 'si', 'sí', 'y', 'yes']:
                return False
        
        try:
            evento.estado_publico = 'publicado'
            evento.actualizado_en = db.session.query(db.func.now()).scalar()
            db.session.commit()
            print(f"✅ Evento '{evento.nombre_evento}' publicado exitosamente")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al publicar evento: {e}")
            return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Publicar evento específico por ID
        try:
            evento_id = int(sys.argv[1])
            publicar_evento_por_id(evento_id)
        except ValueError:
            print("❌ ID de evento inválido. Debe ser un número.")
    else:
        # Publicar todos los eventos en borrador
        publicar_eventos()



