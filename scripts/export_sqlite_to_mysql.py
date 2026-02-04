#!/usr/bin/env python3
"""
Exporta la base SQLite local a un archivo .sql compatible con MySQL.
Para subir solo la BD a cPanel: importa este archivo en phpMyAdmin.

Uso:
  python3 scripts/export_sqlite_to_mysql.py [--output archivo.sql]

Requisitos en cPanel:
  1. Crear base MySQL y usuario en cPanel (MySQL Databases).
  2. Crear las tablas vacías (ej. ejecutar la app una vez con DATABASE_URL=mysql://...
     y que haga create_all, o importar antes un schema si lo tienes).
  3. En phpMyAdmin: Importar este .sql (solo datos; opción "INSERT").
"""

import os
import sys
import sqlite3
import argparse
from datetime import date, datetime

# Raíz del proyecto
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(ROOT, "instance", "bimba.db")

# Orden de tablas para respetar FKs (padres antes que hijos). Las que no estén se añaden al final.
TABLE_ORDER = [
    "cargos",
    "cargo_salary_configs",
    "ingredient_categories",
    "ingredients",
    "products",
    "recipes",
    "recipe_ingredients",
    "ingredient_stocks",
    "employees",
    "shifts",
    "jornadas",
    "planilla_trabajadores",
    "pos_registers",
    "register_sessions",
    "pos_sales",
    "pos_sale_items",
    "register_closes",
    "register_locks",
    "deliveries",
    "inventory_items",
    "system_config",
]


def escape_mysql(value):
    """Escapa un valor para INSERT MySQL."""
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return "'{}'".format(value.strftime("%Y-%m-%d %H:%M:%S").replace("'", "''"))
    s = str(value).replace("\\", "\\\\").replace("'", "''").replace("\r", "\\r").replace("\n", "\\n")
    return "'{}'".format(s)


def export_sqlite_to_mysql(sqlite_path: str, output_path: str) -> None:
    if not os.path.exists(sqlite_path):
        print("No se encontró SQLite en:", sqlite_path)
        sys.exit(1)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    all_tables = [row[0] for row in cur.fetchall()]

    # Ordenar: primero TABLE_ORDER (solo las que existan), luego el resto
    ordered = [t for t in TABLE_ORDER if t in all_tables]
    rest = [t for t in all_tables if t not in TABLE_ORDER]
    tables = ordered + rest

    lines = [
        "-- Exportado desde SQLite para MySQL (solo datos)",
        "-- Importar en phpMyAdmin después de tener las tablas creadas.",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
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
            print("Saltando tabla {}: {}".format(table, e))
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

    lines.append("SET FOREIGN_KEY_CHECKS = 1;")
    conn.close()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Guardado: {}".format(output_path))
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Exportar SQLite local a .sql para MySQL (cPanel)")
    parser.add_argument(
        "--output", "-o",
        default=os.path.join(ROOT, "backups", "bimba_export_mysql.sql"),
        help="Archivo .sql de salida",
    )
    parser.add_argument(
        "--db",
        default=SQLITE_PATH,
        help="Ruta a instance/bimba.db",
    )
    args = parser.parse_args()

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    print("Exportando {} -> {}".format(args.db, args.output))
    export_sqlite_to_mysql(args.db, args.output)
    print("Listo. Sube el .sql a cPanel y impórtalo en phpMyAdmin (después de crear las tablas).")


if __name__ == "__main__":
    main()
