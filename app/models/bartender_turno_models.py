"""
Modelos para gestión de turnos de bartenders con control de stock tipo "caja ciega"
Sistema de apertura y cierre con cálculo de desviaciones y alertas
"""
from datetime import datetime
from typing import Optional, Tuple, List
from . import db
from sqlalchemy import Index, Numeric, Text
from decimal import Decimal


class BartenderTurno(db.Model):
    """
    Turno de un bartender en una ubicación específica.
    Control tipo "caja ciega" con stock inicial y final.
    """
    __tablename__ = 'bartender_turnos'
    
    id = db.Column(db.Integer, primary_key=True)
    bartender_id = db.Column(db.String(100), nullable=False, index=True)
    bartender_name = db.Column(db.String(200), nullable=True)
    ubicacion = db.Column(db.String(50), nullable=False, index=True)  # "barra_pista" o "barra_terraza"
    
    # Fechas del turno
    fecha_hora_apertura = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    fecha_hora_cierre = db.Column(db.DateTime, nullable=True, index=True)
    
    # Estado del turno
    estado = db.Column(db.String(20), nullable=False, default='abierto', index=True)  # "abierto", "cerrado"
    
    # Observaciones
    observaciones_apertura = db.Column(Text, nullable=True)
    observaciones_cierre = db.Column(Text, nullable=True)
    
    # Resumen financiero del turno (calculado al cierre)
    valor_inicial_barra_costo = db.Column(Numeric(10, 2), nullable=True)  # Costo total del stock inicial
    valor_final_barra_costo = db.Column(Numeric(10, 2), nullable=True)  # Costo total del stock final
    valor_vendido_venta = db.Column(Numeric(10, 2), nullable=True)  # Valor de venta de productos entregados
    valor_vendido_costo = db.Column(Numeric(10, 2), nullable=True)  # Costo teórico de productos entregados
    valor_merma_costo = db.Column(Numeric(10, 2), nullable=True)  # Costo total de merma registrada
    valor_perdida_no_justificada_costo = db.Column(Numeric(10, 2), nullable=True)  # Pérdida por desviaciones
    flag_fuga_critica = db.Column(db.Boolean, default=False, nullable=False)  # True si hay alertas críticas
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    stock_inicial = db.relationship('TurnoStockInicial', backref='turno', lazy=True, cascade='all, delete-orphan')
    stock_final = db.relationship('TurnoStockFinal', backref='turno', lazy=True, cascade='all, delete-orphan')
    mermas = db.relationship('MermaInventario', backref='turno', lazy=True)
    desviaciones = db.relationship('TurnoDesviacionInventario', backref='turno', lazy=True)
    alertas = db.relationship('AlertaFugaTurno', backref='turno', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_bartender_turnos_bartender_fecha', 'bartender_id', 'fecha_hora_apertura'),
        Index('idx_bartender_turnos_ubicacion_estado', 'ubicacion', 'estado'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'bartender_id': self.bartender_id,
            'bartender_name': self.bartender_name,
            'ubicacion': self.ubicacion,
            'fecha_hora_apertura': self.fecha_hora_apertura.isoformat() if self.fecha_hora_apertura else None,
            'fecha_hora_cierre': self.fecha_hora_cierre.isoformat() if self.fecha_hora_cierre else None,
            'estado': self.estado,
            'observaciones_apertura': self.observaciones_apertura,
            'observaciones_cierre': self.observaciones_cierre,
            'valor_inicial_barra_costo': float(self.valor_inicial_barra_costo) if self.valor_inicial_barra_costo else None,
            'valor_final_barra_costo': float(self.valor_final_barra_costo) if self.valor_final_barra_costo else None,
            'valor_vendido_venta': float(self.valor_vendido_venta) if self.valor_vendido_venta else None,
            'valor_vendido_costo': float(self.valor_vendido_costo) if self.valor_vendido_costo else None,
            'valor_merma_costo': float(self.valor_merma_costo) if self.valor_merma_costo else None,
            'valor_perdida_no_justificada_costo': float(self.valor_perdida_no_justificada_costo) if self.valor_perdida_no_justificada_costo else None,
            'flag_fuga_critica': self.flag_fuga_critica
        }
    
    def is_open(self) -> bool:
        """Verifica si el turno está abierto"""
        return self.estado == 'abierto'
    
    def get_duracion_minutos(self) -> Optional[int]:
        """Calcula la duración del turno en minutos"""
        if not self.fecha_hora_cierre or not self.fecha_hora_apertura:
            return None
        delta = self.fecha_hora_cierre - self.fecha_hora_apertura
        return int(delta.total_seconds() / 60)
    
    def get_margen_bruto(self) -> Optional[float]:
        """Calcula el margen bruto del turno"""
        if not self.valor_vendido_venta or not self.valor_vendido_costo:
            return None
        return float(self.valor_vendido_venta - self.valor_vendido_costo)
    
    def get_margen_bruto_porcentual(self) -> Optional[float]:
        """Calcula el margen bruto porcentual"""
        if not self.valor_vendido_venta or self.valor_vendido_venta == 0:
            return None
        margen = self.get_margen_bruto()
        if margen is None:
            return None
        return (margen / float(self.valor_vendido_venta)) * 100
    
    def get_total_perdidas(self) -> float:
        """Calcula el total de pérdidas (merma + no justificada)"""
        merma = float(self.valor_merma_costo) if self.valor_merma_costo else 0.0
        no_justificada = float(self.valor_perdida_no_justificada_costo) if self.valor_perdida_no_justificada_costo else 0.0
        return merma + no_justificada
    
    def get_eficiencia_porcentual(self) -> Optional[float]:
        """Calcula la eficiencia del turno (ventas vs pérdidas)"""
        if not self.valor_vendido_venta or self.valor_vendido_venta == 0:
            return None
        perdidas = self.get_total_perdidas()
        return max(0, ((float(self.valor_vendido_venta) - perdidas) / float(self.valor_vendido_venta)) * 100)
    
    def tiene_alertas_criticas(self) -> bool:
        """Verifica si tiene alertas críticas no atendidas"""
        return any(not alerta.atendida and alerta.criticidad == 'alta' for alerta in self.alertas)
    
    def get_cantidad_insumos(self) -> int:
        """Obtiene la cantidad de insumos únicos en el turno"""
        return len(set(s.insumo_id for s in self.stock_inicial))
    
    def get_cantidad_alertas_pendientes(self) -> int:
        """Obtiene la cantidad de alertas pendientes"""
        return sum(1 for alerta in self.alertas if not alerta.atendida)
    
    def puede_cerrarse(self) -> Tuple[bool, str]:
        """
        Valida si el turno puede cerrarse.
        Returns:
            Tuple[bool, str]: (puede_cerrarse, mensaje_error)
        """
        if self.estado != 'abierto':
            return False, f"El turno ya está {self.estado}"
        
        if not self.stock_inicial:
            return False, "No se puede cerrar un turno sin stock inicial"
        
        if not self.stock_final:
            return False, "Debe registrar el stock final antes de cerrar"
        
        # Verificar que todos los insumos iniciales tengan stock final
        insumos_iniciales = {s.insumo_id for s in self.stock_inicial}
        insumos_finales = {s.insumo_id for s in self.stock_final}
        
        faltantes = insumos_iniciales - insumos_finales
        if faltantes:
            return False, f"Faltan {len(faltantes)} insumos en el stock final"
        
        return True, "OK"
    
    def __repr__(self):
        return f'<BartenderTurno {self.id}: {self.bartender_name} - {self.ubicacion} ({self.estado})>'


class TurnoStockInicial(db.Model):
    """
    Stock inicial de cada insumo al abrir el turno.
    """
    __tablename__ = 'turno_stock_inicial'
    
    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=False, index=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    
    # Cantidad inicial confirmada por el bartender
    cantidad_inicial = db.Column(Numeric(10, 3), nullable=False)  # En unidad base (ml, unidades, etc.)
    
    # Valor de costo inicial (para referencia histórica)
    valor_costo_inicial = db.Column(Numeric(10, 2), nullable=False)
    
    # Diferencia con stock teórico (para auditoría)
    diferencia_con_teorico = db.Column(Numeric(10, 3), nullable=True)  # Positivo si hay más, negativo si hay menos
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_turno_stock_inicial_turno_insumo', 'turno_id', 'insumo_id', unique=True),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'turno_id': self.turno_id,
            'insumo_id': self.insumo_id,
            'cantidad_inicial': float(self.cantidad_inicial) if self.cantidad_inicial else 0.0,
            'valor_costo_inicial': float(self.valor_costo_inicial) if self.valor_costo_inicial else 0.0,
            'diferencia_con_teorico': float(self.diferencia_con_teorico) if self.diferencia_con_teorico else None
        }
    
    def get_ajuste_porcentual(self) -> Optional[float]:
        """Calcula el porcentaje de ajuste respecto al stock teórico"""
        if self.diferencia_con_teorico is None:
            return None
        
        # Obtener stock teórico desde la diferencia
        stock_teorico = float(self.cantidad_inicial) - float(self.diferencia_con_teorico)
        if stock_teorico == 0:
            return None
        
        return (float(self.diferencia_con_teorico) / stock_teorico) * 100
    
    def __repr__(self):
        return f'<TurnoStockInicial {self.id}: Turno {self.turno_id} - Insumo {self.insumo_id}>'


class TurnoStockFinal(db.Model):
    """
    Stock final reportado por el bartender al cerrar el turno.
    """
    __tablename__ = 'turno_stock_final'
    
    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=False, index=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    
    # Cantidad final reportada por el bartender
    cantidad_final = db.Column(Numeric(10, 3), nullable=False)
    
    # Valor de costo final (para referencia histórica)
    valor_costo_final = db.Column(Numeric(10, 2), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_turno_stock_final_turno_insumo', 'turno_id', 'insumo_id', unique=True),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'turno_id': self.turno_id,
            'insumo_id': self.insumo_id,
            'cantidad_final': float(self.cantidad_final) if self.cantidad_final else 0.0,
            'valor_costo_final': float(self.valor_costo_final) if self.valor_costo_final else 0.0
        }
    
    def get_diferencia_vs_inicial(self) -> Optional[Decimal]:
        """Obtiene la diferencia entre stock final e inicial"""
        if not self.turno:
            return None
        
        stock_inicial = TurnoStockInicial.query.filter_by(
            turno_id=self.turno_id,
            insumo_id=self.insumo_id
        ).first()
        
        if not stock_inicial:
            return None
        
        return Decimal(str(self.cantidad_final)) - Decimal(str(stock_inicial.cantidad_inicial))
    
    def __repr__(self):
        return f'<TurnoStockFinal {self.id}: Turno {self.turno_id} - Insumo {self.insumo_id}>'


class MermaInventario(db.Model):
    """
    Registro de merma (pérdida de inventario) durante el turno.
    """
    __tablename__ = 'merma_inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    ubicacion = db.Column(db.String(50), nullable=False, index=True)  # "barra_pista", "barra_terraza", "bodega"
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=True, index=True)  # Opcional pero obligatorio si es merma de barra
    
    # Cantidad mermada
    cantidad_mermada = db.Column(Numeric(10, 3), nullable=False)  # En unidad base
    
    # Motivo de la merma
    motivo = db.Column(db.String(200), nullable=False)  # "rotura", "derrame", "error_preparación", etc.
    
    # Costo de la merma (calculado al momento del registro)
    costo_merma = db.Column(Numeric(10, 2), nullable=False)
    
    # Usuario que registró
    usuario_id = db.Column(db.String(100), nullable=False)
    usuario_name = db.Column(db.String(200), nullable=True)
    
    # Fecha y hora
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_merma_inventario_turno_insumo', 'turno_id', 'insumo_id'),
        Index('idx_merma_inventario_ubicacion_fecha', 'ubicacion', 'fecha_hora'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'insumo_id': self.insumo_id,
            'ubicacion': self.ubicacion,
            'turno_id': self.turno_id,
            'cantidad_mermada': float(self.cantidad_mermada) if self.cantidad_mermada else 0.0,
            'motivo': self.motivo,
            'costo_merma': float(self.costo_merma) if self.costo_merma else 0.0,
            'usuario_id': self.usuario_id,
            'usuario_name': self.usuario_name,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None
        }
    
    @classmethod
    def get_motivos_comunes(cls) -> List[str]:
        """Retorna lista de motivos comunes de merma"""
        return [
            'rotura',
            'derrame',
            'error_preparación',
            'vencimiento',
            'contaminación',
            'otro'
        ]
    
    def es_merma_critica(self, umbral_costo: float = 5000.0) -> bool:
        """Verifica si la merma es crítica según umbral de costo"""
        return float(self.costo_merma) > umbral_costo
    
    def __repr__(self):
        return f'<MermaInventario {self.id}: {self.cantidad_mermada} - {self.motivo}>'


class TurnoDesviacionInventario(db.Model):
    """
    Desviación entre stock esperado y stock final reportado para cada insumo del turno.
    """
    __tablename__ = 'turno_desviacion_inventario'
    
    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=False, index=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    ubicacion = db.Column(db.String(50), nullable=False, index=True)
    
    # Valores de stock
    stock_inicial_turno = db.Column(Numeric(10, 3), nullable=False)
    stock_esperado_turno = db.Column(Numeric(10, 3), nullable=False)
    stock_final_reportado = db.Column(Numeric(10, 3), nullable=False)
    
    # Diferencias
    diferencia_turno = db.Column(Numeric(10, 3), nullable=False)  # stock_final_reportado - stock_esperado_turno
    diferencia_porcentual_turno = db.Column(Numeric(5, 2), nullable=False)  # Porcentaje de diferencia
    
    # Costo de la diferencia
    costo_diferencia = db.Column(Numeric(10, 2), nullable=False)  # diferencia_turno * costo_unitario
    
    # Tipo de desviación
    tipo = db.Column(db.String(30), nullable=False, index=True)  # "normal", "perdida", "ganancia", "perdida_critica", "ganancia_rara"
    
    # Timestamps
    fecha_hora_registro = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_turno_desviacion_turno_insumo', 'turno_id', 'insumo_id', unique=True),
        Index('idx_turno_desviacion_tipo', 'tipo'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'turno_id': self.turno_id,
            'insumo_id': self.insumo_id,
            'ubicacion': self.ubicacion,
            'stock_inicial_turno': float(self.stock_inicial_turno) if self.stock_inicial_turno else 0.0,
            'stock_esperado_turno': float(self.stock_esperado_turno) if self.stock_esperado_turno else 0.0,
            'stock_final_reportado': float(self.stock_final_reportado) if self.stock_final_reportado else 0.0,
            'diferencia_turno': float(self.diferencia_turno) if self.diferencia_turno else 0.0,
            'diferencia_porcentual_turno': float(self.diferencia_porcentual_turno) if self.diferencia_porcentual_turno else 0.0,
            'costo_diferencia': float(self.costo_diferencia) if self.costo_diferencia else 0.0,
            'tipo': self.tipo
        }
    
    def es_perdida(self) -> bool:
        """Verifica si es una pérdida (diferencia negativa)"""
        return float(self.diferencia_turno) < 0
    
    def es_ganancia(self) -> bool:
        """Verifica si es una ganancia (diferencia positiva)"""
        return float(self.diferencia_turno) > 0
    
    def es_normal(self) -> bool:
        """Verifica si está dentro del rango normal"""
        return self.tipo == 'normal'
    
    def get_severidad(self) -> str:
        """Obtiene la severidad de la desviación"""
        if self.tipo == 'perdida_critica':
            return 'crítica'
        elif self.tipo == 'perdida':
            return 'media'
        elif self.tipo == 'ganancia_rara':
            return 'alta'
        elif self.tipo == 'ganancia':
            return 'baja'
        return 'normal'
    
    def __repr__(self):
        return f'<TurnoDesviacionInventario {self.id}: {self.diferencia_turno} ({self.tipo})>'


class AlertaFugaTurno(db.Model):
    """
    Alertas de pérdida crítica detectadas en el cierre del turno.
    """
    __tablename__ = 'alerta_fuga_turno'
    
    id = db.Column(db.Integer, primary_key=True)
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=False, index=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    ubicacion = db.Column(db.String(50), nullable=False, index=True)
    
    # Datos de la desviación
    diferencia_turno = db.Column(Numeric(10, 3), nullable=False)
    diferencia_porcentual_turno = db.Column(Numeric(5, 2), nullable=False)
    costo_diferencia = db.Column(Numeric(10, 2), nullable=False)
    
    # Criticidad de la alerta
    criticidad = db.Column(db.String(20), nullable=False, index=True)  # "alta", "media", "baja"
    
    # Estado de la alerta
    atendida = db.Column(db.Boolean, default=False, nullable=False, index=True)
    fecha_atencion = db.Column(db.DateTime, nullable=True)
    observaciones_atencion = db.Column(Text, nullable=True)
    
    # Timestamps
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_alerta_fuga_turno_atendida', 'atendida'),
        Index('idx_alerta_fuga_turno_criticidad', 'criticidad'),
    )
    
    def to_dict(self):
        """Convierte a diccionario"""
        return {
            'id': self.id,
            'turno_id': self.turno_id,
            'insumo_id': self.insumo_id,
            'ubicacion': self.ubicacion,
            'diferencia_turno': float(self.diferencia_turno) if self.diferencia_turno else 0.0,
            'diferencia_porcentual_turno': float(self.diferencia_porcentual_turno) if self.diferencia_porcentual_turno else 0.0,
            'costo_diferencia': float(self.costo_diferencia) if self.costo_diferencia else 0.0,
            'criticidad': self.criticidad,
            'atendida': self.atendida,
            'fecha_atencion': self.fecha_atencion.isoformat() if self.fecha_atencion else None,
            'observaciones_atencion': self.observaciones_atencion,
            'fecha_hora': self.fecha_hora.isoformat() if self.fecha_hora else None
        }
    
    def requiere_accion_inmediata(self) -> bool:
        """Verifica si requiere acción inmediata"""
        return not self.atendida and self.criticidad == 'alta'
    
    def get_tiempo_pendiente_horas(self) -> Optional[float]:
        """Calcula cuántas horas lleva pendiente"""
        if self.atendida:
            return None
        delta = datetime.utcnow() - self.fecha_hora
        return delta.total_seconds() / 3600
    
    @classmethod
    def get_criticidades_disponibles(cls) -> List[str]:
        """Retorna lista de criticidades disponibles"""
        return ['alta', 'media', 'baja']
    
    def __repr__(self):
        return f'<AlertaFugaTurno {self.id}: {self.criticidad} - Turno {self.turno_id}>'





