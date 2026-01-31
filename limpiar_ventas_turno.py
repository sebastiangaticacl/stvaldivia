#!/usr/bin/env python3
"""
Script para ELIMINAR completamente todas las ventas del turno actual (jornada abierta)
Uso: python limpiar_ventas_turno.py [--yes]
⚠️  ADVERTENCIA: Este script ELIMINA físicamente las ventas de la base de datos
"""
import sys
from app import create_app
from app.models import db
from app.models.pos_models import PosSale
from app.models.jornada_models import Jornada
from app.models.sale_delivery_models import SaleDeliveryStatus, DeliveryItem
from app.models.ticket_entrega_models import TicketEntrega
from datetime import datetime
from app.utils.timezone import CHILE_TZ

def limpiar_ventas_turno(auto_confirm=False):
    """Eliminar completamente todas las ventas del turno actual (jornada abierta)"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Buscando jornada abierta...")
        
        # Buscar jornada abierta
        jornada_abierta = Jornada.query.filter_by(
            estado_apertura='abierto',
            eliminado_en=None
        ).order_by(Jornada.fecha_jornada.desc()).first()
        
        if not jornada_abierta:
            print("❌ No hay jornada abierta")
            return
        
        print(f"✅ Jornada encontrada: {jornada_abierta.fecha_jornada} (ID: {jornada_abierta.id})")
        print(f"   Abierta en: {jornada_abierta.abierto_en}")
        
        # Buscar TODAS las ventas del turno (incluyendo canceladas)
        if jornada_abierta.abierto_en:
            opened_dt = jornada_abierta.abierto_en
            if opened_dt.tzinfo:
                opened_dt = opened_dt.replace(tzinfo=None)
            
            ventas_turno = PosSale.query.filter(
                PosSale.created_at >= opened_dt
            ).all()
        else:
            # Si no hay fecha de apertura, usar jornada_id
            ventas_turno = PosSale.query.filter_by(
                jornada_id=jornada_abierta.id
            ).all()
        
        if not ventas_turno:
            print("✅ No hay ventas en el turno actual")
            return
        
        print(f"\n📊 Encontradas {len(ventas_turno)} ventas en el turno:")
        total_monto = 0.0
        canceladas = 0
        for v in ventas_turno:
            estado = "CANCELADA" if v.is_cancelled else "ACTIVA"
            print(f"  - ID: {v.id}, Empleado: {v.employee_name}, Caja: {v.register_name}, Total: ${v.total_amount}, Estado: {estado}, Fecha: {v.created_at}")
            total_monto += float(v.total_amount or 0)
            if v.is_cancelled:
                canceladas += 1
        
        print(f"\n💰 Total: ${total_monto:,.0f}")
        print(f"📋 Resumen: {len(ventas_turno) - canceladas} activas, {canceladas} canceladas")
        print(f"\n⚠️  ADVERTENCIA: Se ELIMINARÁN COMPLETAMENTE {len(ventas_turno)} ventas de la base de datos")
        print(f"   (Los items asociados se eliminarán automáticamente por cascade)")
        
        if not auto_confirm:
            respuesta = input("\n¿Deseas ELIMINAR todas estas ventas? (escribe 'ELIMINAR' para confirmar): ").strip()
            if respuesta != 'ELIMINAR':
                print("❌ Operación cancelada")
                return
        
        # Si llegamos aquí, es porque auto_confirm=True o el usuario confirmó
        # Primero, eliminar registros relacionados que tienen foreign keys a las ventas
        ventas_ids = [v.id for v in ventas_turno]
        ventas_sale_ids_str = [f"BMB-{v.id:06d}" for v in ventas_turno if v.id]
        
        # 1. Eliminar TicketEntrega por sale_id (Integer FK a pos_sales.id)
        deleted_tickets = 0
        for v in ventas_turno:
            tickets = TicketEntrega.query.filter_by(sale_id=v.id).all()
            for ticket in tickets:
                db.session.delete(ticket)
                deleted_tickets += 1
        
        # 2. Eliminar SaleDeliveryStatus (usa sale_id como string, tipo "BMB-000001")
        deleted_delivery_status = 0
        for sale_id_str in ventas_sale_ids_str:
            delivery_status = SaleDeliveryStatus.query.filter_by(sale_id=sale_id_str).first()
            if delivery_status:
                db.session.delete(delivery_status)
                deleted_delivery_status += 1
        
        # 3. Eliminar DeliveryItem por sale_id (string)
        deleted_delivery_items = 0
        for sale_id_str in ventas_sale_ids_str:
            items = DeliveryItem.query.filter_by(sale_id=sale_id_str).all()
            for item in items:
                db.session.delete(item)
                deleted_delivery_items += 1
        
        if deleted_delivery_status > 0 or deleted_delivery_items > 0 or deleted_tickets > 0:
            print(f"\n🧹 Eliminando registros relacionados...")
            print(f"   - SaleDeliveryStatus: {deleted_delivery_status}")
            print(f"   - DeliveryItem: {deleted_delivery_items}")
            print(f"   - TicketEntrega: {deleted_tickets}")
            db.session.flush()  # Flush para asegurar que se eliminen antes de las ventas
        
        # 4. Ahora eliminar las ventas (los items se eliminarán por cascade)
        for v in ventas_turno:
            db.session.delete(v)
            print(f"  ✓ Eliminada: {v.id}")
        
        db.session.commit()
        print(f"\n✅ {len(ventas_turno)} ventas eliminadas completamente de la base de datos")
        print(f"💰 Monto total eliminado: ${total_monto:,.0f}")

if __name__ == '__main__':
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    limpiar_ventas_turno(auto_confirm=auto_confirm)

