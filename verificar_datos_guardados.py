#!/usr/bin/env python3
"""
Script para verificar qué datos se están guardando en las tablas del servidor
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.ecommerce_models import Entrada, CheckoutSession
from app.models import db
from datetime import datetime

app = create_app()

with app.app_context():
    print("=" * 80)
    print("📊 VERIFICACIÓN DE DATOS GUARDADOS EN EL SERVIDOR")
    print("=" * 80)
    print()
    
    # 1. Verificar entradas (compras completadas)
    print("1️⃣  TABLA: entradas (Compras completadas)")
    print("-" * 80)
    entradas = Entrada.query.order_by(Entrada.created_at.desc()).limit(10).all()
    
    if entradas:
        print(f"   ✅ Total de entradas en la base de datos: {Entrada.query.count()}")
        print(f"   📋 Últimas {len(entradas)} entradas:\n")
        
        for entrada in entradas:
            print(f"   🎫 Ticket: {entrada.ticket_code}")
            print(f"      • Producto: {entrada.evento_nombre}")
            print(f"      • Comprador: {entrada.comprador_nombre}")
            print(f"      • Email: {entrada.comprador_email}")
            print(f"      • Teléfono: {entrada.comprador_telefono or 'N/A'}")
            print(f"      • RUT: {entrada.comprador_rut or 'N/A'}")
            print(f"      • Cantidad: {entrada.cantidad}")
            print(f"      • Precio unitario: ${entrada.precio_unitario:,.0f}")
            print(f"      • Precio total: ${entrada.precio_total:,.0f}")
            print(f"      • Estado: {entrada.estado_pago}")
            print(f"      • Método pago: {entrada.metodo_pago or 'N/A'}")
            print(f"      • Fecha creación: {entrada.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if entrada.paid_at:
                print(f"      • Fecha pago: {entrada.paid_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    else:
        print("   ⚠️  No hay entradas guardadas aún")
        print()
    
    # 2. Verificar sesiones de checkout
    print("2️⃣  TABLA: checkout_sessions (Sesiones de compra)")
    print("-" * 80)
    sessions = CheckoutSession.query.order_by(CheckoutSession.created_at.desc()).limit(10).all()
    
    if sessions:
        print(f"   ✅ Total de sesiones en la base de datos: {CheckoutSession.query.count()}")
        print(f"   📋 Últimas {len(sessions)} sesiones:\n")
        
        for session in sessions:
            print(f"   🛒 Sesión: {session.session_id}")
            print(f"      • Producto: {session.evento_nombre}")
            print(f"      • Comprador: {session.comprador_nombre or 'Pendiente'}")
            print(f"      • Email: {session.comprador_email or 'Pendiente'}")
            print(f"      • Cantidad: {session.cantidad}")
            print(f"      • Precio total: ${session.precio_total:,.0f}")
            print(f"      • Estado: {session.estado}")
            print(f"      • Fecha creación: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if session.completed_at:
                print(f"      • Fecha completada: {session.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if session.entrada_id:
                print(f"      • ✅ Vinculada a entrada ID: {session.entrada_id}")
            print()
    else:
        print("   ⚠️  No hay sesiones de checkout guardadas aún")
        print()
    
    # 3. Estadísticas
    print("3️⃣  ESTADÍSTICAS")
    print("-" * 80)
    total_entradas = Entrada.query.count()
    entradas_pagadas = Entrada.query.filter_by(estado_pago='pagado').count()
    entradas_pendientes = Entrada.query.filter_by(estado_pago='pendiente').count()
    
    from sqlalchemy import func
    total_recaudado = db.session.query(func.sum(Entrada.precio_total)).filter_by(estado_pago='pagado').scalar() or 0
    
    print(f"   📊 Total de entradas: {total_entradas}")
    print(f"   ✅ Entradas pagadas: {entradas_pagadas}")
    print(f"   ⏳ Entradas pendientes: {entradas_pendientes}")
    print(f"   💰 Total recaudado: ${float(total_recaudado):,.0f}")
    print()
    
    print("=" * 80)
    print("✅ VERIFICACIÓN COMPLETA")
    print("=" * 80)
    print()
    print("💡 Los datos se guardan automáticamente cuando:")
    print("   1. Un usuario completa el formulario en el landing page")
    print("   2. Se crea una sesión de checkout (tabla: checkout_sessions)")
    print("   3. Se completa la compra (tabla: entradas)")
    print()
    print("🔗 Para ver las compras en el admin:")
    print("   http://localhost:5000/admin/ecommerce/compras")
    print()


