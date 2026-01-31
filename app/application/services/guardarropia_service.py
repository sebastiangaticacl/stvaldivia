"""
Servicio de Aplicación: Gestión de Guardarropía
Gestiona el guardado y retiro de prendas/abrigos de clientes.
"""
from typing import Optional, Tuple, List, Dict
from datetime import datetime
from flask import current_app

from app.application.dto.guardarropia_dto import (
    DepositItemRequest,
    RetrieveItemRequest,
    MarkLostRequest,
    GuardarropiaItemSummary,
    GuardarropiaStats
)
from app.models.guardarropia_models import GuardarropiaItem
from app.infrastructure.repositories.sql_guardarropia_repository import SqlGuardarropiaRepository
from app.infrastructure.repositories.shift_repository import JsonShiftRepository


class GuardarropiaService:
    """
    Servicio de gestión de guardarropía.
    Encapsula la lógica de negocio del guardado y retiro de prendas.
    """
    
    def __init__(
        self,
        repository: Optional[SqlGuardarropiaRepository] = None,
        shift_repository=None
    ):
        """
        Inicializa el servicio de guardarropía.
        
        Args:
            repository: Repositorio de guardarropía
            shift_repository: Repositorio de turnos (para obtener turno actual)
        """
        self.repository = repository or SqlGuardarropiaRepository()
        self.shift_repository = shift_repository or JsonShiftRepository()
    
    def deposit_item(
        self,
        request: DepositItemRequest,
        deposited_by: str
    ) -> Tuple[bool, str, Optional[GuardarropiaItem]]:
        """
        Deposita una prenda en guardarropía.
        
        Args:
            request: DTO con información del item a depositar
            deposited_by: Usuario que deposita el item
            
        Returns:
            Tuple[bool, str, Optional[GuardarropiaItem]]: (éxito, mensaje, item creado)
        """
        try:
            request.validate()
            
            # Obtener turno actual si no se proporciona shift_date
            shift_date = request.shift_date
            if not shift_date:
                shift_status = self.shift_repository.get_current_shift_status()
                if shift_status and shift_status.is_open:
                    shift_date = shift_status.shift_date
                else:
                    from datetime import datetime
                    shift_date = datetime.now().strftime('%Y-%m-%d')
            
            # Normalizar tipo de pago
            payment_type = None
            if request.payment_type:
                payment_map = {
                    'efectivo': 'cash',
                    'débito': 'debit',
                    'crédito': 'credit'
                }
                payment_type = payment_map.get(request.payment_type.lower(), request.payment_type.lower())
            
            # Crear venta POS si hay precio - SIEMPRE guardar en BD
            sale_id = None
            if request.price and request.price > 0:
                try:
                    from flask import session
                    from app.services.pos_service import PosService
                    from app.application.services.service_factory import get_shift_service
                    from decimal import Decimal
                    
                    pos_service = PosService()
                    shift_service = get_shift_service()
                    shift_status = shift_service.get_current_shift_status()
                    
                    # Crear item de venta para el espacio/cluster
                    # Si hay múltiples clusters, crear un item con la cantidad
                    precio_unitario = 500.0  # Precio fijo por cluster
                    sale_items = [{
                        'item_id': 'GUARDARROPIA-ESPACIO',
                        'quantity': request.clusters,  # Cantidad de clusters
                        'price': precio_unitario,  # Precio unitario
                        'name': f'Guardarropía - {request.clusters} Espacio{"s" if request.clusters > 1 else ""}/Cluster{"s" if request.clusters > 1 else ""}',
                        'subtotal': float(request.price)  # Precio total
                    }]
                    
                    # Obtener employee_id de la sesión (priorizar guardarropía, luego admin)
                    employee_id = (
                        session.get('guardarropia_employee_id') or 
                        session.get('pos_employee_id') or 
                        session.get('admin_username') or 
                        'admin'
                    )
                    employee_name = (
                        session.get('guardarropia_employee_name') or 
                        session.get('pos_employee_name') or 
                        session.get('admin_username') or 
                        'Administrador'
                    )
                    register_id = session.get('register_id', 'GUARDARROPIA')
                    register_name = session.get('register_name', 'Guardarropía')
                    
                    # Crear la venta - SIEMPRE guardar en BD
                    sale_result = pos_service.create_sale(
                        items=sale_items,
                        total=Decimal(str(request.price)),
                        payment_type=payment_type or 'cash',
                        employee_id=str(employee_id),
                        register_id=register_id,
                        customer_id=None
                    )
                    
                    if sale_result.get('success'):
                        sale_id = sale_result.get('sale_id')
                        current_app.logger.info(
                            f"✅ Venta POS creada y guardada en BD para guardarropía: {sale_id} - "
                            f"Ticket: {ticket_code}, Precio: ${request.price}, "
                            f"Empleado: {employee_name}, Caja: {register_name}"
                        )
                    else:
                        error_msg = sale_result.get('error', 'Error desconocido')
                        current_app.logger.error(
                            f"❌ No se pudo crear venta POS para guardarropía: {error_msg} - "
                            f"Ticket: {ticket_code}, Precio: ${request.price}"
                        )
                        # IMPORTANTE: Aunque falle la venta POS, continuar guardando el item
                        # El item se guardará sin sale_id asociado
                except Exception as e:
                    current_app.logger.error(
                        f"❌ Error al crear venta POS para guardarropía: {e}", 
                        exc_info=True
                    )
                    # IMPORTANTE: Continuar guardando el item aunque falle la venta POS
                    # El item se guardará sin sale_id asociado
            
            # Asignar clusters si no se proporcionaron
            if not request.cluster_numbers:
                # Obtener clusters disponibles automáticamente
                available_clusters = self.get_available_clusters(count=request.clusters)
                if len(available_clusters) < request.clusters:
                    return False, f"No hay suficientes clusters disponibles. Disponibles: {len(available_clusters)}, Solicitados: {request.clusters}", None
                request.cluster_numbers = ','.join(map(str, available_clusters[:request.clusters]))
            
            # Validar que los clusters no estén ocupados
            occupied_clusters = self.get_occupied_cluster_numbers(shift_date=shift_date)
            requested_clusters = [int(c.strip()) for c in request.cluster_numbers.split(',') if c.strip().isdigit()]
            conflicting_clusters = [c for c in requested_clusters if c in occupied_clusters]
            
            if conflicting_clusters:
                return False, f"Los clusters {', '.join(map(str, conflicting_clusters))} ya están ocupados. Por favor, selecciona otros clusters.", None
            
            # Generar código de ticket automáticamente
            # Formato: IDDIAMESCLUSTER (ejemplo: 110125)
            # ID: contador del día, DIA-MES: fecha, CLUSTER: primer cluster asignado
            from datetime import datetime
            import time
            now = datetime.now()
            dia = now.strftime('%d')  # Día (01-31)
            mes = now.strftime('%m')   # Mes (01-12)
            
            # Obtener el primer cluster asignado
            primer_cluster = min(requested_clusters) if requested_clusters else 1
            
            # Contar items del día para generar ID único
            from app.models.guardarropia_models import GuardarropiaItem
            items_hoy = GuardarropiaItem.query.filter_by(shift_date=shift_date).count()
            ticket_id = items_hoy + 1  # Siguiente ID disponible
            
            # Generar código: IDDIAMESCLUSTER (sin guiones)
            ticket_code = f"{ticket_id}{dia}{mes}{primer_cluster}"
            
            # Verificar que no exista (por si acaso hay duplicados)
            counter = 1
            original_code = ticket_code
            while self.repository.find_by_ticket_code(ticket_code):
                # Si existe, agregar sufijo
                ticket_code = f"{original_code}{counter}"
                counter += 1
                if counter > 99:  # Límite de seguridad
                    # Si hay demasiados, usar timestamp
                    ticket_code = f"{ticket_id}{dia}{mes}{int(time.time())}"
                    break
            
            ticket_code = ticket_code.strip()
            
            # Crear item
            item = GuardarropiaItem(
                ticket_code=ticket_code,
                description=request.description,
                customer_name=request.customer_name,
                customer_phone=request.customer_phone,
                status='deposited',
                deposited_at=datetime.now(),
                deposited_by=deposited_by,
                shift_date=shift_date,
                price=request.price,  # Precio total (clusters * precio_unitario)
                clusters=request.clusters,  # Cantidad de clusters/espacios
                cluster_numbers=request.cluster_numbers,  # Números específicos de clusters
                payment_type=payment_type,
                sale_id=int(sale_id) if sale_id and str(sale_id).isdigit() else None,
                notes=request.notes
            )
            
            # Guardar en BD - CRÍTICO: Asegurar que se guarde
            if not self.repository.save(item):
                current_app.logger.error(
                    f"❌ Error crítico: No se pudo guardar item en BD - "
                    f"Ticket: {ticket_code}, Cliente: {request.customer_name}"
                )
                return False, "Error al guardar el item en la base de datos", None
            
            # Verificar que se guardó correctamente
            saved_item = self.repository.find_by_ticket_code(ticket_code)
            if not saved_item:
                current_app.logger.error(
                    f"❌ Error crítico: Item no encontrado después de guardar - "
                    f"Ticket: {ticket_code}"
                )
                return False, "Error: El item no se guardó correctamente en la base de datos", None
            
            # FASE 3: Generar ticket QR automáticamente
            try:
                from app.helpers.guardarropia_ticket_service import GuardarropiaTicketService
                from flask import session
                
                # Obtener información del usuario
                user_id = (
                    session.get('guardarropia_employee_id') or 
                    session.get('pos_employee_id') or 
                    session.get('admin_username') or 
                    'admin'
                )
                user_name = (
                    session.get('guardarropia_employee_name') or 
                    session.get('pos_employee_name') or 
                    session.get('admin_username') or 
                    'Administrador'
                )
                
                # Obtener jornada_id si está disponible
                jornada_id = None
                try:
                    from app.models.jornada_models import Jornada
                    if shift_date:
                        jornada = Jornada.query.filter_by(
                            fecha_jornada=shift_date,
                            estado_apertura='abierto'
                        ).first()
                        if jornada:
                            jornada_id = jornada.id
                except:
                    pass
                
                ticket_created, ticket_obj, ticket_msg = GuardarropiaTicketService.create_ticket_for_item(
                    item=saved_item,
                    user_id=str(user_id),
                    user_name=user_name,
                    jornada_id=jornada_id
                )
                
                if ticket_created and ticket_obj:
                    current_app.logger.info(
                        f"✅ Ticket QR generado: {ticket_obj.display_code} para item {saved_item.id}"
                    )
                else:
                    current_app.logger.warning(
                        f"⚠️  No se pudo crear ticket QR: {ticket_msg}"
                    )
            except Exception as e:
                current_app.logger.error(
                    f"⚠️  Error al crear ticket QR (item guardado igualmente): {e}", 
                    exc_info=True
                )
                # Continuar aunque falle la generación del ticket QR
            
            current_app.logger.info(
                f"✅ Item depositado y guardado en BD: {item.ticket_code} "
                f"por {deposited_by} - Precio: ${request.price or 'Gratis'} - "
                f"Venta POS: {sale_id or 'N/A'} - ID BD: {saved_item.id}"
            )
            
            message = f"Item depositado exitosamente con código {item.ticket_code}"
            if sale_id:
                message += f" - Venta POS: {sale_id}"
            
            return True, message, saved_item
            
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            current_app.logger.error(f"Error al depositar item: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}", None
    
    def retrieve_item(
        self,
        request: RetrieveItemRequest
    ) -> Tuple[bool, str, Optional[GuardarropiaItem]]:
        """
        Retira una prenda de guardarropía.
        
        Args:
            request: DTO con información para retirar
            
        Returns:
            Tuple[bool, str, Optional[GuardarropiaItem]]: (éxito, mensaje, item actualizado)
        """
        try:
            request.validate()
            
            # Buscar item
            item = self.repository.find_by_ticket_code(request.ticket_code)
            if not item:
                return False, f"No se encontró un item con el código {request.ticket_code}", None
            
            if item.is_retrieved():
                return False, f"El item con código {request.ticket_code} ya fue retirado", item
            
            if item.is_lost():
                return False, f"El item con código {request.ticket_code} está marcado como perdido", item
            
            # Actualizar item
            item.status = 'retrieved'
            item.retrieved_at = datetime.now()
            item.retrieved_by = request.retrieved_by
            item.updated_at = datetime.now()
            
            # Guardar en BD - CRÍTICO: Asegurar que se actualice
            if not self.repository.update(item):
                current_app.logger.error(
                    f"❌ Error crítico: No se pudo actualizar item en BD - "
                    f"Ticket: {item.ticket_code}"
                )
                return False, "Error al actualizar el item en la base de datos", None
            
            # Verificar que se actualizó correctamente
            updated_item = self.repository.find_by_ticket_code(request.ticket_code)
            if not updated_item or not updated_item.is_retrieved():
                current_app.logger.error(
                    f"❌ Error crítico: Item no actualizado correctamente - "
                    f"Ticket: {item.ticket_code}"
                )
                return False, "Error: El item no se actualizó correctamente en la base de datos", None
            
            current_app.logger.info(
                f"✅ Item retirado y guardado en BD: {item.ticket_code} "
                f"por {request.retrieved_by} - ID BD: {updated_item.id}"
            )
            
            return True, f"Item retirado exitosamente", updated_item
            
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            current_app.logger.error(f"Error al retirar item: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}", None
    
    def mark_as_lost(
        self,
        request: MarkLostRequest
    ) -> Tuple[bool, str, Optional[GuardarropiaItem]]:
        """
        Marca un item como perdido.
        
        Args:
            request: DTO con información para marcar como perdido
            
        Returns:
            Tuple[bool, str, Optional[GuardarropiaItem]]: (éxito, mensaje, item actualizado)
        """
        try:
            request.validate()
            
            # Buscar item
            item = self.repository.find_by_ticket_code(request.ticket_code)
            if not item:
                return False, f"No se encontró un item con el código {request.ticket_code}", None
            
            if item.is_retrieved():
                return False, f"El item con código {request.ticket_code} ya fue retirado", item
            
            # Actualizar item
            item.status = 'lost'
            if request.notes:
                item.notes = f"{item.notes or ''}\n[PERDIDO] {request.notes}".strip()
            item.updated_at = datetime.now()
            
            # Guardar en BD - CRÍTICO: Asegurar que se actualice
            if not self.repository.update(item):
                current_app.logger.error(
                    f"❌ Error crítico: No se pudo actualizar item en BD - "
                    f"Ticket: {item.ticket_code}"
                )
                return False, "Error al actualizar el item en la base de datos", None
            
            # Verificar que se actualizó correctamente
            updated_item = self.repository.find_by_ticket_code(request.ticket_code)
            if not updated_item or not updated_item.is_lost():
                current_app.logger.error(
                    f"❌ Error crítico: Item no actualizado correctamente - "
                    f"Ticket: {item.ticket_code}"
                )
                return False, "Error: El item no se actualizó correctamente en la base de datos", None
            
            current_app.logger.info(
                f"✅ Item marcado como perdido y guardado en BD: {item.ticket_code} - "
                f"ID BD: {updated_item.id}"
            )
            
            return True, f"Item marcado como perdido", item
            
        except ValueError as e:
            return False, str(e), None
        except Exception as e:
            current_app.logger.error(f"Error al marcar item como perdido: {e}", exc_info=True)
            return False, f"Error inesperado: {str(e)}", None
    
    def get_item_by_ticket(
        self,
        ticket_code: str
    ) -> Optional[GuardarropiaItemSummary]:
        """
        Obtiene un item por código de ticket.
        
        Args:
            ticket_code: Código del ticket
            
        Returns:
            GuardarropiaItemSummary o None si no existe
        """
        try:
            item = self.repository.find_by_ticket_code(ticket_code)
            if not item:
                return None
            
            return GuardarropiaItemSummary(
                id=item.id,
                ticket_code=item.ticket_code,
                description=item.description,
                customer_name=item.customer_name,
                status=item.status,
                deposited_at=item.deposited_at.isoformat() if item.deposited_at else None,
                retrieved_at=item.retrieved_at.isoformat() if item.retrieved_at else None,
                deposited_by=item.deposited_by,
                retrieved_by=item.retrieved_by,
                shift_date=item.shift_date,
                notes=item.notes,
                photo_path=item.photo_path,
                marked_unretrieved_at=item.marked_unretrieved_at.isoformat() if item.marked_unretrieved_at else None,
                marked_unretrieved_by=item.marked_unretrieved_by,
                tracking_notes=item.tracking_notes,
                last_tracking_date=item.last_tracking_date.isoformat() if item.last_tracking_date else None
            )
        except Exception as e:
            current_app.logger.error(f"Error al obtener item por ticket: {e}")
            return None
    
    def get_deposited_items(
        self,
        shift_date: Optional[str] = None
    ) -> List[GuardarropiaItemSummary]:
        """
        Obtiene todos los items depositados (no retirados).
        
        Args:
            shift_date: Fecha del turno (opcional)
            
        Returns:
            Lista de GuardarropiaItemSummary
        """
        try:
            items = self.repository.find_deposited(shift_date=shift_date)
            return [self._item_to_summary(item) for item in items]
        except Exception as e:
            current_app.logger.error(f"Error al obtener items depositados: {e}")
            return []
    
    def get_all_items(
        self,
        status: Optional[str] = None,
        shift_date: Optional[str] = None
    ) -> List[GuardarropiaItemSummary]:
        """
        Obtiene todos los items, opcionalmente filtrados.
        
        Args:
            status: Estado del item (opcional)
            shift_date: Fecha del turno (opcional)
            
        Returns:
            Lista de GuardarropiaItemSummary
        """
        try:
            if shift_date:
                items = self.repository.find_by_shift_date(shift_date)
                if status:
                    items = [item for item in items if item.status == status]
            else:
                items = self.repository.find_all(status=status)
            
            return [self._item_to_summary(item) for item in items]
        except Exception as e:
            current_app.logger.error(f"Error al obtener items: {e}")
            return []
    
    def get_occupied_clusters(self) -> List[int]:
        """
        Obtiene la lista de números de clusters ocupados.
        
        Returns:
            Lista de números de clusters ocupados (ej: [1, 5, 10])
        """
        try:
            from app.models import db
            
            # Obtener todos los items depositados (no retirados ni perdidos)
            items = GuardarropiaItem.query.filter_by(status='deposited').all()
            
            occupied = set()
            for item in items:
                if item.cluster_numbers:
                    # Parsear números de clusters (formato: "1,2,3" o "1, 2, 3")
                    cluster_nums = [int(c.strip()) for c in item.cluster_numbers.split(',') if c.strip().isdigit()]
                    occupied.update(cluster_nums)
            
            return sorted(list(occupied))
        except Exception as e:
            current_app.logger.error(f"Error al obtener clusters ocupados: {e}", exc_info=True)
            return []
    
    def get_occupied_cluster_numbers(self, shift_date: Optional[str] = None) -> List[int]:
        """
        Obtiene la lista de números de clusters ocupados, opcionalmente filtrados por fecha.
        Excluye items eliminados (soft delete).
        
        Args:
            shift_date: Fecha del turno (opcional)
        
        Returns:
            Lista de números de clusters ocupados (ej: [1, 5, 10])
        """
        try:
            from app.models import db
            from sqlalchemy import or_
            
            # Obtener items depositados (no retirados ni perdidos) y NO eliminados
            query = GuardarropiaItem.query.filter_by(status='deposited')
            if shift_date:
                query = query.filter_by(shift_date=shift_date)
            # Excluir items eliminados (tienen [ELIMINADO] en notas)
            query = query.filter(
                or_(
                    GuardarropiaItem.notes.is_(None),
                    ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
                )
            )
            items = query.all()
            
            occupied = set()
            for item in items:
                if item.cluster_numbers:
                    # Parsear números de clusters (formato: "1,2,3" o "1, 2, 3")
                    cluster_nums = [int(c.strip()) for c in item.cluster_numbers.split(',') if c.strip().isdigit()]
                    occupied.update(cluster_nums)
            
            return sorted(list(occupied))
        except Exception as e:
            current_app.logger.error(f"Error al obtener clusters ocupados: {e}", exc_info=True)
            return []
    
    def get_cluster_info(self, shift_date: Optional[str] = None) -> Dict[int, List[Dict]]:
        """
        Obtiene información detallada de cada cluster ocupado.
        Excluye items eliminados (soft delete).
        
        Args:
            shift_date: Fecha del turno (opcional)
        
        Returns:
            Dict con información: {cluster_num: [{'ticket_code': ..., 'customer_name': ..., ...}, ...]}
        """
        try:
            from app.models import db
            from sqlalchemy import or_
            
            # Obtener todos los items depositados y NO eliminados
            query = GuardarropiaItem.query.filter_by(status='deposited')
            if shift_date:
                query = query.filter_by(shift_date=shift_date)
            # Excluir items eliminados (tienen [ELIMINADO] en notas)
            query = query.filter(
                or_(
                    GuardarropiaItem.notes.is_(None),
                    ~GuardarropiaItem.notes.like('%[ELIMINADO]%')
                )
            )
            items = query.all()
            
            cluster_info = {}
            for item in items:
                if item.cluster_numbers:
                    # Parsear números de clusters
                    cluster_nums = [int(c.strip()) for c in item.cluster_numbers.split(',') if c.strip().isdigit()]
                    for cluster_num in cluster_nums:
                        if cluster_num not in cluster_info:
                            cluster_info[cluster_num] = []
                        cluster_info[cluster_num].append({
                            'ticket_code': item.ticket_code,
                            'customer_name': item.customer_name or 'Sin nombre',
                            'customer_phone': item.customer_phone or '-',
                            'description': item.description or '-',
                            'price': float(item.price) if item.price else 0,
                            'deposited_at': item.deposited_at.isoformat() if item.deposited_at else None
                        })
            
            return cluster_info
        except Exception as e:
            current_app.logger.error(f"Error al obtener información de clusters: {e}", exc_info=True)
            return {}
    
    def get_available_clusters(self, count: int = 1) -> List[int]:
        """
        Obtiene una lista de clusters disponibles.
        
        Args:
            count: Cantidad de clusters a obtener
            
        Returns:
            Lista de números de clusters disponibles
        """
        occupied = set(self.get_occupied_clusters())
        all_clusters = set(range(1, 91))  # Clusters del 1 al 90
        available = sorted(list(all_clusters - occupied))
        
        return available[:count] if count > 0 else available
    
    def get_stats(
        self,
        shift_date: Optional[str] = None
    ) -> GuardarropiaStats:
        """
        Obtiene estadísticas mejoradas de guardarropía.
        
        Args:
            shift_date: Fecha del turno (opcional)
            
        Returns:
            GuardarropiaStats con las estadísticas mejoradas
        """
        try:
            from sqlalchemy import func
            from app.models import db
            from datetime import datetime, timedelta
            from sqlalchemy import or_
            
            # Estadísticas básicas
            total_deposited = self.repository.count_by_status('deposited', shift_date)
            total_retrieved = self.repository.count_by_status('retrieved', shift_date)
            total_lost = self.repository.count_by_status('lost', shift_date)
            
            # Los actualmente almacenados son los depositados que no fueron retirados ni perdidos
            currently_stored = self.repository.find_deposited(shift_date)
            currently_stored_count = len(currently_stored)
            
            # Calcular ingresos
            query = GuardarropiaItem.query
            if shift_date:
                query = query.filter_by(shift_date=shift_date)
            
            # Ingresos totales
            revenue_result = db.session.query(func.sum(GuardarropiaItem.price)).filter(
                GuardarropiaItem.price.isnot(None),
                GuardarropiaItem.price > 0
            )
            if shift_date:
                revenue_result = revenue_result.filter_by(shift_date=shift_date)
            
            total_revenue = float(revenue_result.scalar() or 0)
            
            # Ingresos por tipo de pago
            revenue_cash_query = db.session.query(func.sum(GuardarropiaItem.price)).filter(
                GuardarropiaItem.price.isnot(None),
                GuardarropiaItem.price > 0
            ).filter(
                or_(
                    GuardarropiaItem.payment_type == 'cash',
                    GuardarropiaItem.payment_type == 'efectivo'
                )
            )
            if shift_date:
                revenue_cash_query = revenue_cash_query.filter_by(shift_date=shift_date)
            revenue_cash = float(revenue_cash_query.scalar() or 0)
            
            revenue_debit_query = db.session.query(func.sum(GuardarropiaItem.price)).filter(
                GuardarropiaItem.price.isnot(None),
                GuardarropiaItem.price > 0
            ).filter(
                or_(
                    GuardarropiaItem.payment_type == 'debit',
                    GuardarropiaItem.payment_type == 'débito'
                )
            )
            if shift_date:
                revenue_debit_query = revenue_debit_query.filter_by(shift_date=shift_date)
            revenue_debit = float(revenue_debit_query.scalar() or 0)
            
            revenue_credit_query = db.session.query(func.sum(GuardarropiaItem.price)).filter(
                GuardarropiaItem.price.isnot(None),
                GuardarropiaItem.price > 0
            ).filter(
                or_(
                    GuardarropiaItem.payment_type == 'credit',
                    GuardarropiaItem.payment_type == 'crédito'
                )
            )
            if shift_date:
                revenue_credit_query = revenue_credit_query.filter_by(shift_date=shift_date)
            revenue_credit = float(revenue_credit_query.scalar() or 0)
            
            # Espacios disponibles (90 total)
            spaces_available = max(0, 90 - currently_stored_count)
            spaces_occupied = currently_stored_count
            
            # Items del día/turno
            if shift_date:
                items_today = self.repository.count_by_status('deposited', shift_date)
                items_retrieved_today = self.repository.count_by_status('retrieved', shift_date)
            else:
                # Si no hay shift_date, usar fecha de hoy
                today = datetime.now().strftime('%Y-%m-%d')
                items_today = self.repository.count_by_status('deposited', today)
                items_retrieved_today = self.repository.count_by_status('retrieved', today)
            
            # Calcular tiempo promedio de almacenamiento (solo para items retirados)
            retrieved_items = self.repository.find_all('retrieved')
            avg_deposit_time = None
            if retrieved_items:
                total_hours = 0
                count = 0
                for item in retrieved_items:
                    if item.deposited_at and item.retrieved_at:
                        try:
                            if isinstance(item.deposited_at, str):
                                deposited = datetime.fromisoformat(item.deposited_at.replace('Z', '+00:00'))
                            else:
                                deposited = item.deposited_at
                            
                            if isinstance(item.retrieved_at, str):
                                retrieved = datetime.fromisoformat(item.retrieved_at.replace('Z', '+00:00'))
                            else:
                                retrieved = item.retrieved_at
                            
                            diff = retrieved - deposited
                            total_hours += diff.total_seconds() / 3600
                            count += 1
                        except:
                            pass
                
                if count > 0:
                    avg_deposit_time = total_hours / count
            
            return GuardarropiaStats(
                total_deposited=total_deposited,
                total_retrieved=total_retrieved,
                total_lost=total_lost,
                currently_stored=currently_stored_count,
                shift_date=shift_date,
                total_revenue=total_revenue,
                revenue_today=total_revenue if shift_date else 0.0,
                revenue_cash=revenue_cash,
                revenue_debit=revenue_debit,
                revenue_credit=revenue_credit,
                spaces_available=spaces_available,
                spaces_occupied=spaces_occupied,
                avg_deposit_time=avg_deposit_time,
                items_today=items_today,
                items_retrieved_today=items_retrieved_today
            )
        except Exception as e:
            current_app.logger.error(f"Error al obtener estadísticas: {e}", exc_info=True)
            return GuardarropiaStats(
                total_deposited=0,
                total_retrieved=0,
                total_lost=0,
                currently_stored=0,
                shift_date=shift_date,
                total_revenue=0.0,
                revenue_today=0.0,
                revenue_cash=0.0,
                revenue_debit=0.0,
                revenue_credit=0.0,
                spaces_available=90,
                spaces_occupied=0,
                avg_deposit_time=None,
                items_today=0,
                items_retrieved_today=0
            )
    
    def _item_to_summary(self, item: GuardarropiaItem) -> GuardarropiaItemSummary:
        """Convierte un item a summary"""
        return GuardarropiaItemSummary(
            id=item.id,
            ticket_code=item.ticket_code,
            description=item.description,
            customer_name=item.customer_name,
            status=item.status,
            deposited_at=item.deposited_at.isoformat() if item.deposited_at else None,
            retrieved_at=item.retrieved_at.isoformat() if item.retrieved_at else None,
            deposited_by=item.deposited_by,
            retrieved_by=item.retrieved_by,
            shift_date=item.shift_date,
            price=float(item.price) if item.price else None,
            payment_type=item.payment_type,
            sale_id=item.sale_id,
            notes=item.notes,
            photo_path=item.photo_path,
            marked_unretrieved_at=item.marked_unretrieved_at.isoformat() if item.marked_unretrieved_at else None,
            marked_unretrieved_by=item.marked_unretrieved_by,
            tracking_notes=item.tracking_notes,
            last_tracking_date=item.last_tracking_date.isoformat() if item.last_tracking_date else None
        )

