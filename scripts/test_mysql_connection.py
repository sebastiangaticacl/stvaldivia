#!/usr/bin/env python3
"""
Prueba la conexión a MySQL (DATABASE_URL en .env).
Uso: python3 scripts/test_mysql_connection.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

url = os.environ.get("DATABASE_URL", "")
if not url or "mysql" not in url:
    print("❌ DATABASE_URL no configurado o no es MySQL en .env")
    sys.exit(1)

# Ocultar contraseña al mostrar
safe = url
if "@" in url and ":" in url:
    try:
        pre, post = url.rsplit("@", 1)
        user_part = pre.split("//", 1)[-1]
        if ":" in user_part:
            user = user_part.split(":")[0]
            safe = url.replace(user_part, f"{user}:****", 1)
    except Exception:
        pass
print("Probando:", safe)
print()

try:
    from sqlalchemy import create_engine, text
    engine = create_engine(url, connect_args={"connect_timeout": 10})
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Conexión a MySQL correcta")
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM products"))
        n = r.scalar()
    print(f"✅ Tabla products: {n} filas")
except Exception as e:
    print("❌ Error:", type(e).__name__, str(e))
    if "2003" in str(e) or "Can't connect" in str(e):
        print()
        print("Suele pasar si el hosting bloquea el puerto 3306 desde internet.")
        print("Opciones: 1) cPanel > Remote MySQL: agregar tu IP. 2) Usar túnel SSH.")
    sys.exit(1)
