"""
Helper para gestión de turnos de bartenders
Lógica de apertura y cierre de turnos con control de stock
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import current_app
from app.models import db
from app.models.bartender_turno_models import (
    BartenderTurno, TurnoStockInicial, TurnoStockFinal
)
from app.models.inventory_stock_models import Ingredient, IngredientStock
from decimal import Decimal


class TurnosBartenderHelper:
    """
    Helper para gestionar turnos de bartenders:
    - Apertura de turno con confirmación de stock inicial
    - Cierre de turno con declaración de stock final
    """
    
    UBICACIONES_VALIDAS = ['barra_pista', 'barra_terraza']
    
    def abrir_turno(
        self,
        bartender_id: str,
        bartender_name: str,
        ubicacion: str,
        stock_inicial: List[Dict[str, Any]],  # [{"insumo_id": 1, "cantidad": 100.5}, ...]
        observaciones: Optional[str] = None
    ) -> Tuple[bool, str, Optional[BartenderTurno]]:
        """
        Abre un nuevo turno para un bartender.
        
        Args:
            bartender_id: ID del bartender
            bartender_name: Nombre del bartender
            ubicacion: "barra_pista" o "barra_terraza"
            stock_inicial: Lista de insumos con cantidades iniciales
            observaciones: Observaciones opcionales
            
        Returns:
            Tuple[bool, str, Optional[BartenderTurno]]
        """
        try:
            # Validar ubicación
            if ubicacion not in self.UBICACIONES_VALIDAS:
                return False, f"Ubicación inválida. Debe ser: {', '.join(self.UBICACIONES_VALIDAS)}", None
            
            # Verificar si hay un turno abierto para este bartender en esta ubicación
            turno_abierto = BartenderTurno.query.filter_by(
                bartender_id=bartender_id,
                ubicacion=ubicacion,
                estado='abierto'
            ).first()
            
            if turno_abierto:
                return False, f"Ya existe un turno abierto para {bartender_name} en {ubicacion}", None
            
            # Crear nuevo turno
            turno = BartenderTurno(
                bartender_id=bartender_id,
                bartender_name=bartender_name,
                ubicacion=ubicacion,
                fecha_hora_apertura=datetime.utcnow(),
                estado='abierto',
                observaciones_apertura=observaciones
            )
            
            db.session.add(turno)
            db.session.flush()  # Para obtener el ID
            
            # Registrar stock inicial
            valor_total_inicial = Decimal('0.0')
            
            for item in stock_inicial:
                insumo_id = item.get('insumo_id')
                cantidad = Decimal(str(item.get('cantidad', 0)))
                
                if not insumo_id or cantidad <= 0:
                    continue
                
                # Obtener insumo y su costo unitario
                insumo = Ingredient.query.get(insumo_id)
                if not insumo:
                    current_app.logger.warning(f"Insumo {insumo_id} no encontrado, saltando...")
                    continue
                
                # Obtener costo unitario actual
                costo_unitario = self._get_costo_unitario_actual(insumo_id, ubicacion)
                valor_costo = cantidad * costo_unitario
                valor_total_inicial += valor_costo
                
                # Obtener stock teórico actual de la ubicación
                stock_teorico = self._get_stock_teorico_ubicacion(insumo_id, ubicacion)
                diferencia_con_teorico = cantidad - stock_teorico
                
                # Crear registro de stock inicial
                stock_inicial_reg = TurnoStockInicial(
                    turno_id=turno.id,
                    insumo_id=insumo_id,
                    cantidad_inicial=cantidad,
                    valor_costo_inicial=valor_costo,
                    diferencia_con_teorico=diferencia_con_teorico
                )
                
                db.session.add(stock_inicial_reg)
            
            # Guardar valor total inicial
            turno.valor_inicial_barra_costo = valor_total_inicial
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Turno abierto: {bartender_name} - {ubicacion} (ID: {turno.id})")
            
            return True, f"Turno abierto exitosamente", turno
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al abrir turno: {e}", exc_info=True)
            return False, f"Error al abrir turno: {str(e)}", None
    
    def cerrar_turno(
        self,
        turno_id: int,
        stock_final: List[Dict[str, Any]],  # [{"insumo_id": 1, "cantidad": 80.5}, ...]
        observaciones: Optional[str] = None
    ) -> Tuple[bool, str, Optional[BartenderTurno]]:
        """
        Cierra un turno registrando el stock final.
        
        Args:
            turno_id: ID del turno a cerrar
            stock_final: Lista de insumos con cantidades finales
            observaciones: Observaciones opcionales
            
        Returns:
            Tuple[bool, str, Optional[BartenderTurno]]
        """
        try:
            # Obtener turno
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return False, "Turno no encontrado", None
            
            if turno.estado != 'abierto':
                return False, f"El turno ya está {turno.estado}", None
            
            # Verificar que existe stock inicial
            stock_inicial_count = TurnoStockInicial.query.filter_by(turno_id=turno_id).count()
            if stock_inicial_count == 0:
                return False, "No se puede cerrar un turno sin stock inicial registrado", None
            
            # Registrar stock final
            valor_total_final = Decimal('0.0')
            
            for item in stock_final:
                insumo_id = item.get('insumo_id')
                cantidad = Decimal(str(item.get('cantidad', 0)))
                
                if not insumo_id:
                    continue
                
                # Obtener insumo
                insumo = Ingredient.query.get(insumo_id)
                if not insumo:
                    current_app.logger.warning(f"Insumo {insumo_id} no encontrado, saltando...")
                    continue
                
                # Obtener costo unitario actual
                costo_unitario = self._get_costo_unitario_actual(insumo_id, turno.ubicacion)
                valor_costo = cantidad * costo_unitario
                valor_total_final += valor_costo
                
                # Crear o actualizar registro de stock final
                stock_final_reg = TurnoStockFinal.query.filter_by(
                    turno_id=turno_id,
                    insumo_id=insumo_id
                ).first()
                
                if stock_final_reg:
                    stock_final_reg.cantidad_final = cantidad
                    stock_final_reg.valor_costo_final = valor_costo
                else:
                    stock_final_reg = TurnoStockFinal(
                        turno_id=turno_id,
                        insumo_id=insumo_id,
                        cantidad_final=cantidad,
                        valor_costo_final=valor_costo
                    )
                    db.session.add(stock_final_reg)
            
            # Actualizar turno
            turno.fecha_hora_cierre = datetime.utcnow()
            turno.estado = 'cerrado'
            turno.observaciones_cierre = observaciones
            turno.valor_final_barra_costo = valor_total_final
            
            db.session.commit()
            
            current_app.logger.info(f"✅ Turno cerrado: {turno.bartender_name} - {turno.ubicacion} (ID: {turno.id})")
            
            return True, "Turno cerrado exitosamente", turno
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al cerrar turno: {e}", exc_info=True)
            return False, f"Error al cerrar turno: {str(e)}", None
    
    def get_turno_abierto(self, bartender_id: str, ubicacion: str) -> Optional[BartenderTurno]:
        """Obtiene el turno abierto de un bartender en una ubicación"""
        return BartenderTurno.query.filter_by(
            bartender_id=bartender_id,
            ubicacion=ubicacion,
            estado='abierto'
        ).first()
    
    def get_stock_sugerido(self, ubicacion: str) -> List[Dict[str, Any]]:
        """
        Obtiene el stock actual de la ubicación para sugerir al abrir turno.
        
        Returns:
            Lista de insumos con stock actual
        """
        try:
            # Obtener todos los insumos activos con stock en la ubicación
            stocks = IngredientStock.query.filter_by(
                location=ubicacion
            ).join(Ingredient).filter(
                Ingredient.is_active == True
            ).all()
            
            resultado = []
            for stock in stocks:
                resultado.append({
                    'insumo_id': stock.ingredient_id,
                    'insumo_nombre': stock.ingredient.name if stock.ingredient else '',
                    'cantidad_actual': float(stock.quantity) if stock.quantity else 0.0,
                    'unidad': stock.ingredient.base_unit if stock.ingredient else '',
                    'costo_unitario': float(self._get_costo_unitario_actual(stock.ingredient_id, ubicacion))
                })
            
            return resultado
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener stock sugerido: {e}", exc_info=True)
            return []
    
    def _get_costo_unitario_actual(self, insumo_id: int, ubicacion: str) -> Decimal:
        """Obtiene el costo unitario actual de un insumo"""
        try:
            insumo = Ingredient.query.get(insumo_id)
            if not insumo:
                return Decimal('0.0')
            
            # Usar costo por unidad base del insumo
            if insumo.cost_per_unit:
                return Decimal(str(insumo.cost_per_unit))
            
            return Decimal('0.0')
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener costo unitario: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _get_stock_teorico_ubicacion(self, insumo_id: int, ubicacion: str) -> Decimal:
        """Obtiene el stock teórico actual de un insumo en una ubicación"""
        try:
            stock = IngredientStock.query.filter_by(
                ingredient_id=insumo_id,
                location=ubicacion
            ).first()
            
            if stock and stock.quantity:
                return Decimal(str(stock.quantity))
            
            return Decimal('0.0')
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener stock teórico: {e}", exc_info=True)
            return Decimal('0.0')
    
    def validar_stock_inicial(self, stock_inicial: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Valida que el stock inicial sea válido.
        
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if not stock_inicial:
            return False, "Debe ingresar al menos un insumo con stock inicial"
        
        insumos_ids = set()
        for item in stock_inicial:
            insumo_id = item.get('insumo_id')
            cantidad = item.get('cantidad', 0)
            
            if not insumo_id:
                return False, "Todos los items deben tener un insumo_id válido"
            
            if insumo_id in insumos_ids:
                return False, f"El insumo {insumo_id} está duplicado en el stock inicial"
            
            insumos_ids.add(insumo_id)
            
            if cantidad < 0:
                return False, f"La cantidad del insumo {insumo_id} no puede ser negativa"
            
            # Verificar que el insumo existe
            insumo = Ingredient.query.get(insumo_id)
            if not insumo:
                return False, f"El insumo {insumo_id} no existe"
            
            if not insumo.is_active:
                return False, f"El insumo {insumo_id} está inactivo"
        
        return True, "OK"
    
    def validar_stock_final(self, turno_id: int, stock_final: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Valida que el stock final sea válido y completo.
        
        Returns:
            Tuple[bool, str]: (es_valido, mensaje_error)
        """
        if not stock_final:
            return False, "Debe ingresar el stock final de todos los insumos"
        
        # Obtener stock inicial del turno
        stock_inicial = TurnoStockInicial.query.filter_by(turno_id=turno_id).all()
        insumos_iniciales = {s.insumo_id for s in stock_inicial}
        
        if not insumos_iniciales:
            return False, "El turno no tiene stock inicial registrado"
        
        insumos_finales = set()
        for item in stock_final:
            insumo_id = item.get('insumo_id')
            cantidad = item.get('cantidad', 0)
            
            if not insumo_id:
                return False, "Todos los items deben tener un insumo_id válido"
            
            if insumo_id in insumos_finales:
                return False, f"El insumo {insumo_id} está duplicado en el stock final"
            
            insumos_finales.add(insumo_id)
            
            if cantidad < 0:
                return False, f"La cantidad del insumo {insumo_id} no puede ser negativa"
            
            # Verificar que el insumo existe y estaba en el stock inicial
            if insumo_id not in insumos_iniciales:
                return False, f"El insumo {insumo_id} no estaba en el stock inicial del turno"
        
        # Verificar que todos los insumos iniciales tengan stock final
        faltantes = insumos_iniciales - insumos_finales
        if faltantes:
            nombres_faltantes = []
            for insumo_id in faltantes:
                insumo = Ingredient.query.get(insumo_id)
                nombres_faltantes.append(insumo.name if insumo else f"Insumo {insumo_id}")
            return False, f"Faltan {len(faltantes)} insumos en el stock final: {', '.join(nombres_faltantes[:5])}"
        
        return True, "OK"
    
    def get_turnos_por_bartender(
        self,
        bartender_id: str,
        estado: Optional[str] = None,
        limit: int = 50
    ) -> List[BartenderTurno]:
        """
        Obtiene turnos de un bartender con filtros opcionales.
        
        Args:
            bartender_id: ID del bartender
            estado: Filtrar por estado ('abierto', 'cerrado') o None para todos
            limit: Límite de resultados
            
        Returns:
            Lista de turnos ordenados por fecha de apertura descendente
        """
        query = BartenderTurno.query.filter_by(bartender_id=bartender_id)
        
        if estado:
            query = query.filter_by(estado=estado)
        
        return query.order_by(BartenderTurno.fecha_hora_apertura.desc()).limit(limit).all()
    
    def get_turnos_por_ubicacion(
        self,
        ubicacion: str,
        estado: Optional[str] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        limit: int = 100
    ) -> List[BartenderTurno]:
        """
        Obtiene turnos de una ubicación con filtros opcionales.
        
        Args:
            ubicacion: Ubicación ('barra_pista' o 'barra_terraza')
            estado: Filtrar por estado
            fecha_desde: Fecha desde (opcional)
            fecha_hasta: Fecha hasta (opcional)
            limit: Límite de resultados
            
        Returns:
            Lista de turnos
        """
        query = BartenderTurno.query.filter_by(ubicacion=ubicacion)
        
        if estado:
            query = query.filter_by(estado=estado)
        
        if fecha_desde:
            query = query.filter(BartenderTurno.fecha_hora_apertura >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(BartenderTurno.fecha_hora_apertura <= fecha_hasta)
        
        return query.order_by(BartenderTurno.fecha_hora_apertura.desc()).limit(limit).all()
    
    def calcular_resumen_turno(self, turno: BartenderTurno) -> Tuple[bool, str]:
        """
        Calcula y guarda el resumen financiero completo del turno.
        Esta función debe llamarse al cerrar el turno.
        
        Args:
            turno: BartenderTurno a calcular
            
        Returns:
            Tuple[bool, str]: (éxito, mensaje)
        """
        try:
            from app.helpers.inventario_turno import get_inventario_turno_helper
            from app.helpers.alertas_turno import get_alertas_turno_helper
            from app.models.bartender_turno_models import (
                TurnoStockInicial, TurnoStockFinal, MermaInventario,
                TurnoDesviacionInventario, AlertaFugaTurno
            )
            from app.models.sale_delivery_models import DeliveryItem
            from app.models.inventory_stock_models import InventoryMovement
            from app.models.pos_models import PosSale, PosSaleItem
            from app.models.product_models import Product
            
            inventario_helper = get_inventario_turno_helper()
            
            # 1. Calcular valor_inicial_barra_costo
            stock_inicial_list = TurnoStockInicial.query.filter_by(turno_id=turno.id).all()
            valor_inicial = Decimal('0.0')
            for stock in stock_inicial_list:
                if stock.valor_costo_inicial:
                    valor_inicial += Decimal(str(stock.valor_costo_inicial))
            
            # 2. Calcular valor_final_barra_costo
            stock_final_list = TurnoStockFinal.query.filter_by(turno_id=turno.id).all()
            valor_final = Decimal('0.0')
            for stock in stock_final_list:
                if stock.valor_costo_final:
                    valor_final += Decimal(str(stock.valor_costo_final))
            
            # 3. Calcular valor_vendido_venta (precio de venta de productos entregados)
            valor_vendido_venta = Decimal('0.0')
            
            # Mapear ubicación del turno a formato de DeliveryItem
            # Los turnos usan: "barra_pista" o "barra_terraza"
            # DeliveryItem usa: "Barra Pista" o "Terraza"
            if turno.ubicacion == 'barra_pista':
                ubicacion_delivery = 'Barra Pista'
            elif turno.ubicacion == 'barra_terraza':
                ubicacion_delivery = 'Terraza'
            else:
                # Fallback: intentar convertir
                ubicacion_delivery = turno.ubicacion.replace('barra_', 'Barra ').title()
            
            entregas = DeliveryItem.query.filter(
                DeliveryItem.location == ubicacion_delivery,
                DeliveryItem.delivered_at >= turno.fecha_hora_apertura,
                DeliveryItem.delivered_at <= (turno.fecha_hora_cierre or datetime.utcnow())
            ).all()
            
            current_app.logger.info(f"📦 Encontradas {len(entregas)} entregas para turno {turno.id} en {ubicacion_delivery}")
            
            for entrega in entregas:
                # Buscar venta asociada
                sale = PosSale.query.filter_by(sale_id_phppos=entrega.sale_id).first()
                if not sale:
                    # Intentar buscar por ID local si sale_id tiene formato BMB
                    try:
                        if entrega.sale_id.startswith('BMB-'):
                            parts = entrega.sale_id.split('-')
                            if len(parts) >= 3:
                                local_id = int(parts[-1])
                                sale = PosSale.query.get(local_id)
                    except:
                        pass
                
                if sale:
                    # Buscar item en la venta
                    item = PosSaleItem.query.filter_by(
                        sale_id=sale.id,
                        product_name=entrega.product_name
                    ).first()
                    
                    if item:
                        precio_unitario = Decimal(str(item.unit_price))
                        cantidad = Decimal(str(entrega.quantity_delivered))
                        valor_vendido_venta += precio_unitario * cantidad
            
            # 4. Calcular valor_vendido_costo (costo de insumos usados en productos entregados)
            valor_vendido_costo = Decimal('0.0')
            
            # Método 1: Buscar movimientos de inventario asociados al turno
            movimientos_consumo = InventoryMovement.query.filter(
                InventoryMovement.turno_id == turno.id,
                InventoryMovement.movement_type == InventoryMovement.TYPE_SALE,
                InventoryMovement.quantity < 0
            ).all()
            
            current_app.logger.info(f"📊 Método 1: Encontrados {len(movimientos_consumo)} movimientos con turno_id={turno.id}")
            
            # Método 2: Si no hay movimientos con turno_id, calcular desde entregas y recetas
            if len(movimientos_consumo) == 0 and entregas:
                current_app.logger.info(f"📊 Método 2: Calculando costo desde entregas y recetas de BD")
                
                from app.models.inventory_stock_models import Recipe, RecipeIngredient
                from app.models.product_models import Product
                
                for entrega in entregas:
                    # Buscar producto
                    producto = Product.query.filter_by(name=entrega.product_name).first()
                    if not producto:
                        continue
                    
                    # Buscar receta del producto
                    receta = Recipe.query.filter_by(product_id=producto.id, is_active=True).first()
                    if not receta:
                        continue
                    
                    # Obtener ingredientes de la receta
                    ingredientes_receta = RecipeIngredient.query.filter_by(recipe_id=receta.id).all()
                    
                    cantidad_productos = Decimal(str(entrega.quantity_delivered))
                    
                    for rec_ing in ingredientes_receta:
                        ingrediente = rec_ing.ingredient
                        if ingrediente:
                            cantidad_por_porcion = Decimal(str(rec_ing.quantity_per_portion))
                            cantidad_total = cantidad_por_porcion * cantidad_productos
                            costo_unitario = self._get_costo_unitario_actual(ingrediente.id, turno.ubicacion)
                            costo_item = cantidad_total * costo_unitario
                            valor_vendido_costo += costo_item
                            
                            current_app.logger.info(
                                f"  - {ingrediente.name}: "
                                f"{float(cantidad_total):.2f} × ${float(costo_unitario):.2f} = ${float(costo_item):.2f} "
                                f"(para {float(cantidad_productos)}x {entrega.product_name})"
                            )
            
            # Método 3: Buscar movimientos por referencia de entregas (fallback)
            if valor_vendido_costo == 0 and entregas:
                sale_ids = [e.sale_id for e in entregas]
                movimientos_por_referencia = InventoryMovement.query.filter(
                    InventoryMovement.reference_type == 'delivery',
                    InventoryMovement.reference_id.in_(sale_ids),
                    InventoryMovement.movement_type == InventoryMovement.TYPE_SALE,
                    InventoryMovement.quantity < 0
                ).all()
                
                current_app.logger.info(f"📊 Método 3: Encontrados {len(movimientos_por_referencia)} movimientos por referencia")
                
                for mov in movimientos_por_referencia:
                    if mov.turno_id is None:
                        mov.turno_id = turno.id
                    cantidad_abs = abs(Decimal(str(mov.quantity)))
                    costo_unitario = self._get_costo_unitario_actual(mov.ingredient_id, turno.ubicacion)
                    costo_item = cantidad_abs * costo_unitario
                    valor_vendido_costo += costo_item
                
                if movimientos_por_referencia:
                    db.session.commit()
            
            # Si no hay movimientos con turno_id, buscar por fecha y ubicación
            if len(movimientos_consumo) == 0:
                current_app.logger.warning(f"⚠️  No se encontraron movimientos con turno_id={turno.id}, buscando por fecha/ubicación")
                
                # Buscar movimientos por fecha y ubicación (sin filtro de turno_id)
                movimientos_por_fecha = InventoryMovement.query.filter(
                    InventoryMovement.location == ubicacion_delivery,
                    InventoryMovement.movement_type == InventoryMovement.TYPE_SALE,
                    InventoryMovement.quantity < 0,
                    InventoryMovement.created_at >= turno.fecha_hora_apertura,
                    InventoryMovement.created_at <= (turno.fecha_hora_cierre or datetime.utcnow())
                ).all()
                
                current_app.logger.info(f"📊 Encontrados {len(movimientos_por_fecha)} movimientos por fecha/ubicación")
                
                # Asociar con turno y sumar costos
                for mov in movimientos_por_fecha:
                    cantidad_abs = abs(Decimal(str(mov.quantity)))
                    costo_unitario = self._get_costo_unitario_actual(mov.ingredient_id, turno.ubicacion)
                    costo_item = cantidad_abs * costo_unitario
                    valor_vendido_costo += costo_item
                    
                    # Asociar con turno para futuras consultas
                    if mov.turno_id is None:
                        mov.turno_id = turno.id
                    
                    ingrediente = Ingredient.query.get(mov.ingredient_id)
                    current_app.logger.info(
                        f"  - {ingrediente.name if ingrediente else 'Desconocido'}: "
                        f"{float(cantidad_abs):.2f} × ${float(costo_unitario):.2f} = ${float(costo_item):.2f}"
                    )
                
                # Usar movimientos_por_fecha como lista principal
                movimientos_consumo = movimientos_por_fecha
                
                # Commit para guardar los turno_id actualizados
                db.session.commit()
            else:
                # Procesar movimientos con turno_id
                for mov in movimientos_consumo:
                    cantidad_abs = abs(Decimal(str(mov.quantity)))
                    costo_unitario = self._get_costo_unitario_actual(mov.ingredient_id, turno.ubicacion)
                    costo_item = cantidad_abs * costo_unitario
                    valor_vendido_costo += costo_item
                    
                    ingrediente = Ingredient.query.get(mov.ingredient_id)
                    current_app.logger.info(
                        f"  - {ingrediente.name if ingrediente else 'Desconocido'}: "
                        f"{float(cantidad_abs):.2f} × ${float(costo_unitario):.2f} = ${float(costo_item):.2f}"
                    )
            
            current_app.logger.info(f"💰 valor_vendido_costo calculado: ${float(valor_vendido_costo):,.2f}")
            
            # 5. Calcular valor_merma_costo
            mermas = MermaInventario.query.filter_by(turno_id=turno.id).all()
            valor_merma = Decimal('0.0')
            for merma in mermas:
                if merma.costo_merma:
                    valor_merma += Decimal(str(merma.costo_merma))
            
            # 6. Calcular valor_perdida_no_justificada_costo (desviaciones negativas)
            desviaciones = TurnoDesviacionInventario.query.filter_by(turno_id=turno.id).all()
            valor_perdida_no_justificada = Decimal('0.0')
            for desviacion in desviaciones:
                if desviacion.diferencia_turno < 0:  # Solo pérdidas
                    costo_diff = abs(Decimal(str(desviacion.costo_diferencia)))
                    valor_perdida_no_justificada += costo_diff
            
            # 7. Determinar flag_fuga_critica
            alertas_criticas = AlertaFugaTurno.query.filter_by(
                turno_id=turno.id,
                criticidad='alta',
                atendida=False
            ).count()
            flag_fuga_critica = alertas_criticas > 0
            
            # Guardar valores en el turno
            turno.valor_inicial_barra_costo = valor_inicial
            turno.valor_final_barra_costo = valor_final
            turno.valor_vendido_venta = valor_vendido_venta
            turno.valor_vendido_costo = valor_vendido_costo
            turno.valor_merma_costo = valor_merma
            turno.valor_perdida_no_justificada_costo = valor_perdida_no_justificada
            turno.flag_fuga_critica = flag_fuga_critica
            
            db.session.commit()
            
            current_app.logger.info(
                f"✅ Resumen calculado para turno {turno.id}: "
                f"Venta=${valor_vendido_venta}, Costo=${valor_vendido_costo}, "
                f"Merma=${valor_merma}, Pérdida=${valor_perdida_no_justificada}"
            )
            
            return True, "Resumen calculado exitosamente"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al calcular resumen del turno: {e}", exc_info=True)
            return False, f"Error al calcular resumen: {str(e)}"
    
    def get_estadisticas_bartender(
        self,
        bartender_id: str,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Obtiene estadísticas de un bartender.
        
        Returns:
            Dict con estadísticas agregadas
        """
        query = BartenderTurno.query.filter_by(bartender_id=bartender_id, estado='cerrado')
        
        if fecha_desde:
            query = query.filter(BartenderTurno.fecha_hora_cierre >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(BartenderTurno.fecha_hora_cierre <= fecha_hasta)
        
        turnos = query.all()
        
        if not turnos:
            return {
                'total_turnos': 0,
                'promedio_duracion_minutos': 0,
                'total_ventas': 0.0,
                'total_perdidas': 0.0,
                'promedio_eficiencia': 0.0,
                'turnos_con_alertas': 0
            }
        
        total_ventas = sum(float(t.valor_vendido_venta) for t in turnos if t.valor_vendido_venta)
        total_perdidas = sum(t.get_total_perdidas() for t in turnos)
        duraciones = [t.get_duracion_minutos() for t in turnos if t.get_duracion_minutos()]
        eficiencias = [t.get_eficiencia_porcentual() for t in turnos if t.get_eficiencia_porcentual() is not None]
        turnos_con_alertas = sum(1 for t in turnos if t.flag_fuga_critica)
        
        return {
            'total_turnos': len(turnos),
            'promedio_duracion_minutos': sum(duraciones) / len(duraciones) if duraciones else 0,
            'total_ventas': total_ventas,
            'total_perdidas': total_perdidas,
            'promedio_eficiencia': sum(eficiencias) / len(eficiencias) if eficiencias else 0.0,
            'turnos_con_alertas': turnos_con_alertas,
            'porcentaje_turnos_con_alertas': (turnos_con_alertas / len(turnos) * 100) if turnos else 0.0
        }


def get_turnos_bartender_helper() -> TurnosBartenderHelper:
    """Factory function para obtener instancia del helper"""
    return TurnosBartenderHelper()





