"""
Migración: Crear tablas de Tickets de Entrega con QR
FASE 1: Ticket QR al emitir venta
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models import db
from sqlalchemy import text, inspect

def migrate_ticket_entrega():
    """Ejecuta la migración para crear tablas de tickets de entrega"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🚀 MIGRACIÓN: TICKETS DE ENTREGA CON QR")
        print("=" * 60)
        
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # ==========================================
        # 1. Crear tabla ticket_entregas
        # ==========================================
        print("\n📋 1. Creando tabla ticket_entregas...")
        if 'ticket_entregas' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE ticket_entregas (
                        id SERIAL PRIMARY KEY,
                        display_code VARCHAR(50) UNIQUE NOT NULL,
                        qr_token VARCHAR(64) UNIQUE NOT NULL,
                        sale_id INTEGER NOT NULL UNIQUE REFERENCES pos_sales(id),
                        jornada_id INTEGER NOT NULL REFERENCES jornadas(id),
                        shift_date VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        created_by_employee_id VARCHAR(50) NOT NULL,
                        created_by_employee_name VARCHAR(200) NOT NULL,
                        register_id VARCHAR(50) NOT NULL,
                        delivered_at TIMESTAMP,
                        delivered_by VARCHAR(200),
                        hash_integridad VARCHAR(64)
                    )
                """))
                
                # Índices
                connection.execute(text("CREATE INDEX idx_ticket_entrega_display_code ON ticket_entregas(display_code)"))
                connection.execute(text("CREATE INDEX idx_ticket_entrega_qr_token ON ticket_entregas(qr_token)"))
                connection.execute(text("CREATE INDEX idx_ticket_entrega_sale_id ON ticket_entregas(sale_id)"))
                connection.execute(text("CREATE INDEX idx_ticket_entrega_status ON ticket_entregas(status, created_at)"))
                connection.execute(text("CREATE INDEX idx_ticket_entrega_jornada ON ticket_entregas(jornada_id, shift_date)"))
                
                connection.commit()
            print("✅ Tabla ticket_entregas creada")
        else:
            print("⏭️  Tabla ticket_entregas ya existe")
        
        # ==========================================
        # 2. Crear tabla ticket_entrega_items
        # ==========================================
        print("\n📋 2. Creando tabla ticket_entrega_items...")
        if 'ticket_entrega_items' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE ticket_entrega_items (
                        id SERIAL PRIMARY KEY,
                        ticket_id INTEGER NOT NULL REFERENCES ticket_entregas(id) ON DELETE CASCADE,
                        product_id VARCHAR(50) NOT NULL,
                        product_name VARCHAR(200) NOT NULL,
                        qty INTEGER NOT NULL,
                        delivered_qty INTEGER NOT NULL DEFAULT 0,
                        status VARCHAR(20) NOT NULL DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        delivered_at TIMESTAMP
                    )
                """))
                
                # Índices
                connection.execute(text("CREATE INDEX idx_ticket_item_ticket_id ON ticket_entrega_items(ticket_id)"))
                connection.execute(text("CREATE INDEX idx_ticket_item_ticket_status ON ticket_entrega_items(ticket_id, status)"))
                connection.execute(text("CREATE INDEX idx_ticket_item_product ON ticket_entrega_items(product_id, ticket_id)"))
                
                connection.commit()
            print("✅ Tabla ticket_entrega_items creada")
        else:
            print("⏭️  Tabla ticket_entrega_items ya existe")
        
        # ==========================================
        # 3. Crear tabla delivery_logs
        # ==========================================
        print("\n📋 3. Creando tabla delivery_logs...")
        if 'delivery_logs' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE delivery_logs (
                        id SERIAL PRIMARY KEY,
                        ticket_id INTEGER REFERENCES ticket_entregas(id),
                        item_id INTEGER REFERENCES ticket_entrega_items(id),
                        action VARCHAR(20) NOT NULL,
                        bartender_user_id VARCHAR(100),
                        bartender_name VARCHAR(200),
                        scanner_device_id VARCHAR(100),
                        qty INTEGER,
                        product_name VARCHAR(200),
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                """))
                
                # Índices
                connection.execute(text("CREATE INDEX idx_delivery_log_ticket_id ON delivery_logs(ticket_id)"))
                connection.execute(text("CREATE INDEX idx_delivery_log_item_id ON delivery_logs(item_id)"))
                connection.execute(text("CREATE INDEX idx_delivery_log_action_date ON delivery_logs(action, created_at)"))
                connection.execute(text("CREATE INDEX idx_delivery_log_bartender_date ON delivery_logs(bartender_user_id, created_at)"))
                connection.execute(text("CREATE INDEX idx_delivery_log_scanner ON delivery_logs(scanner_device_id)"))
                
                connection.commit()
            print("✅ Tabla delivery_logs creada")
        else:
            print("⏭️  Tabla delivery_logs ya existe")
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 60)

if __name__ == '__main__':
    migrate_ticket_entrega()











