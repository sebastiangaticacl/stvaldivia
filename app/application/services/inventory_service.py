"""
Servicio de Aplicación: Gestión de Inventario
Gestiona el inventario de botellas por barra en los turnos.
"""
from typing import Optional, Tuple, Dict, List
from datetime import datetime
from flask import current_app

from app.domain.inventory import ShiftInventory, BarInventory
from app.application.dto.inventory_dto import (
    RegisterInitialInventoryRequest,
    FinalizeInventoryRequest,
    InventorySummary
)
from app.infrastructure.repositories.inventory_repository import (
    InventoryRepository,
    JsonInventoryRepository
)
from app.infrastructure.repositories.shift_repository import JsonShiftRepository


class InventoryService:
    """
    Servicio de gestión de inventario.
    Encapsula la lógica de negocio del inventario.
    """
    
    def __init__(
        self,
        inventory_repository: Optional[InventoryRepository] = None,
        shift_repository=None
    ):
        """
        Inicializa el servicio de inventario.
        
        Args:
            inventory_repository: Repositorio de inventario
            shift_repository: Repositorio de turnos (para obtener turno actual)
        """
        self.inventory_repository = inventory_repository or JsonInventoryRepository()
        self.shift_repository = shift_repository or JsonShiftRepository()
    
    def register_initial_inventory(
        self,
        request: RegisterInitialInventoryRequest
    ) -> Tuple[bool, str]:
        """
        Registra el inventario inicial de una barra al abrir el turno.
        
        Args:
            request: DTO con información del inventario inicial
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            # Obtener turno actual
            shift_status = self.shift_repository.get_current_shift_status()
            if not shift_status.is_open:
                return False, "No hay un turno abierto. Abre un turno primero."
            
            from app.helpers.date_normalizer import normalize_shift_date
            shift_date_raw = shift_status.shift_date
            shift_date = normalize_shift_date(shift_date_raw) or shift_date_raw
            
            # Obtener o crear inventario del turno
            shift_inventory = self.inventory_repository.get_shift_inventory(shift_date)
            if not shift_inventory:
                shift_inventory = ShiftInventory(shift_date=shift_date)
            
            # Obtener o crear inventario de la barra
            bar_inventory = shift_inventory.get_bar_inventory(request.barra)
            
            # Registrar items
            for product_name, initial_quantity in request.items.items():
                bar_inventory.add_item(product_name, initial_quantity)
            
            # Marcar como registrado
            bar_inventory.registered_at = datetime.now().isoformat()
            bar_inventory.registered_by = request.registered_by
            
            # Guardar
            if not self.inventory_repository.save_shift_inventory(shift_inventory):
                return False, "Error al guardar el inventario"
            
            current_app.logger.info(
                f"Inventario inicial registrado para {request.barra} "
                f"por {request.registered_by} - {len(request.items)} items"
            )
            
            return True, f"Inventario inicial registrado para {request.barra}"
            
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            current_app.logger.error(f"Error al registrar inventario inicial: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}"
    
    def record_delivery(
        self,
        barra: str,
        product_name: str,
        quantity: int
    ) -> bool:
        """
        Registra una entrega de producto (descuenta del inventario).
        Se llama automáticamente cuando se entrega un producto.
        
        Args:
            barra: Nombre de la barra
            product_name: Nombre del producto
            quantity: Cantidad entregada
            
        Returns:
            bool: True si se registró correctamente
        """
        try:
            return self.inventory_repository.record_delivery(barra, product_name, quantity)
        except Exception as e:
            current_app.logger.error(f"Error al registrar entrega en inventario: {e}")
            return False
    
    def finalize_inventory(
        self,
        request: FinalizeInventoryRequest
    ) -> Tuple[bool, str]:
        """
        Finaliza el inventario de una barra al cerrar el turno.
        Calcula las cantidades finales esperadas y las compara con las reales.
        
        Args:
            request: DTO con información para finalizar
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            request.validate()
            
            # Obtener turno actual
            shift_status = self.shift_repository.get_current_shift_status()
            if not shift_status.is_open:
                return False, "No hay un turno abierto."
            
            from app.helpers.date_normalizer import normalize_shift_date
            shift_date_raw = shift_status.shift_date
            shift_date = normalize_shift_date(shift_date_raw) or shift_date_raw
            
            # Obtener inventario del turno
            shift_inventory = self.inventory_repository.get_shift_inventory(shift_date)
            if not shift_inventory:
                return False, "No hay inventario registrado para este turno."
            
            # Obtener inventario de la barra
            bar_inventory = shift_inventory.barras.get(request.barra)
            if not bar_inventory:
                return False, f"No hay inventario registrado para {request.barra}."
            
            # Finalizar
            bar_inventory.finalize(
                finalized_by=request.finalized_by,
                actual_quantities=request.actual_quantities
            )
            
            # Guardar
            if not self.inventory_repository.save_shift_inventory(shift_inventory):
                return False, "Error al guardar el inventario finalizado"
            
            # Calcular resumen
            summary = bar_inventory.get_summary()
            
            current_app.logger.info(
                f"Inventario finalizado para {request.barra} "
                f"por {request.finalized_by} - Diferencia: {summary['total_difference']}"
            )
            
            return True, f"Inventario finalizado para {request.barra}"
            
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            current_app.logger.error(f"Error al finalizar inventario: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}"
    
    def get_bar_inventory_summary(
        self,
        barra: str,
        shift_date: Optional[str] = None
    ) -> Optional[InventorySummary]:
        """
        Obtiene un resumen del inventario de una barra.
        
        Args:
            barra: Nombre de la barra
            shift_date: Fecha del turno (opcional, usa turno actual si no se proporciona)
            
        Returns:
            InventorySummary o None si no existe
        """
        try:
            if not shift_date:
                shift_status = self.shift_repository.get_current_shift_status()
                if not shift_status.is_open:
                    return None
                shift_date = shift_status.shift_date
            
            bar_inventory = self.inventory_repository.get_bar_inventory(shift_date, barra)
            if not bar_inventory:
                return None
            
            summary = bar_inventory.get_summary()
            items = [item.to_dict() for item in bar_inventory.items.values()]
            
            return InventorySummary(
                barra=summary['barra'],
                shift_date=summary['shift_date'],
                total_items=summary['total_items'],
                total_initial=summary['total_initial'],
                total_delivered=summary['total_delivered'],
                total_expected_final=summary['total_expected_final'],
                total_actual_final=summary.get('total_actual_final'),
                total_difference=summary.get('total_difference'),
                is_finalized=summary['is_finalized'],
                items=items
            )
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de inventario: {e}")
            return None
    
    def get_shift_inventory_summary(
        self,
        shift_date: Optional[str] = None
    ) -> Optional[Dict[str, InventorySummary]]:
        """
        Obtiene un resumen del inventario de todas las barras del turno.
        
        Args:
            shift_date: Fecha del turno (opcional)
            
        Returns:
            Dict con resúmenes por barra o None
        """
        try:
            if not shift_date:
                shift_status = self.shift_repository.get_current_shift_status()
                if not shift_status.is_open:
                    return None
                shift_date = shift_status.shift_date
            
            shift_inventory = self.inventory_repository.get_shift_inventory(shift_date)
            if not shift_inventory:
                return None
            
            summaries = {}
            for barra, bar_inventory in shift_inventory.barras.items():
                summary = bar_inventory.get_summary()
                items = [item.to_dict() for item in bar_inventory.items.values()]
                
                summaries[barra] = InventorySummary(
                    barra=summary['barra'],
                    shift_date=summary['shift_date'],
                    total_items=summary['total_items'],
                    total_initial=summary['total_initial'],
                    total_delivered=summary['total_delivered'],
                    total_expected_final=summary['total_expected_final'],
                    total_actual_final=summary.get('total_actual_final'),
                    total_difference=summary.get('total_difference'),
                    is_finalized=summary['is_finalized'],
                    items=items
                )
            
            return summaries
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de inventario del turno: {e}")
            return None









