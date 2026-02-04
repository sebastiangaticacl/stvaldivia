#!/usr/bin/env python3
"""
Seed de datos de prueba (LOCAL ONLY).

Uso:
  python3 scripts/seed_local_demo_data.py

Notas:
  - No conecta a nada externo (solo SQLite local).
  - Es idempotente: si ya hay datos, no duplica (usa lookups por claves únicas).
"""

import os
import sys
import json
import uuid
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Dict, Tuple, Any

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from app.helpers.seed_test_data import seed_test_register_and_product, seed_test_cashier_user
from app.helpers.timezone_utils import CHILE_TZ

from app.models.shift_models import Shift
from app.models.jornada_models import Jornada, PlanillaTrabajador
from app.models.product_models import Product
from app.models.inventory_models import InventoryItem
from app.models.cargo_models import Cargo
from app.models.cargo_salary_models import CargoSalaryConfig
from app.models.pos_models import PosRegister, RegisterSession, RegisterClose, RegisterLock, PosSale, PosSaleItem, Employee
from app.models.delivery_models import Delivery
from app.models.inventory_stock_models import (
    IngredientCategory,
    Ingredient as StockIngredient,
    IngredientStock,
    Recipe,
    RecipeIngredient,
)


def _env_flag(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _get_or_create_by(model, where: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None):
    obj = model.query.filter_by(**where).first()
    if obj:
        return obj, False
    obj = model(**where)
    if defaults:
        for k, v in defaults.items():
            setattr(obj, k, v)
    db.session.add(obj)
    db.session.flush()
    return obj, True


def seed_local_demo_data():
    # Seguridad: nunca seedear en producción
    flask_env = (os.environ.get("FLASK_ENV") or "").lower()
    if flask_env == "production":
        raise RuntimeError("Refusing to seed in production (FLASK_ENV=production).")

    # En este proyecto, LOCAL_ONLY suele ser true por defecto en local
    local_only = _env_flag("LOCAL_ONLY", True)
    if not local_only:
        raise RuntimeError("Refusing to seed when LOCAL_ONLY is not enabled.")

    today = date.today()
    today_str = today.isoformat()
    now_utc = datetime.utcnow()
    # Para que el "turno actual" tenga suficientes ventas y gráficos por hora:
    opened_at_utc = now_utc - timedelta(hours=6)

    print("🧪 Seedeando datos demo locales...")
    db.create_all()

    # =========================================================
    # Jornada ABIERTA + Shift abierto (lo mínimo para flujos POS)
    # =========================================================
    jornada = Jornada.query.filter_by(estado_apertura="abierto").order_by(Jornada.fecha_jornada.desc()).first()
    if not jornada:
        jornada = Jornada(
            fecha_jornada=today_str,
            tipo_turno="Noche",
            nombre_fiesta="DEMO - Noche de Prueba",
            horario_apertura_programado="22:00",
            horario_cierre_programado="05:00",
            horario_apertura_real=opened_at_utc,
            estado_apertura="abierto",
            djs="DJ Demo",
            barras_disponibles=json.dumps(["barra_principal", "terraza"]),
            abierto_en=opened_at_utc,
            abierto_por="seed_local_demo_data",
            responsable_cajas="Admin Demo",
            responsable_puerta="Puerta Demo",
            responsable_seguridad="Seguridad Demo",
            responsable_admin="Admin Demo",
        )
        db.session.add(jornada)
        db.session.flush()
        print(f"✅ Jornada creada (id={jornada.id})")
    else:
        print(f"✅ Jornada abierta existente (id={jornada.id})")

    shift, created_shift = _get_or_create_by(
        Shift,
        {"shift_date": today_str},
        {
            "is_open": True,
            "opened_by": "seed_local_demo_data",
            "opened_at": now_utc.isoformat(),
            "fiesta_nombre": jornada.nombre_fiesta,
            "djs": jornada.djs,
            "barras_disponibles": json.dumps(["barra_principal", "terraza"]),
            "bartenders": json.dumps(["Bartender Demo"]),
            "notes": "Turno demo generado automáticamente",
        },
    )
    if created_shift:
        print("✅ Shift creado y marcado como abierto")

    # =========================================================
    # Cargos + configuración de sueldos
    # =========================================================
    cargos_demo = [
        ("Cajero", "Operación de caja / TPV", 1, 50000, 0),
        ("Bartender", "Barra y preparación", 2, 60000, 5000),
        ("Seguridad", "Control y seguridad", 3, 55000, 0),
        ("Puerta", "Acceso y entradas", 4, 50000, 0),
        ("Admin", "Administración", 5, 70000, 0),
    ]
    for nombre, desc, orden, sueldo, bono in cargos_demo:
        cargo, _ = _get_or_create_by(Cargo, {"nombre": nombre}, {"descripcion": desc, "orden": orden, "activo": True})
        _get_or_create_by(
            CargoSalaryConfig,
            {"cargo": nombre},
            {"sueldo_por_turno": Decimal(str(sueldo)), "bono_fijo": Decimal(str(bono))},
        )
    print("✅ Cargos y sueldos listos")

    # =========================================================
    # Caja + producto test + usuario cajero test (helpers existentes)
    # =========================================================
    ok_reg, msg_reg, test_register, test_product = seed_test_register_and_product(db)
    if not ok_reg:
        raise RuntimeError(msg_reg)
    ok_emp, msg_emp, test_emp = seed_test_cashier_user(db)
    if not ok_emp:
        raise RuntimeError(msg_emp)
    print(f"✅ {msg_reg}")
    print(f"✅ {msg_emp}")

    # =========================================================
    # Cajas extra demo
    # =========================================================
    def ensure_register(code: str, name: str, location: str, tpv_type: str):
        reg = PosRegister.query.filter((PosRegister.code == code) | (PosRegister.name == name)).first()
        if reg:
            return reg, False
        reg = PosRegister(
            name=name,
            code=code,
            is_active=True,
            location=location,
            tpv_type=tpv_type,
            default_location=location,
            is_test=True,
            payment_methods=json.dumps(["cash", "debit", "credit"]),
            payment_provider_primary="GETNET",
            operational_status="active",
        )
        db.session.add(reg)
        db.session.flush()
        return reg, True

    caja_1, created = ensure_register("CAJA1", "Caja 1 (Demo)", "barra_principal", "barra")
    if created:
        print("✅ Caja demo creada: CAJA1")
    puerta_1, created = ensure_register("PUERTA1", "Puerta 1 (Demo)", "puerta", "puerta")
    if created:
        print("✅ Caja demo creada: PUERTA1")

    # =========================================================
    # Empleados demo (además del TEST0000)
    # =========================================================
    demo_employees = [
        ("1", "Camila", "Cajera", "Camila Demo", "Cajero", True, False, "1234"),
        ("2", "Diego", "Barra", "Diego Demo", "Bartender", False, True, "2222"),
        ("3", "Sofía", "Puerta", "Sofía Demo", "Puerta", False, False, "3333"),
    ]
    for emp_id, first, last, full, cargo, is_cashier, is_bartender, pin in demo_employees:
        emp = Employee.query.get(emp_id)
        if not emp:
            emp = Employee(id=emp_id, name=full)
            db.session.add(emp)
        emp.first_name = first
        emp.last_name = last
        emp.name = full
        emp.cargo = cargo
        emp.is_cashier = bool(is_cashier)
        emp.is_bartender = bool(is_bartender)
        emp.is_active = True
        emp.deleted = "0"
        emp.synced_from_phppos = False
        emp.pin = pin
    db.session.flush()
    print("✅ Empleados demo listos")

    # =========================================================
    # Planilla (para que aparezcan en algunos flujos)
    # =========================================================
    def ensure_planilla(emp_id: str, emp_name: str, rol: str, area: str):
        plan = PlanillaTrabajador.query.filter_by(jornada_id=jornada.id, id_empleado=str(emp_id)).first()
        if plan:
            return plan, False
        plan = PlanillaTrabajador(
            jornada_id=jornada.id,
            id_empleado=str(emp_id),
            nombre_empleado=emp_name,
            rol=rol,
            hora_inicio="22:00",
            hora_fin="05:00",
            costo_hora=0.0,
            costo_total=0.0,
            area=area,
            origen="seed",
        )
        db.session.add(plan)
        db.session.flush()
        # Intentar congelar pago si hay config (no bloquea si falla)
        try:
            plan.calcular_y_congelar_pago(cargo_nombre=rol.capitalize())
        except Exception:
            pass
        return plan, True

    ensure_planilla("TEST0000", "Usuario Test", "cajero", "caja")
    ensure_planilla("1", "Camila Demo", "cajero", "caja")
    ensure_planilla("2", "Diego Demo", "bartender", "barra_principal")
    ensure_planilla("3", "Sofía Demo", "puerta", "puerta")
    print("✅ Planilla demo lista")

    # =========================================================
    # Productos demo (inventario propio)
    # =========================================================
    products_demo = [
        ("PISCO SOUR", "Coctelería", 5500, 1800, 120, 10, True),
        ("MOJITO", "Coctelería", 6000, 1900, 90, 10, True),
        ("GIN TONIC", "Coctelería", 7000, 2200, 80, 10, True),
        ("VODKA TONIC", "Coctelería", 6500, 2100, 80, 10, True),
        ("RAMAZZOTTI", "Coctelería", 6500, 2000, 60, 10, False),
        ("CERVEZA LATA", "Bebidas", 3500, 1200, 300, 20, False),
        ("CERVEZA SCHOP", "Bebidas", 4500, 1500, 200, 20, False),
        ("AGUA MINERAL", "Bebidas", 1500, 400, 200, 20, False),
        ("BEBIDA", "Bebidas", 2500, 600, 200, 20, False),
        ("ENERGÉTICA", "Bebidas", 3500, 1200, 120, 10, False),
        ("SHOT TEQUILA", "Shots", 4000, 1400, 120, 10, False),
        ("SHOT PISCO", "Shots", 3500, 1200, 120, 10, False),
        ("SNACK PAPAS", "Snacks", 2000, 700, 80, 10, False),
        ("SNACK MANÍ", "Snacks", 1500, 400, 80, 10, False),
        ("ENTRADA GENERAL", "Entradas", 10000, 0, 9999, 0, False),
        ("ENTRADA VIP", "Entradas", 20000, 0, 9999, 0, False),
        ("ENTRADA 2x1", "Entradas", 15000, 0, 9999, 0, False),
    ]
    created_products = 0
    product_by_name: dict[str, Product] = {}
    for name, cat, price, cost, stock, stock_min, is_kit in products_demo:
        p = Product.query.filter_by(name=name).first()
        if not p:
            p = Product(name=name)
            db.session.add(p)
            created_products += 1
        p.category = cat
        p.price = int(price)
        p.cost_price = int(cost)
        p.stock_quantity = int(stock)
        p.stock_minimum = int(stock_min)
        p.is_active = True
        p.is_kit = bool(is_kit)
        p.is_test = True  # demo/local
        product_by_name[name] = p
    db.session.flush()
    print(f"✅ Productos demo listos (+{created_products} creados)")

    # =========================================================
    # Ingredientes + stock + receta para un kit (PISCO SOUR)
    # =========================================================
    cat_dest, _ = _get_or_create_by(IngredientCategory, {"name": "Destilados"}, {"description": "Destilados base"})
    cat_mix, _ = _get_or_create_by(IngredientCategory, {"name": "Mixers"}, {"description": "Jugos y mixers"})
    cat_ins, _ = _get_or_create_by(IngredientCategory, {"name": "Insumos"}, {"description": "Jarabes y otros"})

    ing_pisco, _ = _get_or_create_by(
        StockIngredient,
        {"name": "Pisco"},
        {"category_id": cat_dest.id, "base_unit": "ml", "package_size": Decimal("1000"), "package_unit": "botella", "cost_per_unit": Decimal("1.5")},
    )
    ing_limon, _ = _get_or_create_by(
        StockIngredient,
        {"name": "Jugo de Limón"},
        {"category_id": cat_mix.id, "base_unit": "ml", "package_size": None, "package_unit": None, "cost_per_unit": Decimal("0.8")},
    )
    ing_jarabe, _ = _get_or_create_by(
        StockIngredient,
        {"name": "Jarabe Simple"},
        {"category_id": cat_ins.id, "base_unit": "ml", "package_size": Decimal("1000"), "package_unit": "botella", "cost_per_unit": Decimal("0.3")},
    )

    def ensure_stock(ing_id: int, location: str, qty: str):
        stock = IngredientStock.query.filter_by(ingredient_id=ing_id, location=location).first()
        if stock:
            return stock, False
        stock = IngredientStock(ingredient_id=ing_id, location=location, quantity=Decimal(qty))
        db.session.add(stock)
        db.session.flush()
        return stock, True

    ensure_stock(ing_pisco.id, "bodega", "50000")
    ensure_stock(ing_pisco.id, "barra_principal", "8000")
    ensure_stock(ing_limon.id, "barra_principal", "4000")
    ensure_stock(ing_jarabe.id, "barra_principal", "3000")

    pisco_sour = product_by_name.get("PISCO SOUR")
    if pisco_sour:
        rec = Recipe.query.filter_by(product_id=pisco_sour.id).first()
        if not rec:
            rec = Recipe(product_id=pisco_sour.id, name="Receta Pisco Sour", is_active=True, description="Demo local")
            db.session.add(rec)
            db.session.flush()

        # Limpiar ingredientes previos (si existieran) para evitar duplicados
        RecipeIngredient.query.filter_by(recipe_id=rec.id).delete()
        db.session.flush()

        db.session.add_all(
            [
                RecipeIngredient(recipe_id=rec.id, ingredient_id=ing_pisco.id, quantity_per_portion=Decimal("60"), tolerance_percent=Decimal("3.0"), order=1),
                RecipeIngredient(recipe_id=rec.id, ingredient_id=ing_limon.id, quantity_per_portion=Decimal("30"), tolerance_percent=Decimal("3.0"), order=2),
                RecipeIngredient(recipe_id=rec.id, ingredient_id=ing_jarabe.id, quantity_per_portion=Decimal("20"), tolerance_percent=Decimal("3.0"), order=3),
            ]
        )
        db.session.flush()
        print("✅ Receta demo creada para PISCO SOUR")

    # =========================================================
    # InventoryItem (legacy) para pantallas de inventario simple
    # =========================================================
    # Solo crear si no hay items para hoy
    existing_inv = InventoryItem.query.filter_by(shift_date=date.today(), barra="barra_principal").count()
    if existing_inv == 0:
        db.session.add_all(
            [
                InventoryItem(shift_date=date.today(), barra="barra_principal", product_name="CERVEZA LATA", initial_quantity=100, delivered_quantity=25, final_quantity=75, status="open"),
                InventoryItem(shift_date=date.today(), barra="barra_principal", product_name="AGUA MINERAL", initial_quantity=80, delivered_quantity=10, final_quantity=70, status="open"),
            ]
        )
        db.session.flush()
        print("✅ InventoryItem demo creado (barra_principal)")

    # =========================================================
    # Histórico de ventas / cierres / locks (para estadísticas)
    # =========================================================
    history_days = int(os.environ.get("SEED_HISTORY_DAYS", "14"))
    base_sales_per_day = int(os.environ.get("SEED_SALES_PER_DAY", "60"))
    rng = random.Random(20260131)

    # Empleados para ventas/deliveries
    camila = Employee.query.get("1")
    diego = Employee.query.get("2")
    sofia = Employee.query.get("3")

    # Registros (IMPORTANTE: para métricas, register_id suele ser str(tpv.id))
    registers = [
        {"reg": test_register, "id": str(test_register.id), "name": test_register.name, "cashier": test_emp},
        {"reg": caja_1, "id": str(caja_1.id), "name": caja_1.name, "cashier": camila or test_emp},
        {"reg": puerta_1, "id": str(puerta_1.id), "name": puerta_1.name, "cashier": sofia or test_emp},
    ]

    # Productos por categoría para generar tickets más realistas
    entradas = [product_by_name[n] for n in ["ENTRADA GENERAL", "ENTRADA VIP", "ENTRADA 2x1"] if n in product_by_name]
    bebidas = [
        product_by_name[n]
        for n in [
            "PISCO SOUR",
            "MOJITO",
            "GIN TONIC",
            "VODKA TONIC",
            "RAMAZZOTTI",
            "CERVEZA LATA",
            "CERVEZA SCHOP",
            "AGUA MINERAL",
            "BEBIDA",
            "ENERGÉTICA",
            "SHOT TEQUILA",
            "SHOT PISCO",
            "SNACK PAPAS",
            "SNACK MANÍ",
        ]
        if n in product_by_name
    ]

    def pick_payment(total: int):
        r = rng.random()
        if r < 0.34:
            return "Efectivo", Decimal(total), Decimal(0), Decimal(0)
        if r < 0.72:
            return "Débito", Decimal(0), Decimal(total), Decimal(0)
        return "Crédito", Decimal(0), Decimal(0), Decimal(total)

    def ensure_register_session(day_str: str, jornada_id: int, reg_id: str, cashier: Employee, status: str):
        existing = RegisterSession.query.filter_by(register_id=reg_id, jornada_id=jornada_id, shift_date=day_str).first()
        if existing:
            # Asegurar status coherente
            existing.status = status
            return existing
        opened_at = datetime.utcnow() if day_str != today_str else opened_at_utc
        sess = RegisterSession(
            register_id=reg_id,
            opened_by_employee_id=str(cashier.id),
            opened_by_employee_name=str(cashier.name),
            opened_at=opened_at,
            status=status,
            shift_date=day_str,
            jornada_id=jornada_id,
            initial_cash=Decimal(str(rng.choice([0, 10000, 20000, 50000]))),
            ticket_count=0,
        )
        if status == "CLOSED":
            sess.closed_at = opened_at + timedelta(hours=6)
            sess.closed_by = "seed_local_demo_data"
        db.session.add(sess)
        db.session.flush()
        return sess

    def ensure_register_close(day_str: str, reg_id: str, reg_name: str, cashier: Employee, expected: dict, add_big_difference: bool = False):
        existing = RegisterClose.query.filter_by(shift_date=day_str, register_id=reg_id).first()
        if existing:
            return existing
        expected_cash = Decimal(str(expected.get("cash", 0)))
        expected_debit = Decimal(str(expected.get("debit", 0)))
        expected_credit = Decimal(str(expected.get("credit", 0)))
        expected_total = expected_cash + expected_debit + expected_credit

        # Por defecto, "arqueo" igual al esperado; si se pide, forzar diferencia grande
        actual_cash = expected_cash
        actual_debit = expected_debit
        actual_credit = expected_credit
        if add_big_difference:
            actual_cash = expected_cash - Decimal("15000") if expected_cash >= Decimal("15000") else expected_cash + Decimal("15000")

        diff_cash = actual_cash - expected_cash
        diff_debit = actual_debit - expected_debit
        diff_credit = actual_credit - expected_credit
        difference_total = diff_cash + diff_debit + diff_credit

        cierre = RegisterClose(
            register_id=reg_id,
            register_name=reg_name,
            employee_id=str(cashier.id),
            employee_name=str(cashier.name),
            shift_date=day_str,
            opened_at=None,
            closed_at=datetime.utcnow(),
            expected_cash=expected_cash,
            expected_debit=expected_debit,
            expected_credit=expected_credit,
            actual_cash=actual_cash,
            actual_debit=actual_debit,
            actual_credit=actual_credit,
            diff_cash=diff_cash,
            diff_debit=diff_debit,
            diff_credit=diff_credit,
            difference_total=difference_total,
            total_sales=int(expected.get("sales_count", 0)),
            total_amount=expected_total,
            notes="Cierre demo generado automáticamente",
            status="closed",
        )
        db.session.add(cierre)
        db.session.flush()
        return cierre

    def ensure_lock_for_today(reg_id: str, cashier: Employee):
        # Simular una caja "abierta/bloqueada" para métricas/alertas
        now_chile = datetime.now(CHILE_TZ).replace(tzinfo=None)
        lock = RegisterLock.query.get(reg_id)
        if not lock:
            lock = RegisterLock(
                register_id=reg_id,
                employee_id=str(cashier.id),
                employee_name=str(cashier.name),
                session_id="seed",
                locked_at=now_chile - timedelta(minutes=95),  # >60min para activar alerta
                expires_at=now_chile + timedelta(minutes=30),
            )
            db.session.add(lock)
            db.session.flush()
        return lock

    # Generar jornadas + shifts + ventas históricas
    for offset in range(history_days):
        day = today - timedelta(days=offset)
        day_str = day.isoformat()

        # Jornada por día (solo hoy queda "abierto")
        jornada_day = Jornada.query.filter_by(fecha_jornada=day_str).order_by(Jornada.id.desc()).first()
        if not jornada_day:
            jornada_day = Jornada(
                fecha_jornada=day_str,
                tipo_turno="Noche",
                nombre_fiesta=f"DEMO - {day_str}",
                horario_apertura_programado="22:00",
                horario_cierre_programado="05:00",
                horario_apertura_real=None,
                estado_apertura="abierto" if day_str == today_str else "listo",
                djs="DJ Demo",
                barras_disponibles=json.dumps(["barra_principal", "terraza"]),
                abierto_en=opened_at_utc if day_str == today_str else None,
                abierto_por="seed_local_demo_data" if day_str == today_str else None,
            )
            db.session.add(jornada_day)
            db.session.flush()
        else:
            if day_str != today_str and jornada_day.estado_apertura == "abierto":
                # Asegurar que no queden múltiples "abiertos"
                jornada_day.estado_apertura = "listo"

        _get_or_create_by(
            Shift,
            {"shift_date": day_str},
            {
                "is_open": True if day_str == today_str else False,
                "opened_by": "seed_local_demo_data",
                "opened_at": (opened_at_utc if day_str == today_str else datetime(day.year, day.month, day.day, 22, 0)).isoformat(),
                "closed_by": None if day_str == today_str else "seed_local_demo_data",
                "closed_at": None if day_str == today_str else datetime(day.year, day.month, day.day, 23, 59).isoformat(),
                "fiesta_nombre": jornada_day.nombre_fiesta,
                "djs": jornada_day.djs,
                "barras_disponibles": json.dumps(["barra_principal", "terraza"]),
                "bartenders": json.dumps(["Diego Demo"]),
                "notes": "Turno demo histórico",
            },
        )

        # Cantidad de ventas por día (más en viernes/sábado)
        weekend_boost = 1.6 if day.weekday() in (4, 5) else 1.0
        sales_target = int(base_sales_per_day * weekend_boost)
        if day_str == today_str:
            sales_target = max(30, int(base_sales_per_day * 0.6))

        # Crear sesiones de caja por día
        for r in registers:
            status = "OPEN" if (day_str == today_str and r["id"] == str(test_register.id)) else "CLOSED"
            ensure_register_session(day_str, jornada_day.id, r["id"], r["cashier"], status)

        # Crear ventas (idempotentes por idempotency_key DEMO-YYYYMMDD-regid-idx)
        totals_by_register: Dict[str, Dict[str, Any]] = {r["id"]: {"cash": 0, "debit": 0, "credit": 0, "sales_count": 0} for r in registers}

        for i in range(sales_target):
            reg = rng.choices(registers, weights=[0.45, 0.4, 0.15], k=1)[0]
            reg_id = reg["id"]
            cashier = reg["cashier"] or test_emp

            # Hora de venta: hoy dentro del rango abierto; histórico repartido en la tarde/noche
            if day_str == today_str:
                span_minutes = int(max((now_utc - opened_at_utc).total_seconds() // 60, 60))
                minute_offset = rng.randint(0, span_minutes)
                created_at = opened_at_utc + timedelta(minutes=minute_offset)
            else:
                hour = rng.randint(16, 23)
                minute = rng.randint(0, 59)
                created_at = datetime(day.year, day.month, day.day, hour, minute)

            idempotency_key = f"DEMO{day.strftime('%Y%m%d')}-{reg_id}-{i:04d}"
            if PosSale.query.filter_by(idempotency_key=idempotency_key).first():
                continue

            # Flags para variedad (pero la mayoría debe contar para métricas)
            is_cancelled = rng.random() < 0.02
            is_courtesy = (not is_cancelled) and (rng.random() < 0.01)
            no_revenue = (not is_cancelled) and (rng.random() < 0.03)
            is_test = (not is_cancelled) and (rng.random() < 0.03)

            # Armar items por tipo de caja
            items = []
            if reg["reg"].tpv_type == "puerta" and entradas:
                # 1-3 entradas
                for _ in range(rng.randint(1, 3)):
                    p = rng.choice(entradas)
                    q = rng.choice([1, 1, 1, 2])
                    items.append((p, q))
            else:
                # 1-4 items de bar
                for _ in range(rng.randint(1, 4)):
                    p = rng.choice(bebidas)
                    q = rng.choice([1, 1, 2, 3])
                    items.append((p, q))

            total = sum(int(p.price) * int(q) for p, q in items)
            if is_courtesy:
                total = 0

            pay_type, cash, debit, credit = pick_payment(total)
            if total == 0:
                cash, debit, credit = Decimal(0), Decimal(0), Decimal(0)

            sale = PosSale(
                total_amount=Decimal(str(total)),
                payment_type=pay_type,
                payment_cash=cash,
                payment_debit=debit,
                payment_credit=credit,
                employee_id=str(cashier.id),
                employee_name=str(cashier.name),
                register_id=reg_id,
                register_name=reg["name"],
                shift_date=day_str,
                jornada_id=jornada_day.id,
                synced_to_phppos=False,
                register_session_id=None,
                payment_provider=None,
                is_courtesy=is_courtesy,
                is_test=is_test,
                no_revenue=no_revenue,
                idempotency_key=idempotency_key,
                is_cancelled=is_cancelled,
                cancelled_at=(created_at + timedelta(minutes=2)) if is_cancelled else None,
                cancelled_by="seed_local_demo_data" if is_cancelled else None,
                cancelled_reason="Demo cancelada" if is_cancelled else None,
                inventory_applied=False,
                created_at=created_at,
            )
            db.session.add(sale)
            db.session.flush()

            for p, q in items:
                db.session.add(
                    PosSaleItem(
                        sale_id=sale.id,
                        product_id=str(p.id),
                        product_name=p.name,
                        quantity=int(q),
                        unit_price=Decimal(str(p.price)),
                        subtotal=Decimal(str(int(p.price) * int(q))),
                    )
                )

                # Crear deliveries solo para items de bar (mejora gráficos/top productos)
                if reg["reg"].tpv_type != "puerta" and total > 0 and diego:
                    db.session.add(
                        Delivery(
                            sale_id=str(sale.id),
                            item_name=p.name,
                            qty=int(q),
                            bartender=str(diego.name),
                            barra="barra_principal",
                            admin_user="seed",
                            timestamp=created_at + timedelta(minutes=rng.randint(1, 15)),
                        )
                    )

            # Acumular totales por caja/día para cierres
            if not is_cancelled:
                totals_by_register[reg_id]["cash"] += int(cash)
                totals_by_register[reg_id]["debit"] += int(debit)
                totals_by_register[reg_id]["credit"] += int(credit)
                totals_by_register[reg_id]["sales_count"] += 1

        # Cierres: para días históricos cerrar todo; para hoy cerrar 1 y dejar pendientes otros
        for r in registers:
            reg_id = r["id"]
            expected = totals_by_register[reg_id]
            if day_str != today_str:
                ensure_register_close(day_str, reg_id, r["name"], r["cashier"], expected, add_big_difference=False)
            else:
                # Cerrar solo una caja y dejar el resto pendiente (para alertas/KPIs)
                if reg_id == str(caja_1.id):
                    ensure_register_close(day_str, reg_id, r["name"], r["cashier"], expected, add_big_difference=True)

    # Locks para métricas/alertas del turno actual
    ensure_lock_for_today(str(test_register.id), test_emp)

    db.session.commit()
    print("🎉 Seed demo completado.")


def main():
    app = create_app()
    with app.app_context():
        seed_local_demo_data()


if __name__ == "__main__":
    main()

