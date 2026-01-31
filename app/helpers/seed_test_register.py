"""
Helper para crear/actualizar caja de prueba idempotente + producto de prueba
"""
import json
import logging
from app.models import db
from app.models.pos_models import PosRegister
from app.models.product_models import Product

logger = logging.getLogger(__name__)


def seed_test_register():
    """
    Crea o actualiza la caja de prueba TEST001 + producto TEST100 de forma idempotente
    
    Returns:
        Tuple[bool, str, PosRegister, Product]: (success, status, register, product)
        status puede ser: "created", "updated", o mensaje de error
    """
    try:
        # Buscar caja existente por code o name
        test_register = PosRegister.query.filter(
            (PosRegister.code == 'TEST001') | (PosRegister.name == 'CAJA TEST')
        ).first()
        
        # ==========================================
        # SEED: CAJA TEST001 (TEST / QA ONLY)
        # ==========================================
        # Configuración de la caja de prueba
        test_config = {
            'name': 'CAJA TEST BIMBA',
            'code': 'TEST001',
            'location': 'TEST',
            'register_type': 'HUMANA',
            'tpv_type': 'humana',  # Legacy
            'is_active': True,
            'operational_status': 'active',
            'is_test': True,
            'payment_methods': json.dumps(['cash', 'debit', 'credit']),
            'payment_provider_primary': 'GETNET',
            'payment_provider_backup': 'KLAP',
            'fallback_policy': json.dumps({
                'enabled': True,
                'max_switch_time_seconds': 60,
                'backup_devices_required': 1,
                'trigger_events': ['pos_error', 'pos_offline']
            }),
            'provider_config': json.dumps({
                'note': 'TEST REGISTER - no usar en operación real',
                'GETNET': {
                    'mode': 'manual',
                    'note': 'Pago manual confirmado'
                },
                'KLAP': {
                    'merchant_id': 'TEST-KLAP',
                    'note': 'Backup para pruebas'
                }
            })
        }
        
        if test_register:
            # Actualizar caja existente
            logger.info(f"✅ Actualizando caja de prueba existente: {test_register.id}")
            
            test_register.name = test_config['name']
            test_register.code = test_config['code']
            test_register.location = test_config['location']
            test_register.register_type = test_config['register_type']
            test_register.tpv_type = test_config['tpv_type']
            test_register.is_active = test_config['is_active']
            test_register.operational_status = test_config['operational_status']
            test_register.is_test = test_config['is_test']
            test_register.payment_methods = test_config['payment_methods']
            test_register.payment_provider_primary = test_config['payment_provider_primary']
            test_register.payment_provider_backup = test_config['payment_provider_backup']
            test_register.fallback_policy = test_config['fallback_policy']
            test_register.provider_config = test_config['provider_config']
            test_register.updated_at = db.func.now()
            
            register_status = "updated"
            register = test_register
        
        else:
            # Crear nueva caja de prueba
            logger.info("✅ Creando nueva caja de prueba")
            
            new_register = PosRegister(
                name=test_config['name'],
                code=test_config['code'],
                location=test_config['location'],
                register_type=test_config['register_type'],
                tpv_type=test_config['tpv_type'],
                is_active=test_config['is_active'],
                operational_status=test_config['operational_status'],
                is_test=test_config['is_test'],
                payment_methods=test_config['payment_methods'],
                payment_provider_primary=test_config['payment_provider_primary'],
                payment_provider_backup=test_config['payment_provider_backup'],
                fallback_policy=test_config['fallback_policy'],
                provider_config=test_config['provider_config'],
                superadmin_only=False,  # Permitir acceso normal para pruebas
                max_concurrent_sessions=1,
                requires_cash_count=True
            )
            
            db.session.add(new_register)
            db.session.flush()  # Para obtener ID
            
            register_status = "created"
            register = new_register
        
        # ==========================================
        # SEED: PRODUCTO TEST100 (TEST / QA ONLY)
        # ==========================================
        test_product_name = "TEST PRODUCTO $100"
        # Buscar por name o external_id="TEST100"
        test_product = Product.query.filter(
            (Product.name == test_product_name) | (Product.external_id == "TEST100")
        ).first()
        
        if test_product:
            # Actualizar producto existente
            logger.info(f"✅ Actualizando producto de prueba existente: {test_product.id}")
            
            test_product.name = test_product_name
            test_product.price = 100
            test_product.cost_price = 0
            test_product.is_active = True
            test_product.is_kit = False  # Producto simple sin receta
            test_product.category = "TEST"
            test_product.stock_quantity = 0
            test_product.stock_minimum = 0
            
            # Asignar external_id como sku/code
            if hasattr(test_product, 'external_id'):
                test_product.external_id = "TEST100"
            
            product_status = "updated"
        else:
            # Crear nuevo producto de prueba
            logger.info("✅ Creando nuevo producto de prueba")
            
            test_product = Product(
                name=test_product_name,
                category="TEST",
                price=100,
                cost_price=0,
                stock_quantity=0,
                stock_minimum=0,
                is_active=True,
                is_kit=False,  # Producto simple sin receta
                external_id="TEST100"  # sku/code para identificación
            )
            
            db.session.add(test_product)
            product_status = "created"
        
        db.session.commit()
        
        # ==========================================
        # SMOKE TEST: Verificar que existen
        # ==========================================
        verify_register = PosRegister.query.filter_by(code='TEST001').first()
        verify_product = Product.query.filter_by(name=test_product_name).first()
        
        if not verify_register:
            logger.error("⚠️ Smoke test falló: caja TEST001 no encontrada después de seed")
            return False, "Error: Caja no se creó correctamente", None, None
        
        if not verify_product:
            logger.error("⚠️ Smoke test falló: producto TEST100 no encontrado después de seed")
            return False, "Error: Producto no se creó correctamente", None, None
        
        logger.info(f"✅ Smoke test OK: Caja {verify_register.id} y Producto {verify_product.id} verificados")
        
        # Determinar status general
        if register_status == "created" and product_status == "created":
            overall_status = "created"
        elif register_status == "updated" and product_status == "updated":
            overall_status = "updated"
        else:
            overall_status = "mixed"  # Uno creado, otro actualizado
        
        return True, overall_status, register, test_product
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al crear/actualizar caja/producto de prueba: {e}", exc_info=True)
        return False, f"Error: {str(e)}", None, None

