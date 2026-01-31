"""
Servicio de gestión de entregas de tickets
Implementa la lógica operativa completa de Club Bimba:
- NO descuenta inventario al vender
- Solo descuenta inventario al entregar (según receta)
- Tracking completo de entregas por bartender
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import current_app
from app.models import db
from app.models.sale_delivery_models import SaleDeliveryStatus, DeliveryItem
from app.models.delivery_models import Delivery
from app.models.pos_models import PosSale, PosSaleItem
from app.services.recipe_service import RecipeService

# Importar RecipeService correctamente
try:
    from app.services.recipe_service import get_recipe_service
except ImportError:
    # Fallback si no existe la función factory
    pass


class SaleDeliveryService:
    """
    Servicio para gestionar el ciclo completo de entregas:
    1. Crear estado de entrega al vender
    2. Escanear ticket y obtener productos pendientes
    3. Entregar productos uno a uno con descuento de inventario
    4. Finalizar ticket cuando todos están entregados
    """
    
    def __init__(self):
        self.recipe_service = RecipeService()
    
    def create_delivery_status(self, sale: PosSale) -> SaleDeliveryStatus:
        """
        Crea el estado de entrega para una venta recién creada.
        Se llama automáticamente cuando se crea una venta en POS.
        
        Args:
            sale: PosSale - Venta recién creada
            
        Returns:
            SaleDeliveryStatus - Estado creado
        """
        try:
            # Obtener items de la venta
            items_detail = []
            total_items = 0
            
            for item in sale.items:
                items_detail.append({
                    'product_name': item.product_name,
                    'product_id': item.product_id,
                    'quantity': item.quantity,
                    'entregado': 0,
                    'pendiente': item.quantity
                })
                total_items += item.quantity
            
            # Crear estado de entrega
            delivery_status = SaleDeliveryStatus(
                sale_id=self._get_sale_id_for_tracking(sale),
                estado_entrega='pendiente',
                total_items=total_items,
                items_entregados=0,
                items_pendientes=total_items,
                items_detail=items_detail
            )
            
            db.session.add(delivery_status)
            db.session.commit()
            
            current_app.logger.info(f"✅ Estado de entrega creado para venta {delivery_status.sale_id}")
            return delivery_status
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear estado de entrega: {e}", exc_info=True)
            raise
    
    def _get_sale_id_for_tracking(self, sale: PosSale) -> str:
        """
        Obtiene el ID de venta para tracking.
        Prioriza sale_id_phppos si existe, sino usa ID local con formato BMB.
        """
        if sale.sale_id_phppos:
            return sale.sale_id_phppos
        
        # Generar ID local si no existe
        from app.helpers.timezone_utils import CHILE_TZ
        if not hasattr(sale, 'id') or sale.id is None:
            db.session.flush()  # Para obtener el ID
            
        return f"BMB-{sale.created_at.strftime('%Y%m%d')}-{str(sale.id).zfill(6)}"
    
    def scan_ticket(self, sale_id: str, scanner_id: str, scanner_name: str) -> Dict[str, Any]:
        """
        Escanea un ticket y registra el escaneo.
        Verifica que el ticket existe, no está duplicado y no está completado.
        
        Args:
            sale_id: ID del ticket a escanear
            scanner_id: ID del escáner/bartender
            scanner_name: Nombre del bartender
            
        Returns:
            Dict con información del ticket y productos pendientes
        """
        try:
            # Buscar estado de entrega
            delivery_status = SaleDeliveryStatus.query.filter_by(sale_id=sale_id).first()
            
            if not delivery_status:
                # Intentar buscar en PosSale
                sale = PosSale.query.filter_by(sale_id_phppos=sale_id).first()
                if not sale:
                    # Buscar por ID local
                    try:
                        if sale_id.startswith('BMB-'):
                            parts = sale_id.split('-')
                            if len(parts) >= 3:
                                local_id = int(parts[-1])
                                sale = PosSale.query.get(local_id)
                    except:
                        pass
                
                if sale:
                    # Crear estado de entrega si no existe
                    delivery_status = self.create_delivery_status(sale)
                else:
                    return {
                        'error': 'Ticket no encontrado',
                        'sale_id': sale_id
                    }
            
            # Verificar que no esté completado
            if delivery_status.estado_entrega == 'completado':
                return {
                    'error': 'Este ticket ya fue completamente entregado',
                    'sale_id': sale_id,
                    'completed_at': delivery_status.completed_at.isoformat() if delivery_status.completed_at else None
                }
            
            # Registrar escaneo
            if not delivery_status.scanned_at:
                delivery_status.scanned_at = datetime.utcnow()
                delivery_status.scanner_id = scanner_id
                delivery_status.scanner_name = scanner_name
                if delivery_status.estado_entrega == 'pendiente':
                    delivery_status.estado_entrega = 'en_proceso'
                db.session.commit()
            
            return {
                'success': True,
                'sale_id': sale_id,
                'estado': delivery_status.estado_entrega,
                'items_detail': delivery_status.items_detail or [],
                'items_pendientes': delivery_status.items_pendientes,
                'items_entregados': delivery_status.items_entregados,
                'scanned_at': delivery_status.scanned_at.isoformat() if delivery_status.scanned_at else None
            }
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al escanear ticket {sale_id}: {e}", exc_info=True)
            return {
                'error': f'Error al escanear ticket: {str(e)}',
                'sale_id': sale_id
            }
    
    def deliver_product(
        self,
        sale_id: str,
        product_name: str,
        quantity: int,
        bartender_id: str,
        bartender_name: str,
        location: str
    ) -> Tuple[bool, str, Optional[DeliveryItem], List[Dict[str, Any]]]:
        """
        Entrega un producto individual y descuenta inventario según receta.
        
        Args:
            sale_id: ID del ticket
            product_name: Nombre del producto a entregar
            quantity: Cantidad a entregar (normalmente 1)
            bartender_id: ID del bartender que entrega
            bartender_name: Nombre del bartender
            location: Ubicación ("Barra Pista" o "Terraza")
            
        Returns:
            Tuple[bool, str, Optional[DeliveryItem], List[Dict]]:
            (success, message, delivery_item, ingredients_consumed)
        """
        try:
            # Obtener estado de entrega
            delivery_status = SaleDeliveryStatus.query.filter_by(sale_id=sale_id).first()
            
            if not delivery_status:
                return False, f"Ticket {sale_id} no encontrado", None, []
            
            # Verificar que no esté completado
            if delivery_status.estado_entrega == 'completado':
                return False, "Este ticket ya fue completamente entregado", None, []
            
            # Verificar cantidad pendiente
            items_detail = delivery_status.items_detail or []
            product_found = False
            pending_qty = 0
            product_id = None
            
            for item in items_detail:
                if item.get('product_name', '').lower() == product_name.lower():
                    product_found = True
                    pending_qty = item.get('pendiente', 0)
                    product_id = item.get('product_id')
                    break
            
            if not product_found:
                return False, f"Producto '{product_name}' no encontrado en este ticket", None, []
            
            if quantity > pending_qty:
                return False, f"No se puede entregar {quantity} unidades. Solo hay {pending_qty} pendientes", None, []
            
            # CORRECCIÓN CRÍTICA: Verificar si el inventario ya fue aplicado para esta venta
            from app.models.pos_models import PosSale
            sale = PosSale.query.filter_by(id=int(sale_id) if sale_id.isdigit() else None).first()
            if sale and sale.inventory_applied:
                current_app.logger.warning(
                    f"⚠️ Inventario ya aplicado para venta #{sale_id} - evitando doble descuento en entrega"
                )
                # Continuar con la entrega pero sin descontar inventario nuevamente
                ingredients_consumed = []
                delivery_type = 'unidad'
            else:
                # Aplicar consumo de inventario según receta
                ingredients_consumed = []
                delivery_type = 'unidad'
                
                try:
                    # Intentar obtener receta del producto y aplicar consumo
                    recipe_result = self.recipe_service.apply_recipe_consumption(
                        product_name=product_name,
                        quantity=quantity,
                        location=location,
                        bartender_id=bartender_id,
                        bartender_name=bartender_name,
                        sale_id=sale_id
                    )
                
                    if recipe_result and len(recipe_result) >= 2:
                        success = recipe_result[0]
                        if success:
                            # Obtener lista de consumos (tercer elemento del tuple)
                            ingredients_consumed = recipe_result[2] if len(recipe_result) > 2 else []
                            if ingredients_consumed:
                                delivery_type = 'receta'
                            else:
                                # Producto sin receta, descuenta 1 unidad
                                delivery_type = 'unidad'
                        else:
                            current_app.logger.warning(f"⚠️ Error al aplicar receta: {recipe_result[1]}")
                            # Continuar con entrega aunque haya error en receta
                    else:
                        current_app.logger.warning(f"⚠️ Respuesta inesperada de apply_recipe_consumption")
                        
                        # Verificar si el producto está marcado como kit pero no tiene receta
                        from app.models.product_models import Product
                        product = Product.query.filter_by(name=product_name).first()
                        if product and product.is_kit:
                            current_app.logger.warning(
                                f"⚠️ Producto '{product_name}' marcado como kit pero sin receta configurada. "
                                f"Por favor, configure la receta en la gestión de productos."
                            )
                        
                except Exception as e:
                    current_app.logger.error(f"Error al aplicar consumo de receta: {e}", exc_info=True)
                    # Continuar con entrega aunque haya error
            
            # Crear registro de entrega detallada
            delivery_item = DeliveryItem(
                sale_id=sale_id,
                product_name=product_name,
                product_id=product_id,
                quantity_delivered=quantity,
                bartender_id=bartender_id,
                bartender_name=bartender_name,
                location=location,
                delivery_type=delivery_type,
                ingredients_consumed=ingredients_consumed
            )
            
            db.session.add(delivery_item)
            
            # Actualizar estado de entrega
            for item in items_detail:
                if item.get('product_name', '').lower() == product_name.lower():
                    item['entregado'] = item.get('entregado', 0) + quantity
                    item['pendiente'] = item.get('pendiente', 0) - quantity
                    break
            
            delivery_status.items_detail = items_detail
            delivery_status.items_entregados += quantity
            delivery_status.items_pendientes -= quantity
            delivery_status.update_status()
            
            # También crear registro en Delivery (compatibilidad con sistema existente)
            delivery = Delivery(
                sale_id=sale_id,
                item_name=product_name,
                qty=quantity,
                bartender=bartender_name,
                barra=location,
                timestamp=datetime.utcnow()
            )
            db.session.add(delivery)
            
            delivery_item.delivery_id = delivery.id
            
            db.session.commit()
            
            # Enviar evento a n8n (después de commit exitoso)
            try:
                from app.helpers.n8n_client import send_delivery_created
                send_delivery_created(
                    delivery_id=delivery.id,
                    item_name=product_name,
                    quantity=quantity,
                    bartender=bartender_name,
                    barra=location
                )
            except Exception as e:
                current_app.logger.warning(f"Error enviando evento a n8n: {e}")
            
            message = f"{quantity} x {product_name} entregado(s)"
            if ingredients_consumed:
                ingredientes_str = ", ".join([
                    f"{c.get('cantidad', 0)} {c.get('unidad', '')} de {c.get('ingrediente', '')}"
                    for c in ingredients_consumed
                ])
                message += f" (Inventario: {ingredientes_str})"
            
            current_app.logger.info(f"✅ Entrega registrada: {message}")
            
            return True, message, delivery_item, ingredients_consumed
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al entregar producto: {e}", exc_info=True)
            return False, f"Error al entregar producto: {str(e)}", None, []
    
    def get_delivery_status(self, sale_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de entrega de un ticket.
        
        Args:
            sale_id: ID del ticket
            
        Returns:
            Dict con estado de entrega o None si no existe
        """
        try:
            delivery_status = SaleDeliveryStatus.query.filter_by(sale_id=sale_id).first()
            
            if not delivery_status:
                return None
            
            return delivery_status.to_dict()
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener estado de entrega: {e}", exc_info=True)
            return None
    
    def get_deliveries_by_bartender(
        self,
        bartender_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene todas las entregas realizadas por un bartender.
        
        Args:
            bartender_id: ID del bartender
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)
            
        Returns:
            Lista de entregas
        """
        try:
            query = DeliveryItem.query.filter_by(bartender_id=bartender_id)
            
            if start_date:
                query = query.filter(DeliveryItem.delivered_at >= start_date)
            if end_date:
                query = query.filter(DeliveryItem.delivered_at <= end_date)
            
            deliveries = query.order_by(DeliveryItem.delivered_at.desc()).all()
            
            return [d.to_dict() for d in deliveries]
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener entregas por bartender: {e}", exc_info=True)
            return []


def get_sale_delivery_service() -> SaleDeliveryService:
    """Factory function para obtener instancia del servicio"""
    return SaleDeliveryService()





