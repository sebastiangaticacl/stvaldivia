"""
Servicio para el POS propio
Gestiona ventas usando la API de PHP Point of Sale
"""
import logging
from typing import Dict, List, Optional, Any
from flask import current_app, session
from sqlalchemy import func
from app.infrastructure.external.phppos_kiosk_client import PHPPosKioskClient
from app.helpers.cache import cached

logger = logging.getLogger(__name__)


class PosService:
    """Servicio para gestionar el POS"""
    
    def __init__(self):
        self.php_pos_client = PHPPosKioskClient()
    
    def get_products(self, category: Optional[str] = None, limit: int = 1000, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Obtiene productos desde la base de datos LOCAL
        """
        try:
            from app.models.product_models import Product
            
            query = Product.query.filter_by(is_active=True)
            
            if category:
                # Búsqueda case-insensitive parcial (compatible MySQL)
                query = query.filter(func.lower(Product.category).like(func.lower(f"%{category}%")))
            
            products_db = query.limit(limit).all()
            
            products_list = []
            for p in products_db:
                # Formato compatible con el frontend existente
                products_list.append({
                    'item_id': str(p.id),
                    'name': p.name,
                    'category': p.category,
                    'category_normalized': p.category,
                    'category_display': p.category.upper() if p.category else 'GENERAL',
                    'price': float(p.price) if p.price else 0.0,
                    'cost_price': float(p.cost_price) if p.cost_price else 0.0,
                    'quantity': p.stock_quantity,
                    'is_kit': False, # Por ahora todo es producto simple
                    'description': '',
                    'image_id': None
                })
            
            # Ordenar por categoría
            products_list.sort(key=lambda x: (x.get('category_display') or '').lower())
            
            logger.info(f"✅ Obtenidos {len(products_list)} productos desde BD Local")
            return products_list
            
        except Exception as e:
            logger.error(f"Error al obtener productos locales: {e}")
            return []
    
    def get_product(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un producto específico desde BD Local"""
        try:
            from app.models.product_models import Product
            p = Product.query.get(int(item_id))
            
            if not p:
                return None
                
            return {
                'item_id': str(p.id),
                'name': p.name,
                'category': p.category,
                'price': float(p.price) if p.price else 0.0,
                'cost_price': float(p.cost_price) if p.cost_price else 0.0,
                'quantity': p.stock_quantity
            }
        except Exception as e:
            logger.error(f"Error al obtener producto local {item_id}: {e}")
            return None
    
    def get_item_kit(self, kit_id: str) -> Optional[Dict[str, Any]]:
        """Compatibilidad: trata kits como productos normales"""
        return self.get_product(kit_id)
    
    def create_sale(
        self,
        items: List[Dict[str, Any]],
        total: float,
        payment_type: str,
        employee_id: Optional[str] = None,
        register_id: Optional[str] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crea una venta LOCALMENTE y actualiza inventario
        """
        try:
            from app.models import db, PosSale, PosSaleItem
            from app.models.product_models import Product
            from datetime import datetime
            
            # Obtener employee_id y register_id de la sesión si no se proporcionan
            if not employee_id:
                # Obtener bartender_id de forma consistente
                employee_id = session.get('bartender_id')
                if not employee_id:
                    employee_id = session.get('employee_id')
                # Si es un ID numérico de empleado, intentar obtener el nombre
                if employee_id and employee_id.isdigit():
                    from app.models import Employee
                    emp = Employee.query.get(int(employee_id))
                    employee_name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
                else:
                    employee_name = session.get('pos_employee_name', 'Unknown')
            else:
                employee_name = "Unknown" # Deberíamos buscarlo si tenemos el ID
            
            if not register_id:
                register_id = session.get('register_id', '1')
            
            # Mapear tipos de pago
            payment_type_map = {
                'Cash': 'cash',
                'Efectivo': 'cash',
                'Debit': 'debit',
                'Débito': 'debit',
                'Credit': 'credit',
                'Crédito': 'credit'
            }
            normalized_payment = payment_type_map.get(payment_type, 'cash')
            
            # Crear venta
            sale = PosSale(
                sale_time=datetime.now(),
                customer_id=int(customer_id) if customer_id and customer_id.isdigit() else None,
                employee_id=int(employee_id) if employee_id and employee_id.isdigit() else None,
                employee_name=employee_name,
                register_id=register_id,
                payment_type=normalized_payment,
                total_amount=total,
                payment_cash=total if normalized_payment == 'cash' else 0,
                payment_debit=total if normalized_payment == 'debit' else 0,
                payment_credit=total if normalized_payment == 'credit' else 0,
                status='completed'
            )
            
            # Obtener turno actual para asociar fecha
            from app.application.services.service_factory import get_shift_service
            from app.helpers.date_normalizer import normalize_shift_date
            shift_service = get_shift_service()
            shift_status = shift_service.get_current_shift_status()
            if shift_status and shift_status.is_open:
                sale.shift_date = normalize_shift_date(shift_status.shift_date) or shift_status.shift_date
            else:
                sale.shift_date = normalize_shift_date(datetime.now().strftime('%Y-%m-%d')) or datetime.now().strftime('%Y-%m-%d')

            db.session.add(sale)
            db.session.flush() # Para obtener ID
            
            # CORRECCIÓN: Usar Decimal para cálculos financieros
            from app.helpers.financial_utils import to_decimal, round_currency
            
            for item in items:
                item_id = item.get('item_id')
                quantity = float(to_decimal(item.get('quantity', 1)))
                price = float(to_decimal(item.get('price', 0)))
                
                # Buscar producto para obtener nombre correcto
                product = Product.query.get(int(item_id))
                product_name = product.name if product else f"Item {item_id}"
                
                sale_item = PosSaleItem(
                    sale_id=sale.id,
                    product_id=int(item_id) if item_id and item_id.isdigit() else None,
                    product_name=product_name,
                    quantity=quantity,
                    item_price=price,
                    total_price=quantity * price
                )
                db.session.add(sale_item)
                
                # CORRECCIÓN CRÍTICA: NO descontar inventario aquí
                # El inventario se descuenta SOLO cuando se entrega el producto (en SaleDeliveryService.deliver_product)
                # Esto evita doble descuento y permite validar stock antes de entregar
                # 
                # NOTA: El inventario se aplicará cuando el bartender escanee el ticket y entregue el producto
                # usando SaleDeliveryService.deliver_product() o InventoryStockService.apply_inventory_for_sale()

            db.session.commit()
            
            logger.info(f"✅ Venta LOCAL creada exitosamente: ID={sale.id}")
            
            return {
                'success': True,
                'sale_id': str(sale.id),
                'receipt_code': f"POS-{sale.id}",
                'receipt_url': None, # No generamos URL externa
                'sale_info': { # Info mínima para el frontend
                    'sale_id': str(sale.id),
                    'date': sale.sale_time.isoformat(),
                    'total': total,
                    'items': items
                },
                'message': 'Venta registrada localmente'
            }
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error inesperado al crear venta local: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}',
                'sale_id': None
            }
    
    def get_registers(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de cajas locales
        """
        # Preferir cajas desde BD (pos_registers). Si no hay datos, usar fallback estático.
        try:
            from app.models.pos_models import PosRegister
            from sqlalchemy import or_

            # Incluir cajas de prueba siempre (tanto en desarrollo como producción)
            # include_test siempre True - mostrar todas las cajas

            query = PosRegister.query.filter(PosRegister.is_active == True)

            # Ocultar cajas solo-superadmin en el selector POS (empleados)
            # (puede venir como NULL en migraciones antiguas)
            if hasattr(PosRegister, 'superadmin_only'):
                query = query.filter(or_(PosRegister.superadmin_only == False, PosRegister.superadmin_only.is_(None)))

            # NO filtrar cajas de prueba - mostrarlas siempre
            # if not include_test and hasattr(PosRegister, 'is_test'):
            #     query = query.filter(or_(PosRegister.is_test == False, PosRegister.is_test.is_(None)))

            regs = query.order_by(PosRegister.created_at.desc()).all()

            if regs:
                result: List[Dict[str, Any]] = []
                for r in regs:
                    is_test_val = bool(getattr(r, 'is_test', False))
                    name = r.name or f"Caja {r.id}"
                    display_name = name
                    # Señal visual para test (mostrar siempre, tanto en desarrollo como producción)
                    if is_test_val:
                        display_name = f"🧪 {name}"

                    result.append({
                        'id': str(r.id),
                        'name': name,
                        'display_name': display_name,
                        'code': getattr(r, 'code', None),
                        'is_test': is_test_val,
                    })
                return result

        except Exception as e:
            logger.error(f"Error al obtener cajas desde BD: {e}", exc_info=True)

        # Fallback estático (si no hay tablas o no hay datos)
        return [
            {'id': '1', 'name': 'Barra Principal'},
            {'id': '2', 'name': 'Barra Terraza'},
            {'id': '3', 'name': 'Barra VIP'},
            {'id': '4', 'name': 'Barra Exterior'},
            {'id': '5', 'name': 'Caja Entrada'},
        ]
    
    def calculate_total(self, items: List[Dict[str, Any]]) -> float:
        """
        Calcula el total de los items usando Decimal para precisión financiera
        
        Args:
            items: Lista de items con 'quantity' y 'price'
            
        Returns:
            Total calculado (redondeado a 2 decimales)
        """
        # CORRECCIÓN: Usar Decimal para cálculos financieros precisos
        from app.helpers.financial_utils import calculate_total as calculate_total_decimal
        return calculate_total_decimal(items)

