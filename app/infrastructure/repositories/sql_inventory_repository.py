"""
Repositorio de Inventario SQL
Implementación de InventoryRepository usando SQLAlchemy.
"""
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy import and_
from flask import current_app

from app.models import db
from app.models.inventory_models import InventoryItem
from app.domain.inventory import ShiftInventory, BarInventory, InventoryItem as DomainInventoryItem
from app.infrastructure.repositories.inventory_repository import InventoryRepository


class SqlInventoryRepository(InventoryRepository):
    """
    Implementación SQL del repositorio de inventario.
    Usa el modelo InventoryItem.
    """
    
    def __init__(self):
        """
        Inicializa el repositorio.
        La verificación de la tabla se hace de forma lazy en el primer uso
        para evitar problemas con el contexto de Flask.
        """
        # No hacer verificación aquí - se hará en el primer uso cuando haya contexto Flask
        pass
    
    def _ensure_table_exists(self):
        """Verifica que la tabla existe, creándola si es necesario"""
        try:
            from flask import has_app_context, current_app
            from app.models import db
            
            if not has_app_context():
                # Si no hay contexto, no podemos verificar ahora
                return
            
            # Intentar una consulta simple para verificar que la tabla existe
            try:
                InventoryItem.query.limit(1).all()
                current_app.logger.debug("✅ Tabla inventory_items verificada")
            except Exception as e:
                # Si la tabla no existe, intentar crearla
                current_app.logger.warning(f"⚠️ Tabla inventory_items no encontrada, intentando crear: {e}")
                try:
                    db.create_all()
                    current_app.logger.info("✅ Tabla inventory_items creada exitosamente")
                except Exception as create_error:
                    current_app.logger.error(f"❌ Error al crear tabla inventory_items: {create_error}")
                    raise RuntimeError(
                        f"No se pudo crear la tabla inventory_items. "
                        f"Verifica la conexión a la base de datos: {create_error}"
                    ) from create_error
        except RuntimeError:
            raise  # Re-lanzar RuntimeError
        except Exception as e:
            # Otros errores - loggear pero no fallar
            try:
                from flask import current_app
                current_app.logger.warning(f"⚠️ Advertencia al verificar tabla inventory_items: {e}")
            except RuntimeError:
                import logging
                logging.getLogger(__name__).warning(f"⚠️ Advertencia al verificar tabla inventory_items: {e}")
    
    def save_shift_inventory(self, inventory: ShiftInventory) -> bool:
        """
        Guarda el inventario de un turno.
        Actualiza o crea los items en la base de datos.
        """
        try:
            # Asegurar que la tabla existe
            self._ensure_table_exists()
            
            shift_date = datetime.strptime(inventory.shift_date, '%Y-%m-%d').date()
            
            # Procesar cada barra
            for barra_name, bar_inventory in inventory.barras.items():
                # Procesar cada item
                for product_name, item in bar_inventory.items.items():
                    # Asegurar que el producto existe en el catálogo global
                    from app.models.product_models import Product
                    product = Product.query.filter_by(name=product_name).first()
                    if not product:
                        product = Product(name=product_name)
                        db.session.add(product)
                        # Flush para obtener ID si fuera necesario, aunque aquí usamos nombre
                        db.session.flush()

                    # Buscar si ya existe el item de inventario
                    db_item = InventoryItem.query.filter_by(
                        shift_date=shift_date,
                        barra=barra_name,
                        product_name=product_name
                    ).first()
                    
                    if db_item:
                        # Actualizar existente
                        db_item.initial_quantity = item.initial_quantity
                        db_item.delivered_quantity = item.delivered_quantity
                        db_item.final_quantity = item.final_quantity
                        db_item.status = 'finalized' if bar_inventory.is_finalized else 'open'
                        # No actualizamos created_at, updated_at se actualiza solo
                    else:
                        # Crear nuevo
                        db_item = InventoryItem(
                            shift_date=shift_date,
                            barra=barra_name,
                            product_name=product_name,
                            initial_quantity=item.initial_quantity,
                            delivered_quantity=item.delivered_quantity,
                            final_quantity=item.final_quantity,
                            status='finalized' if bar_inventory.is_finalized else 'open'
                        )
                        db.session.add(db_item)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al guardar inventario SQL: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
    
    def get_shift_inventory(self, shift_date: str) -> Optional[ShiftInventory]:
        """Obtiene el inventario de un turno"""
        try:
            # Asegurar que la tabla existe
            self._ensure_table_exists()
            
            # Convertir string a date
            date_obj = datetime.strptime(shift_date, '%Y-%m-%d').date()
            
            # Obtener todos los items del turno
            items = InventoryItem.query.filter_by(shift_date=date_obj).all()
            
            if not items:
                return None
            
            # Reconstruir estructura de objetos de dominio
            shift_inventory = ShiftInventory(shift_date=shift_date)
            
            # Agrupar por barra
            items_by_bar = {}
            for item in items:
                if item.barra not in items_by_bar:
                    items_by_bar[item.barra] = []
                items_by_bar[item.barra].append(item)
            
            # Crear inventarios de barra
            for barra, bar_items in items_by_bar.items():
                bar_inventory = shift_inventory.get_bar_inventory(barra)
                
                # Determinar estado (si alguno está finalizado, asumimos finalizado para esa barra)
                is_finalized = any(item.status == 'finalized' for item in bar_items)
                if is_finalized:
                    # Usar la fecha de actualización más reciente como fecha de finalización
                    latest_update = max(item.updated_at for item in bar_items)
                    bar_inventory.finalized_at = latest_update.isoformat() if latest_update else datetime.now().isoformat()
                    bar_inventory.finalized_by = "System" 
                
                # Agregar items
                for db_item in bar_items:
                    domain_item = DomainInventoryItem(
                        product_name=db_item.product_name,
                        initial_quantity=db_item.initial_quantity
                    )
                    domain_item.delivered_quantity = db_item.delivered_quantity
                    domain_item.final_quantity = db_item.final_quantity
                    
                    bar_inventory.items[db_item.product_name] = domain_item
            
            return shift_inventory
            
        except Exception as e:
            error_msg = f"Error al obtener inventario SQL para fecha {shift_date}: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return None
    
    def get_current_shift_inventory(self) -> Optional[ShiftInventory]:
        """Obtiene el inventario del turno actual"""
        try:
            from app.infrastructure.repositories.shift_repository import JsonShiftRepository
            shift_repo = JsonShiftRepository()
            shift_status = shift_repo.get_current_shift_status()
            
            if not shift_status.is_open or not shift_status.shift_date:
                return None
            
            return self.get_shift_inventory(shift_status.shift_date)
        except Exception as e:
            current_app.logger.error(f"Error al obtener inventario del turno actual SQL: {e}")
            return None
    
    def get_bar_inventory(self, shift_date: str, barra: str) -> Optional[BarInventory]:
        """Obtiene el inventario de una barra específica"""
        try:
            shift_inventory = self.get_shift_inventory(shift_date)
            if not shift_inventory:
                return None
            
            return shift_inventory.barras.get(barra)
        except Exception as e:
            current_app.logger.error(f"Error al obtener inventario de barra SQL: {e}")
            return None
    
    def record_delivery(self, barra: str, product_name: str, quantity: int) -> bool:
        """
        Registra una entrega de producto (descuenta del inventario).
        Busca en el turno actual.
        Optimizado para SQL: actualiza directamente la base de datos.
        """
        try:
            # Asegurar que la tabla existe
            self._ensure_table_exists()
            
            # Obtener fecha del turno actual
            from app.infrastructure.repositories.shift_repository import JsonShiftRepository
            shift_repo = JsonShiftRepository()
            shift_status = shift_repo.get_current_shift_status()
            
            if not shift_status.is_open or not shift_status.shift_date:
                return True # No hay turno, no hacemos nada pero no es error
            
            shift_date = datetime.strptime(shift_status.shift_date, '%Y-%m-%d').date()
            
            # Buscar item
            item = InventoryItem.query.filter_by(
                shift_date=shift_date,
                barra=barra,
                product_name=product_name
            ).first()
            
            if item:
                # Actualizar cantidad entregada
                item.delivered_quantity += quantity
                item.updated_at = datetime.utcnow()  # Actualizar timestamp
                db.session.commit()
                try:
                    current_app.logger.debug(
                        f"✅ Inventario actualizado: {barra} - {product_name} "
                        f"(entregado: {item.delivered_quantity})"
                    )
                except RuntimeError:
                    pass
                return True
            
            # Si el item no existe en el inventario inicial, podríamos crearlo o ignorarlo.
            # Por ahora lo ignoramos para mantener consistencia con la lógica de negocio
            # (solo se descuenta lo que se registró al inicio)
            # Opcionalmente podríamos registrarlo como item no planificado.
            
            return True
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error al registrar entrega SQL: {barra} - {product_name} x{quantity}: {e}"
            try:
                current_app.logger.error(error_msg, exc_info=True)
            except RuntimeError:
                import logging
                logging.getLogger(__name__).error(error_msg, exc_info=True)
            return False
