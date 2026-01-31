"""
Migración P0: Hardening del POS
Agrega tablas y columnas necesarias para los hallazgos P0
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
from app import CHILE_TZ

def migrate_p0_hardening():
    """Ejecuta la migración P0"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("🚀 MIGRACIÓN P0: HARDENING DEL POS")
        print("=" * 60)
        
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        # ==========================================
        # 1. Crear tabla register_sessions (P0-001, P0-003, P0-010)
        # ==========================================
        print("\n📋 1. Creando tabla register_sessions...")
        if 'register_sessions' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE register_sessions (
                        id SERIAL PRIMARY KEY,
                        register_id VARCHAR(50) NOT NULL,
                        opened_by_employee_id VARCHAR(50) NOT NULL,
                        opened_by_employee_name VARCHAR(200) NOT NULL,
                        opened_at TIMESTAMP NOT NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                        shift_date VARCHAR(50) NOT NULL,
                        jornada_id INTEGER NOT NULL REFERENCES jornadas(id),
                        initial_cash NUMERIC(10, 2),
                        closed_at TIMESTAMP,
                        closed_by VARCHAR(200),
                        idempotency_key_open VARCHAR(64) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Índices
                connection.execute(text("CREATE INDEX idx_register_sessions_register_id ON register_sessions(register_id)"))
                connection.execute(text("CREATE INDEX idx_register_sessions_status ON register_sessions(status)"))
                connection.execute(text("CREATE INDEX idx_register_sessions_jornada_id ON register_sessions(jornada_id)"))
                connection.execute(text("CREATE INDEX idx_register_sessions_shift_date ON register_sessions(shift_date)"))
                connection.execute(text("CREATE INDEX idx_register_sessions_register_status ON register_sessions(register_id, status)"))
                connection.execute(text("CREATE INDEX idx_register_sessions_idempotency ON register_sessions(idempotency_key_open)"))
                
                connection.commit()
            print("✅ Tabla register_sessions creada")
        else:
            print("⏭️  Tabla register_sessions ya existe")
        
        # ==========================================
        # 2. Crear tabla sale_audit_logs (P0-013, P0-014, P1-016)
        # ==========================================
        print("\n📋 2. Creando tabla sale_audit_logs...")
        if 'sale_audit_logs' not in existing_tables:
            with db.engine.connect() as connection:
                connection.execute(text("""
                    CREATE TABLE sale_audit_logs (
                        id SERIAL PRIMARY KEY,
                        event_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL DEFAULT 'info',
                        actor_user_id VARCHAR(50),
                        actor_name VARCHAR(200) NOT NULL,
                        register_id VARCHAR(50),
                        sale_id INTEGER REFERENCES pos_sales(id),
                        jornada_id INTEGER REFERENCES jornadas(id),
                        register_session_id INTEGER REFERENCES register_sessions(id),
                        payload_json TEXT,
                        ip_address VARCHAR(45),
                        session_id VARCHAR(200),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Índices
                connection.execute(text("CREATE INDEX idx_audit_log_event_type ON sale_audit_logs(event_type, created_at)"))
                connection.execute(text("CREATE INDEX idx_audit_log_register ON sale_audit_logs(register_id, created_at)"))
                connection.execute(text("CREATE INDEX idx_audit_log_severity ON sale_audit_logs(severity, created_at)"))
                connection.execute(text("CREATE INDEX idx_audit_log_sale_id ON sale_audit_logs(sale_id)"))
                connection.execute(text("CREATE INDEX idx_audit_log_jornada_id ON sale_audit_logs(jornada_id)"))
                connection.execute(text("CREATE INDEX idx_audit_log_actor_user_id ON sale_audit_logs(actor_user_id)"))
                
                connection.commit()
            print("✅ Tabla sale_audit_logs creada")
        else:
            print("⏭️  Tabla sale_audit_logs ya existe")
        
        # ==========================================
        # 3. Agregar columnas a pos_sales (P0-004, P0-007, P0-008, P0-016)
        # ==========================================
        print("\n📋 3. Agregando columnas a pos_sales...")
        if 'pos_sales' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('pos_sales')]
            
            # jornada_id (P0-004)
            if 'jornada_id' not in columns:
                print("  ➕ Agregando jornada_id...")
                with db.engine.connect() as connection:
                    # Primero agregar columna nullable
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN jornada_id INTEGER"))
                    # Crear índice
                    connection.execute(text("CREATE INDEX idx_pos_sales_jornada_id ON pos_sales(jornada_id)"))
                    # Agregar foreign key
                    connection.execute(text("ALTER TABLE pos_sales ADD CONSTRAINT fk_pos_sales_jornada FOREIGN KEY (jornada_id) REFERENCES jornadas(id)"))
                    # Para datos existentes, intentar asociar con jornada activa
                    connection.execute(text("""
                        UPDATE pos_sales 
                        SET jornada_id = (
                            SELECT id FROM jornadas 
                            WHERE jornadas.fecha_jornada = pos_sales.shift_date 
                            AND jornadas.estado_apertura = 'abierto'
                            LIMIT 1
                        )
                        WHERE jornada_id IS NULL AND shift_date IS NOT NULL
                    """))
                    # Si no hay jornada, usar una jornada por defecto o dejar NULL temporalmente
                    # Por ahora, dejamos NULL para ventas sin jornada (se validará en código)
                    connection.commit()
                print("  ✅ jornada_id agregado")
            else:
                print("  ⏭️  jornada_id ya existe")
            
            # shift_date: cambiar a NOT NULL (P0-004)
            # Nota: Esto puede fallar si hay ventas con shift_date NULL
            # Por ahora, solo agregamos la columna si no existe y validamos en código
            
            # no_revenue (P0-016)
            if 'no_revenue' not in columns:
                print("  ➕ Agregando no_revenue...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN no_revenue BOOLEAN DEFAULT FALSE NOT NULL"))
                    connection.execute(text("CREATE INDEX idx_pos_sales_no_revenue ON pos_sales(no_revenue, is_courtesy, is_test)"))
                    # Marcar ventas de caja SUPERADMIN como no_revenue
                    connection.execute(text("""
                        UPDATE pos_sales 
                        SET no_revenue = TRUE 
                        WHERE register_id IN (
                            SELECT code FROM pos_registers WHERE superadmin_only = TRUE
                        )
                    """))
                    connection.commit()
                print("  ✅ no_revenue agregado")
            else:
                print("  ⏭️  no_revenue ya existe")
            
            # idempotency_key (P0-007)
            if 'idempotency_key' not in columns:
                print("  ➕ Agregando idempotency_key...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN idempotency_key VARCHAR(64) UNIQUE"))
                    connection.execute(text("CREATE INDEX idx_pos_sales_idempotency_key ON pos_sales(idempotency_key)"))
                    connection.commit()
                print("  ✅ idempotency_key agregado")
            else:
                print("  ⏭️  idempotency_key ya existe")
            
            # Campos de cancelación (P0-008)
            if 'is_cancelled' not in columns:
                print("  ➕ Agregando campos de cancelación...")
                with db.engine.connect() as connection:
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN is_cancelled BOOLEAN DEFAULT FALSE NOT NULL"))
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN cancelled_at TIMESTAMP"))
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN cancelled_by VARCHAR(200)"))
                    connection.execute(text("ALTER TABLE pos_sales ADD COLUMN cancelled_reason TEXT"))
                    connection.execute(text("CREATE INDEX idx_pos_sales_is_cancelled ON pos_sales(is_cancelled)"))
                    connection.commit()
                print("  ✅ Campos de cancelación agregados")
            else:
                print("  ⏭️  Campos de cancelación ya existen")
        else:
            print("⚠️  Tabla pos_sales no existe, omitiendo cambios")
        
        # ==========================================
        # 4. Agregar idempotency_key_close a register_closes (P0-011)
        # ==========================================
        print("\n📋 4. Agregando idempotency_key_close a register_closes...")
        if 'register_closes' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('register_closes')]
            if 'idempotency_key_close' not in columns:
                print("  ➕ Agregando idempotency_key_close...")
                with db.engine.connect() as connection:
                    # Agregar columna nullable primero
                    connection.execute(text("ALTER TABLE register_closes ADD COLUMN idempotency_key_close VARCHAR(64)"))
                    # Crear índice
                    connection.execute(text("CREATE INDEX idx_register_closes_idempotency ON register_closes(idempotency_key_close)"))
                    # Agregar constraint UNIQUE (puede fallar si hay duplicados, pero es aceptable)
                    try:
                        connection.execute(text("ALTER TABLE register_closes ADD CONSTRAINT uq_register_closes_idempotency UNIQUE (idempotency_key_close)"))
                    except Exception as e:
                        print(f"  ⚠️  No se pudo agregar constraint UNIQUE (puede haber duplicados): {e}")
                    connection.commit()
                print("  ✅ idempotency_key_close agregado")
            else:
                print("  ⏭️  idempotency_key_close ya existe")
        else:
            print("⚠️  Tabla register_closes no existe, omitiendo cambios")
        
        print("\n" + "=" * 60)
        print("✅ MIGRACIÓN P0 COMPLETADA")
        print("=" * 60)
        print("\n⚠️  IMPORTANTE:")
        print("  - Las ventas existentes con shift_date=NULL pueden necesitar actualización manual")
        print("  - Las ventas de caja SUPERADMIN han sido marcadas como no_revenue")
        print("  - Revisa los datos y ejecuta validaciones antes de usar en producción")
        print("=" * 60)

if __name__ == '__main__':
    migrate_p0_hardening()

