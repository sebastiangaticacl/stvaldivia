#!/usr/bin/env python3
"""
Script para crear/actualizar el evento "Preventa Año Nuevo BIMBA"
con precio $5000 y 50 cupos
"""
import sys
import os
from datetime import datetime, date, time

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db
from app.models.programacion_models import ProgramacionEvento

def crear_preventa_ano_nuevo():
    """Crea o actualiza el evento de preventa Año Nuevo"""
    app = create_app()
    
    with app.app_context():
        try:
            # Buscar si ya existe un evento con este nombre
            evento = ProgramacionEvento.query.filter_by(
                nombre_evento='Preventa Año Nuevo BIMBA',
                eliminado_en=None
            ).first()
            
            # Fecha del evento: 31 de diciembre de 2025 (Año Nuevo)
            fecha_evento = date(2025, 12, 31)
            
            if evento:
                print(f"✅ Evento encontrado (ID: {evento.id}), actualizando...")
                evento.fecha = fecha_evento
                evento.estado_publico = 'publicado'
                evento.aforo_objetivo = 50
                evento.horario_apertura_publico = time(20, 0)  # 20:00
                evento.descripcion_corta = 'Preventa especial para Año Nuevo en BIMBA'
                evento.actualizado_en = datetime.utcnow()
            else:
                print("➕ Creando nuevo evento...")
                evento = ProgramacionEvento(
                    fecha=fecha_evento,
                    nombre_evento='Preventa Año Nuevo BIMBA',
                    tipo_noche='Año Nuevo',
                    estado_publico='publicado',
                    estado_produccion='confirmado',
                    aforo_objetivo=50,
                    horario_apertura_publico=time(20, 0),  # 20:00
                    descripcion_corta='Preventa especial para Año Nuevo en BIMBA',
                    creado_por='sistema',
                    creado_en=datetime.utcnow(),
                    actualizado_en=datetime.utcnow()
                )
                db.session.add(evento)
            
            # Configurar precio: $5000
            precios = [{
                'tier': 'Preventa',
                'precio': 5000,
                'hasta': None  # Sin límite de fecha, pero limitado por cupos
            }]
            evento.set_tiers_precios(precios)
            
            db.session.commit()
            
            print(f"✅ Evento configurado exitosamente:")
            print(f"   - Nombre: {evento.nombre_evento}")
            print(f"   - Fecha: {evento.fecha}")
            print(f"   - Precio: $5,000")
            print(f"   - Cupos: {evento.aforo_objetivo}")
            print(f"   - Estado: {evento.estado_publico}")
            print(f"   - ID: {evento.id}")
            
            # Verificar que aparezca en el ecommerce
            print("\n📋 Verificando disponibilidad en ecommerce...")
            eventos_publicos = ProgramacionEvento.query.filter(
                ProgramacionEvento.estado_publico == 'publicado',
                ProgramacionEvento.fecha >= date.today(),
                ProgramacionEvento.eliminado_en.is_(None)
            ).all()
            
            encontrado = any(e.id == evento.id for e in eventos_publicos)
            if encontrado:
                print("✅ El evento está publicado y aparecerá en el ecommerce")
            else:
                print("⚠️ El evento no aparece en la lista de eventos públicos")
            
            return evento
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error al crear/actualizar evento: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == '__main__':
    crear_preventa_ano_nuevo()

