"""
Migración: Crear tablas de Tickets QR de Guardarropía
FASE 3: Ticket QR para guardarropía
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

def migrate_guardarropia_ticket():
    """Ejecuta la migración para crear tablas de tickets QR de guardarropía"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🚀 MIGRACIÓN: TICKETS QR DE GUARDARROPÍA")
        print("=" * 60)
        
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # ==========================================
        # 1. Crear tabla guardarropia_tickets
        # ==========================================
        print("\n📋 1. Creando tabla guardarropia_tickets...")
        if 'guardarropia_tickets' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE guardarropia_tickets (
                        id SERIAL PRIMARY KEY,
                        display_code VARCHAR(50) UNIQUE NOT NULL,
                        qr_token VARCHAR(64) UNIQUE NOT NULL,
                        item_id INTEGER NOT NULL UNIQUE REFERENCES guardarropia_items(id),
                        jornada_id INTEGER REFERENCES jornadas(id),
                        shift_date VARCHAR(50),
                        status VARCHAR(20) NOT NULL DEFAULT 'open',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        created_by_user_id VARCHAR(100) NOT NULL,
                        created_by_user_name VARCHAR(200) NOT NULL,
                        paid_at TIMESTAMP,
                        paid_by VARCHAR(200),
                        price NUMERIC(10, 2),
                        payment_type VARCHAR(20),
                        checked_out_at TIMESTAMP,
                        checked_out_by VARCHAR(200),
                        hash_integridad VARCHAR(64)
                    )
                """))
                
                # Índices (con verificación de existencia usando IF NOT EXISTS)
                try:
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_ticket_display_code ON guardarropia_tickets(display_code)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_ticket_qr_token ON guardarropia_tickets(qr_token)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_ticket_item_id ON guardarropia_tickets(item_id)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_ticket_status ON guardarropia_tickets(status, created_at)"))
                except Exception as e:
                    # Si falla, los índices probablemente ya existen
                    print(f"  ⚠️  Algunos índices ya existen (esto es normal): {e}")
                
                connection.commit()
            print("✅ Tabla guardarropia_tickets creada")
        else:
            print("⏭️  Tabla guardarropia_tickets ya existe")
        
        # ==========================================
        # 2. Crear tabla guardarropia_ticket_logs
        # ==========================================
        print("\n📋 2. Creando tabla guardarropia_ticket_logs...")
        if 'guardarropia_ticket_logs' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE guardarropia_ticket_logs (
                        id SERIAL PRIMARY KEY,
                        ticket_id INTEGER NOT NULL REFERENCES guardarropia_tickets(id) ON DELETE CASCADE,
                        action VARCHAR(20) NOT NULL,
                        actor_user_id VARCHAR(100),
                        actor_name VARCHAR(200),
                        notes TEXT,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                """))
                
                # Índices (con verificación de existencia usando IF NOT EXISTS)
                try:
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_log_ticket_id ON guardarropia_ticket_logs(ticket_id)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_log_action_date ON guardarropia_ticket_logs(action, created_at)"))
                    connection.execute(text("CREATE INDEX IF NOT EXISTS idx_guardarropia_log_actor_date ON guardarropia_ticket_logs(actor_user_id, created_at)"))
                except Exception as e:
                    # Si falla, los índices probablemente ya existen
                    print(f"  ⚠️  Algunos índices ya existen (esto es normal): {e}")
                
                connection.commit()
            print("✅ Tabla guardarropia_ticket_logs creada")
        else:
            print("⏭️  Tabla guardarropia_ticket_logs ya existe")
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN COMPLETADA")
        print("=" * 60)

if __name__ == '__main__':
    migrate_guardarropia_ticket()

