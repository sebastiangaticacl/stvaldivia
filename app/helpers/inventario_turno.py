"""
Helper para cálculos de inventario durante turnos de bartenders
Calcula stock esperado, desviaciones y costos
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import current_app
from app.models import db
from app.models.bartender_turno_models import (
    BartenderTurno, TurnoStockInicial, TurnoStockFinal,
    TurnoDesviacionInventario
)
from app.models.inventory_stock_models import InventoryMovement, Ingredient
from app.models.sale_delivery_models import DeliveryItem
from decimal import Decimal


class InventarioTurnoHelper:
    """
    Helper para calcular:
    - Stock esperado al cierre del turno
    - Desviaciones entre esperado y reportado
    - Costos y valores del turno
    """
    
    def calcular_stock_esperado_turno(
        self,
        turno_id: int,
        insumo_id: int
    ) -> Decimal:
        """
        Calcula el stock esperado de un insumo al cierre del turno.
        
        Fórmula:
        STOCK_ESPERADO = STOCK_INICIAL_TURNO
                         + TRANSFERENCIAS_ENTRANTES
                         - CONSUMO_POR_RECETAS
                         - MERMAS_REGISTRADAS
        
        Args:
            turno_id: ID del turno
            insumo_id: ID del insumo
            
        Returns:
            Decimal: Stock esperado
        """
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return Decimal('0.0')
            
            # 1. Stock inicial del turno
            stock_inicial_reg = TurnoStockInicial.query.filter_by(
                turno_id=turno_id,
                insumo_id=insumo_id
            ).first()
            
            stock_inicial = Decimal('0.0')
            if stock_inicial_reg:
                stock_inicial = Decimal(str(stock_inicial_reg.cantidad_inicial))
            
            # 2. Transferencias entrantes (movimientos tipo 'entrada' o 'transferencia' durante el turno)
            transferencias_entrantes = Decimal('0.0')
            movimientos_entrada = InventoryMovement.query.filter(
                InventoryMovement.ingredient_id == insumo_id,
                InventoryMovement.location == turno.ubicacion,
                InventoryMovement.turno_id == turno_id,
                InventoryMovement.movement_type.in_(['entrada', 'transferencia']),
                InventoryMovement.quantity > 0
            ).all()
            
            for mov in movimientos_entrada:
                transferencias_entrantes += Decimal(str(mov.quantity))
            
            # 3. Consumo por recetas (movimientos tipo 'venta' o 'delivery' durante el turno)
            consumo_por_recetas = Decimal('0.0')
            movimientos_consumo = InventoryMovement.query.filter(
                InventoryMovement.ingredient_id == insumo_id,
                InventoryMovement.location == turno.ubicacion,
                InventoryMovement.turno_id == turno_id,
                InventoryMovement.movement_type.in_(['venta', 'delivery']),
                InventoryMovement.quantity < 0
            ).all()
            
            for mov in movimientos_consumo:
                # La cantidad es negativa, así que sumamos el valor absoluto
                consumo_por_recetas += abs(Decimal(str(mov.quantity)))
            
            # También buscar en DeliveryItem directamente (por si no se registró en InventoryMovement)
            from app.models.sale_delivery_models import SaleDeliveryStatus
            entregas_turno = db.session.query(DeliveryItem).join(
                SaleDeliveryStatus, DeliveryItem.sale_id == SaleDeliveryStatus.sale_id
            ).filter(
                DeliveryItem.location == turno.ubicacion,
                DeliveryItem.delivered_at >= turno.fecha_hora_apertura,
                DeliveryItem.delivered_at <= (turno.fecha_hora_cierre or datetime.utcnow())
            ).all()
            
            # Sumar consumo de ingredientes desde entregas
            for entrega in entregas_turno:
                if entrega.ingredients_consumed:
                    for consumo in entrega.ingredients_consumed:
                        # Buscar insumo por nombre (si no tenemos ID directo)
                        ingrediente_nombre = consumo.get('ingrediente', '')
                        ingrediente = Ingredient.query.filter_by(name=ingrediente_nombre).first()
                        if ingrediente and ingrediente.id == insumo_id:
                            cantidad_consumida = Decimal(str(consumo.get('cantidad', 0)))
                            consumo_por_recetas += cantidad_consumida
            
            # 4. Mermas registradas durante el turno
            from app.models.bartender_turno_models import MermaInventario
            mermas = MermaInventario.query.filter_by(
                turno_id=turno_id,
                insumo_id=insumo_id
            ).all()
            
            mermas_registradas = Decimal('0.0')
            for merma in mermas:
                mermas_registradas += Decimal(str(merma.cantidad_mermada))
            
            # Calcular stock esperado
            stock_esperado = stock_inicial + transferencias_entrantes - consumo_por_recetas - mermas_registradas
            
            return stock_esperado
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular stock esperado: {e}", exc_info=True)
            return Decimal('0.0')
    
    def calcular_desviaciones_turno(
        self,
        turno_id: int
    ) -> Tuple[bool, str, List[TurnoDesviacionInventario]]:
        """
        Calcula todas las desviaciones del turno comparando stock esperado vs final reportado.
        
        Args:
            turno_id: ID del turno
            
        Returns:
            Tuple[bool, str, List[TurnoDesviacionInventario]]
        """
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return False, "Turno no encontrado", []
            
            if turno.estado != 'cerrado':
                return False, "El turno debe estar cerrado para calcular desviaciones", []
            
            # Obtener todos los insumos con stock inicial
            stocks_iniciales = TurnoStockInicial.query.filter_by(turno_id=turno_id).all()
            
            desviaciones = []
            
            for stock_inicial in stocks_iniciales:
                insumo_id = stock_inicial.insumo_id
                
                # Obtener stock final reportado
                stock_final_reg = TurnoStockFinal.query.filter_by(
                    turno_id=turno_id,
                    insumo_id=insumo_id
                ).first()
                
                if not stock_final_reg:
                    current_app.logger.warning(f"No hay stock final para insumo {insumo_id} en turno {turno_id}")
                    continue
                
                # Calcular stock esperado
                stock_esperado = self.calcular_stock_esperado_turno(turno_id, insumo_id)
                
                # Obtener valores
                stock_inicial_val = Decimal(str(stock_inicial.cantidad_inicial))
                stock_esperado_val = stock_esperado
                stock_final_val = Decimal(str(stock_final_reg.cantidad_final))
                
                # Calcular diferencia
                diferencia_turno = stock_final_val - stock_esperado_val
                
                # Calcular diferencia porcentual (evitar división por cero)
                if stock_esperado_val > 0:
                    diferencia_porcentual = (diferencia_turno / stock_esperado_val) * Decimal('100')
                else:
                    diferencia_porcentual = Decimal('0.0') if diferencia_turno == 0 else Decimal('100.0')
                
                # Obtener costo unitario para calcular costo de diferencia
                costo_unitario = self._get_costo_unitario_actual(insumo_id, turno.ubicacion)
                costo_diferencia = diferencia_turno * costo_unitario
                
                # Determinar tipo de desviación
                tipo = self._determinar_tipo_desviacion(diferencia_turno, diferencia_porcentual, costo_diferencia)
                
                # Crear o actualizar registro de desviación
                desviacion = TurnoDesviacionInventario.query.filter_by(
                    turno_id=turno_id,
                    insumo_id=insumo_id
                ).first()
                
                if desviacion:
                    desviacion.stock_inicial_turno = stock_inicial_val
                    desviacion.stock_esperado_turno = stock_esperado_val
                    desviacion.stock_final_reportado = stock_final_val
                    desviacion.diferencia_turno = diferencia_turno
                    desviacion.diferencia_porcentual_turno = diferencia_porcentual
                    desviacion.costo_diferencia = costo_diferencia
                    desviacion.tipo = tipo
                else:
                    desviacion = TurnoDesviacionInventario(
                        turno_id=turno_id,
                        insumo_id=insumo_id,
                        ubicacion=turno.ubicacion,
                        stock_inicial_turno=stock_inicial_val,
                        stock_esperado_turno=stock_esperado_val,
                        stock_final_reportado=stock_final_val,
                        diferencia_turno=diferencia_turno,
                        diferencia_porcentual_turno=diferencia_porcentual,
                        costo_diferencia=costo_diferencia,
                        tipo=tipo
                    )
                    db.session.add(desviacion)
                
                desviaciones.append(desviacion)
            
            db.session.commit()
            
            return True, f"Desviaciones calculadas: {len(desviaciones)} insumos", desviaciones
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al calcular desviaciones: {e}", exc_info=True)
            return False, f"Error al calcular desviaciones: {str(e)}", []
    
    def calcular_resumen_financiero_turno(
        self,
        turno_id: int
    ) -> Dict[str, Any]:
        """
        Calcula el resumen financiero completo del turno.
        
        Returns:
            Dict con valores calculados
        """
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return {}
            
            # Valores ya guardados en el turno
            valor_inicial = Decimal(str(turno.valor_inicial_barra_costo)) if turno.valor_inicial_barra_costo else Decimal('0.0')
            valor_final = Decimal(str(turno.valor_final_barra_costo)) if turno.valor_final_barra_costo else Decimal('0.0')
            
            # Valor vendido (venta)
            valor_vendido_venta = self._calcular_valor_vendido_venta(turno_id)
            
            # Valor vendido (costo teórico)
            valor_vendido_costo = self._calcular_valor_vendido_costo(turno_id)
            
            # Valor de merma
            valor_merma = self._calcular_valor_merma(turno_id)
            
            # Valor de pérdida no justificada (suma de costos de diferencia negativos)
            valor_perdida_no_justificada = self._calcular_valor_perdida_no_justificada(turno_id)
            
            return {
                'valor_inicial_barra_costo': float(valor_inicial),
                'valor_final_barra_costo': float(valor_final),
                'valor_vendido_venta': float(valor_vendido_venta),
                'valor_vendido_costo': float(valor_vendido_costo),
                'valor_merma_costo': float(valor_merma),
                'valor_perdida_no_justificada_costo': float(valor_perdida_no_justificada),
                'margen_bruto': float(valor_vendido_venta - valor_vendido_costo),
                'margen_bruto_porcentual': float(((valor_vendido_venta - valor_vendido_costo) / valor_vendido_venta * 100) if valor_vendido_venta > 0 else 0)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular resumen financiero: {e}", exc_info=True)
            return {}
    
    def _calcular_valor_vendido_venta(self, turno_id: int) -> Decimal:
        """Calcula el valor de venta de productos entregados en el turno"""
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return Decimal('0.0')
            
            # Buscar entregas del turno
            entregas = DeliveryItem.query.filter(
                DeliveryItem.location == turno.ubicacion,
                DeliveryItem.delivered_at >= turno.fecha_hora_apertura,
                DeliveryItem.delivered_at <= (turno.fecha_hora_cierre or datetime.utcnow())
            ).all()
            
            valor_total = Decimal('0.0')
            
            # Obtener precios de productos desde PosSale
            from app.models.pos_models import PosSale, PosSaleItem
            
            for entrega in entregas:
                # Buscar venta asociada
                sale = PosSale.query.filter_by(sale_id_phppos=entrega.sale_id).first()
                if sale:
                    # Buscar item en la venta
                    item = PosSaleItem.query.filter_by(
                        sale_id=sale.id,
                        product_name=entrega.product_name
                    ).first()
                    
                    if item:
                        precio_unitario = Decimal(str(item.unit_price))
                        cantidad = Decimal(str(entrega.quantity_delivered))
                        valor_total += precio_unitario * cantidad
            
            return valor_total
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular valor vendido venta: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _calcular_valor_vendido_costo(self, turno_id: int) -> Decimal:
        """Calcula el costo teórico de productos entregados usando recetas"""
        try:
            turno = BartenderTurno.query.get(turno_id)
            if not turno:
                return Decimal('0.0')
            
            # Sumar costos de ingredientes consumidos en entregas
            entregas = DeliveryItem.query.filter(
                DeliveryItem.location == turno.ubicacion,
                DeliveryItem.delivered_at >= turno.fecha_hora_apertura,
                DeliveryItem.delivered_at <= (turno.fecha_hora_cierre or datetime.utcnow())
            ).all()
            
            valor_total = Decimal('0.0')
            
            for entrega in entregas:
                if entrega.ingredients_consumed:
                    for consumo in entrega.ingredients_consumed:
                        ingrediente_nombre = consumo.get('ingrediente', '')
                        cantidad = Decimal(str(consumo.get('cantidad', 0)))
                        
                        # Buscar insumo y su costo
                        ingrediente = Ingredient.query.filter_by(name=ingrediente_nombre).first()
                        if ingrediente:
                            costo_unitario = self._get_costo_unitario_actual(ingrediente.id, turno.ubicacion)
                            valor_total += cantidad * costo_unitario
            
            return valor_total
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular valor vendido costo: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _calcular_valor_merma(self, turno_id: int) -> Decimal:
        """Calcula el valor total de merma registrada en el turno"""
        try:
            from app.models.bartender_turno_models import MermaInventario
            
            mermas = MermaInventario.query.filter_by(turno_id=turno_id).all()
            
            valor_total = Decimal('0.0')
            for merma in mermas:
                valor_total += Decimal(str(merma.costo_merma))
            
            return valor_total
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular valor merma: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _calcular_valor_perdida_no_justificada(self, turno_id: int) -> Decimal:
        """Calcula el valor de pérdida no justificada (desviaciones negativas)"""
        try:
            desviaciones = TurnoDesviacionInventario.query.filter_by(turno_id=turno_id).all()
            
            valor_total = Decimal('0.0')
            for desviacion in desviaciones:
                # Solo sumar diferencias negativas (pérdidas)
                if desviacion.diferencia_turno < 0:
                    valor_total += abs(Decimal(str(desviacion.costo_diferencia)))
            
            return valor_total
            
        except Exception as e:
            current_app.logger.error(f"Error al calcular valor pérdida no justificada: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _get_costo_unitario_actual(self, insumo_id: int, ubicacion: str) -> Decimal:
        """Obtiene el costo unitario actual de un insumo"""
        try:
            insumo = Ingredient.query.get(insumo_id)
            if not insumo:
                return Decimal('0.0')
            
            if insumo.cost_per_unit:
                return Decimal(str(insumo.cost_per_unit))
            
            return Decimal('0.0')
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener costo unitario: {e}", exc_info=True)
            return Decimal('0.0')
    
    def _determinar_tipo_desviacion(
        self,
        diferencia: Decimal,
        diferencia_porcentual: Decimal,
        costo_diferencia: Decimal
    ) -> str:
        """
        Determina el tipo de desviación basado en la diferencia.
        
        Returns:
            "normal", "perdida", "ganancia", "perdida_critica", "ganancia_rara"
        """
        if diferencia == 0:
            return "normal"
        
        if diferencia < 0:
            # Pérdida
            if abs(diferencia_porcentual) > 5 or abs(costo_diferencia) > 10000:  # Umbrales configurables
                return "perdida_critica"
            return "perdida"
        else:
            # Ganancia (raro, pero posible)
            if abs(diferencia_porcentual) > 5:
                return "ganancia_rara"
            return "ganancia"
    
    def get_resumen_desviaciones_turno(self, turno_id: int) -> Dict[str, Any]:
        """
        Obtiene un resumen de las desviaciones del turno.
        
        Returns:
            Dict con estadísticas de desviaciones
        """
        try:
            desviaciones = TurnoDesviacionInventario.query.filter_by(turno_id=turno_id).all()
            
            if not desviaciones:
                return {
                    'total_insumos': 0,
                    'insumos_normales': 0,
                    'insumos_con_perdida': 0,
                    'insumos_con_ganancia': 0,
                    'insumos_criticos': 0,
                    'total_perdida_costo': 0.0,
                    'total_ganancia_costo': 0.0,
                    'promedio_desviacion_porcentual': 0.0
                }
            
            total_perdida = sum(float(d.costo_diferencia) for d in desviaciones if d.es_perdida())
            total_ganancia = sum(float(d.costo_diferencia) for d in desviaciones if d.es_ganancia())
            desviaciones_porc = [abs(float(d.diferencia_porcentual_turno)) for d in desviaciones]
            
            return {
                'total_insumos': len(desviaciones),
                'insumos_normales': sum(1 for d in desviaciones if d.es_normal()),
                'insumos_con_perdida': sum(1 for d in desviaciones if d.es_perdida()),
                'insumos_con_ganancia': sum(1 for d in desviaciones if d.es_ganancia()),
                'insumos_criticos': sum(1 for d in desviaciones if d.tipo == 'perdida_critica'),
                'total_perdida_costo': abs(total_perdida),
                'total_ganancia_costo': total_ganancia,
                'promedio_desviacion_porcentual': sum(desviaciones_porc) / len(desviaciones_porc) if desviaciones_porc else 0.0
            }
            
        except Exception as e:
            current_app.logger.error(f"Error al obtener resumen de desviaciones: {e}", exc_info=True)
            return {}


def get_inventario_turno_helper() -> InventarioTurnoHelper:
    """Factory function para obtener instancia del helper"""
    return InventarioTurnoHelper()





