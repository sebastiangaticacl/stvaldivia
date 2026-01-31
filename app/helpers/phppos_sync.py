"""
Helper para sincronizar ventas locales con PHP POS
"""
import logging
from flask import current_app
from app.models import db
from app.models.pos_models import PosSale, PosSaleItem
from app.infrastructure.external.phppos_kiosk_client import PHPPosKioskClient

logger = logging.getLogger(__name__)


def sync_pending_sales_to_phppos(shift_date=None):
    """
    Sincroniza todas las ventas pendientes (synced_to_phppos=False) con PHP POS.
    
    Args:
        shift_date: Fecha del turno (opcional). Si se proporciona, solo sincroniza ventas de ese turno.
    
    Returns:
        dict: {
            'success': bool,
            'synced_count': int,
            'failed_count': int,
            'errors': list
        }
    """
    try:
        # Obtener ventas pendientes de sincronización
        query = PosSale.query.filter_by(synced_to_phppos=False)
        
        if shift_date:
            query = query.filter_by(shift_date=shift_date)
        
        pending_sales = query.all()
        
        if not pending_sales:
            logger.info("No hay ventas pendientes de sincronización")
            return {
                'success': True,
                'synced_count': 0,
                'failed_count': 0,
                'errors': []
            }
        
        logger.info(f"Sincronizando {len(pending_sales)} venta(s) pendiente(s) con PHP POS...")
        
        # Inicializar cliente PHP POS
        phppos_client = PHPPosKioskClient()
        
        if not phppos_client.api_key:
            error_msg = "API_KEY no configurada. No se pueden sincronizar ventas."
            logger.error(f"❌ {error_msg}")
            return {
                'success': False,
                'synced_count': 0,
                'failed_count': len(pending_sales),
                'errors': [error_msg]
            }
        
        synced_count = 0
        failed_count = 0
        errors = []
        
        # Sincronizar cada venta
        for sale in pending_sales:
            try:
                # Preparar items para PHP POS
                items_for_phppos = []
                for item in sale.items:
                    items_for_phppos.append({
                        'item_id': item.product_id,
                        'quantity': item.quantity,
                        'price': float(item.unit_price)
                    })
                
                # Determinar tipo de pago (mapear a formato PHP POS)
                payment_type = sale.payment_type
                if payment_type == 'Efectivo':
                    payment_type = 'Cash'
                elif payment_type == 'Débito':
                    payment_type = 'Debit'
                elif payment_type == 'Crédito':
                    payment_type = 'Credit'
                # Si ya está en formato correcto, mantenerlo
                
                # Crear venta en PHP POS
                result = phppos_client.create_sale(
                    items=items_for_phppos,
                    total=float(sale.total_amount),
                    payment_type=payment_type,
                    employee_id=sale.employee_id,
                    register_id=sale.register_id
                )
                
                if result.get('success') and result.get('sale_id'):
                    # Actualizar venta local con el ID de PHP POS
                    sale.sale_id_phppos = str(result.get('sale_id'))
                    sale.synced_to_phppos = True
                    
                    # Commit individual para cada venta sincronizada
                    try:
                        db.session.commit()
                        synced_count += 1
                        logger.info(
                            f"✅ Venta {sale.id} sincronizada con PHP POS "
                            f"(sale_id_phppos: {sale.sale_id_phppos})"
                        )
                    except Exception as commit_error:
                        db.session.rollback()
                        error_msg = f"Error al guardar sincronización de venta {sale.id}: {str(commit_error)}"
                        errors.append(error_msg)
                        failed_count += 1
                        logger.error(f"❌ {error_msg}", exc_info=True)
                else:
                    error_msg = result.get('error', 'Error desconocido al crear venta en PHP POS')
                    errors.append(f"Venta {sale.id}: {error_msg}")
                    failed_count += 1
                    logger.warning(f"⚠️  No se pudo sincronizar venta {sale.id}: {error_msg}")
                    
            except Exception as e:
                error_msg = f"Error al sincronizar venta {sale.id}: {str(e)}"
                errors.append(error_msg)
                failed_count += 1
                logger.error(f"❌ {error_msg}", exc_info=True)
                db.session.rollback()
                continue
        
        result = {
            'success': failed_count == 0,
            'synced_count': synced_count,
            'failed_count': failed_count,
            'errors': errors
        }
        
        if synced_count > 0:
            logger.info(
                f"✅ Sincronización completada: {synced_count} venta(s) sincronizada(s), "
                f"{failed_count} fallida(s)"
            )
        
        return result
        
    except Exception as e:
        error_msg = f"Error general al sincronizar ventas: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return {
            'success': False,
            'synced_count': 0,
            'failed_count': len(pending_sales) if 'pending_sales' in locals() else 0,
            'errors': [error_msg]
        }

