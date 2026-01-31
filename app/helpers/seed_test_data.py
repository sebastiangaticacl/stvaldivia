"""
TEST / QA ONLY – DO NOT USE IN PROD LOGIC

Helper para crear/actualizar caja de prueba y producto de prueba de forma idempotente.
"""
import json
import logging
from sqlalchemy import or_
from app.models.pos_models import PosRegister, Employee
from app.models.product_models import Product
from app.models.jornada_models import Jornada, PlanillaTrabajador

logger = logging.getLogger(__name__)


def seed_test_register_and_product(db):
    """
    TEST / QA ONLY – DO NOT USE IN PROD LOGIC
    
    Crea o actualiza de forma IDEMPOTENTE:
    - Una CAJA DE PRUEBA (TEST001)
    - Un PRODUCTO DE PRUEBA de $100 (TEST100)
    
    Returns:
        Tuple[bool, str, PosRegister|None, Product|None]:
            (success, message, register, product)
    """
    try:
        # ==========================================
        # SEED: CAJA TEST001 (TEST / QA ONLY)
        # ==========================================
        test_register = PosRegister.query.filter(
            or_(PosRegister.code == "TEST001", PosRegister.name == "CAJA TEST BIMBA")
        ).first()
        
        if test_register:
            logger.info(f"✅ Actualizando caja de prueba existente: {test_register.id}")
            register_status = "updated"
        else:
            logger.info("✅ Creando nueva caja de prueba")
            test_register = PosRegister()
            db.session.add(test_register)
            register_status = "created"
        
        # Actualizar/crear campos clave (idempotente)
        test_register.name = "CAJA TEST BIMBA"
        test_register.code = "TEST001"
        test_register.is_active = True
        test_register.register_type = "HUMANA"
        test_register.payment_methods = json.dumps(["cash", "debit", "credit"])
        test_register.payment_provider_primary = "GETNET"
        test_register.payment_provider_backup = "KLAP"
        test_register.operational_status = "active"
        test_register.allowed_categories = None  # NULL real
        test_register.is_test = True
        # Campos seguros por defecto
        if getattr(test_register, "superadmin_only", False):
            test_register.superadmin_only = False
        if getattr(test_register, "max_concurrent_sessions", None) is None:
            test_register.max_concurrent_sessions = 1
        if getattr(test_register, "requires_cash_count", None) is None:
            test_register.requires_cash_count = True
        
        db.session.flush()  # Asegurar IDs disponibles
        
        # ==========================================
        # SEED: PRODUCTO TEST100 (TEST / QA ONLY)
        # ==========================================
        test_product = Product.query.filter(
            or_(Product.external_id == "TEST100", Product.name == "TEST PRODUCTO $100")
        ).first()
        
        if test_product:
            logger.info(f"✅ Actualizando producto de prueba existente: {test_product.id}")
            product_status = "updated"
        else:
            logger.info("✅ Creando nuevo producto de prueba")
            test_product = Product()
            db.session.add(test_product)
            product_status = "created"
        
        # Actualizar/crear campos clave (idempotente)
        test_product.name = "TEST PRODUCTO $100"
        test_product.external_id = "TEST100"
        test_product.price = 100
        test_product.cost_price = 0
        test_product.is_active = True
        test_product.is_kit = False
        test_product.category = "TEST"
        test_product.stock_quantity = 0  # Stock de prueba, no bloquea flujos reales
        test_product.is_test = True
        
        db.session.flush()  # Asegurar IDs disponibles sin commit
        
        message = "Caja y producto de prueba listos"
        return True, message, test_register, test_product
    
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error al crear/actualizar datos de prueba: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None, None


def seed_test_cashier_user(db):
    """
    TEST / QA ONLY – DO NOT USE IN PROD LOGIC
    
    Crea o actualiza de forma IDEMPOTENTE:
    - Un EMPLEADO de prueba para CAJA con PIN 0000
    - Y lo asigna a la planilla de la jornada ABIERTA (si existe), para que aparezca en /caja/login_old
    
    Returns:
        Tuple[bool, str, Employee|None]:
            (success, message, employee)
    """
    try:
        test_employee_id = "TEST0000"
        test_pin = "0000"
        test_name = "Usuario Test"

        employee = Employee.query.get(test_employee_id)
        if employee:
            logger.info(f"✅ Actualizando empleado de prueba existente: {employee.id}")
        else:
            logger.info("✅ Creando nuevo empleado de prueba (PIN 0000)")
            employee = Employee(id=test_employee_id, name=test_name)
            db.session.add(employee)

        # Campos mínimos para login local
        employee.first_name = "Usuario"
        employee.last_name = "Test"
        employee.name = test_name
        employee.pin = test_pin
        employee.cargo = "Cajero"
        employee.is_cashier = True
        employee.is_bartender = False
        employee.is_active = True
        employee.deleted = "0"
        employee.synced_from_phppos = False

        db.session.flush()

        # Asignar a planilla de jornada abierta (si existe)
        jornada_abierta = Jornada.query.filter_by(estado_apertura='abierto').order_by(
            Jornada.fecha_jornada.desc()
        ).first()

        if not jornada_abierta:
            return True, "Empleado test (PIN 0000) creado, pero no hay jornada abierta para asignarlo a planilla", employee

        planilla = PlanillaTrabajador.query.filter_by(
            jornada_id=jornada_abierta.id,
            id_empleado=str(test_employee_id)
        ).first()

        if not planilla:
            planilla = PlanillaTrabajador(
                jornada_id=jornada_abierta.id,
                id_empleado=str(test_employee_id),
                nombre_empleado=test_name,
                rol="cajero",
                hora_inicio="00:00",
                hora_fin="23:59",
                costo_hora=0.0,
                costo_total=0.0,
                area="caja"
            )
            db.session.add(planilla)
        else:
            planilla.nombre_empleado = test_name
            planilla.rol = "cajero"
            planilla.area = planilla.area or "caja"

        db.session.flush()

        return True, "Empleado test (PIN 0000) creado y asignado a Caja en la jornada abierta", employee

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error al crear/actualizar empleado test (0000): {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg, None

