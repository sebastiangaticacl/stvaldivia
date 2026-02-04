#!/usr/bin/env python3
"""
Genera un único .sql con TODO: esquema MySQL (CREATE TABLE) + datos (INSERT).
Para subir solo la BD a cPanel: crea la base en MySQL, luego importa este archivo en phpMyAdmin.

Uso:
  python3 scripts/export_sqlite_to_mysql_full.py [--output archivo.sql]

Requisitos:
  - pip install mysql-connector-python  (o pymysql) para el dialecto MySQL al generar DDL.
"""

import os
import sys
import sqlite3
import argparse
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(ROOT, "instance", "bimba.db")

TABLE_ORDER = [
    "cargos", "cargo_salary_configs", "ingredient_categories", "ingredients",
    "products", "recipes", "recipe_ingredients", "ingredient_stocks",
    "employees", "shifts", "jornadas", "planilla_trabajadores",
    "pos_registers", "register_sessions", "pos_sales", "pos_sale_items",
    "register_closes", "register_locks", "deliveries", "inventory_items",
    "system_config",
]


def escape_mysql(value):
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return "'{}'".format(value.strftime("%Y-%m-%d %H:%M:%S").replace("'", "''"))
    s = str(value).replace("\\", "\\\\").replace("'", "''").replace("\r", "\\r").replace("\n", "\\n")
    return "'{}'".format(s)


def generate_mysql_schema():
    """Genera CREATE TABLE para MySQL desde los modelos de la app."""
    sys.path.insert(0, ROOT)
    from app import create_app
    from app.models import db
    from sqlalchemy import create_engine
    from sqlalchemy.schema import CreateTable

    app = create_app()
    with app.app_context():
        # Motor MySQL solo para compilar DDL (no se conecta si solo compilamos)
        try:
            engine = create_engine("mysql+mysqlconnector://dummy:dummy@127.0.0.1/dummy")
        except Exception:
            try:
                engine = create_engine("mysql+pymysql://dummy:dummy@127.0.0.1/dummy")
            except Exception as e:
                print("Necesitas mysql-connector-python o pymysql: pip install mysql-connector-python")
                raise SystemExit(1) from e

        lines = []
        for table in db.metadata.sorted_tables:
            try:
                # SQLAlchemy 2.x: CreateTable(..., if_not_exists=True)
                ddl = CreateTable(table, if_not_exists=True).compile(engine)
                lines.append(str(ddl) + ";")
                lines.append("")
            except Exception as e:
                print("  Advertencia: no se pudo generar DDL para {}: {}".format(table.name, e))
        return "\n".join(lines)


def export_sqlite_data(sqlite_path: str):
    """Exporta datos de SQLite a listas de líneas SQL (INSERT)."""
    if not os.path.exists(sqlite_path):
        return []

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    all_tables = [row[0] for row in cur.fetchall()]
    ordered = [t for t in TABLE_ORDER if t in all_tables]
    rest = [t for t in all_tables if t not in TABLE_ORDER]
    tables = ordered + rest

    lines = [
        "",
        "-- ========== DATOS (exportados desde SQLite) ==========",
        "",
    ]

    for table in tables:
        cur.execute("PRAGMA table_info({})".format(table))
        columns = [row[1] for row in cur.fetchall()]
        if not columns:
            continue
        try:
            cur.execute("SELECT * FROM {}".format(table))
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            print("  Saltando tabla {}: {}".format(table, e))
            continue
        if not rows:
            continue

        num_rows = len(rows)
        cols_str = ", ".join("`{}`".format(c) for c in columns)
        lines.append("-- Tabla: {}".format(table))
        lines.append("DELETE FROM `{}`;".format(table))

        batch = []
        for row in rows:
            values = [escape_mysql(row[c]) for c in columns]
            batch.append("({})".format(", ".join(values)))
            if len(batch) >= 100:
                lines.append("INSERT INTO `{}` ({}) VALUES\n{};".format(table, cols_str, ",\n".join(batch)))
                batch = []
        if batch:
            lines.append("INSERT INTO `{}` ({}) VALUES\n{};".format(table, cols_str, ",\n".join(batch)))
        lines.append("")
        print("  {}: {} filas".format(table, num_rows))

    conn.close()
    return lines


def main():
    parser = argparse.ArgumentParser(description="Exportar SQLite a .sql completo (esquema + datos) para MySQL")
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(ROOT, "backups", "bimba_mysql_completo.sql"),
        help="Archivo .sql de salida",
    )
    parser.add_argument("--db", default=SQLITE_PATH, help="Ruta a instance/bimba.db")
    parser.add_argument("--solo-datos", action="store_true", help="Solo INSERT (sin CREATE TABLE)")
    args = parser.parse_args()

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    header = [
        "-- BIMBA: exportación completa para MySQL (cPanel)",
        "-- 1. Crear base y usuario en cPanel > MySQL Databases",
        "-- 2. En phpMyAdmin, seleccionar la base e Importar este archivo",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]

    if not args.solo_datos:
        print("Generando esquema MySQL (CREATE TABLE)...")
        schema = generate_mysql_schema()
        body = "\n".join(header) + "\n\n-- ========== ESQUEMA (tablas) ==========\n\n" + schema + "\n"
    else:
        body = "\n".join(header)

    print("Exportando datos desde {}...".format(args.db))
    data_lines = export_sqlite_data(args.db)
    body += "\n".join(data_lines)
    body += "SET FOREIGN_KEY_CHECKS = 1;\n"

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(body)

    print("Guardado: {}".format(args.output))
    print("Listo. Sube este archivo a cPanel > phpMyAdmin > Importar.")


if __name__ == "__main__":
    main()
