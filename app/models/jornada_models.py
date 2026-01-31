"""
Modelos de base de datos para el sistema de Jornadas
Gestión completa de apertura de jornada en la discoteca
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Text, Index
import json


class Jornada(db.Model):
    """Jornada completa de trabajo"""
    __tablename__ = 'jornadas'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha_jornada = db.Column(db.String(50), nullable=False, index=True)  # Fecha de apertura
    fecha_cierre_programada = db.Column(db.String(50), nullable=True)  # Fecha de cierre (se registra automáticamente al cerrar)
    tipo_turno = db.Column(db.String(50), nullable=False)  # "Noche", "Día", "Especial"
    nombre_fiesta = db.Column(db.String(200), nullable=False)
    horario_apertura_programado = db.Column(db.String(10), nullable=False)  # "20:00" - Hora de apertura
    horario_cierre_programado = db.Column(db.String(10), nullable=True)  # "04:00" - Se registra automáticamente al cerrar
    horario_apertura_real = db.Column(db.DateTime, nullable=True)  # Timestamp real de apertura
    
    # Responsables
    responsable_cajas = db.Column(db.String(200), nullable=True)
    responsable_puerta = db.Column(db.String(200), nullable=True)
    responsable_seguridad = db.Column(db.String(200), nullable=True)
    responsable_admin = db.Column(db.String(200), nullable=True)
    
    # Estado
    estado_apertura = db.Column(db.String(50), default='preparando', nullable=False)  # preparando, revisando, listo, abierto
    checklist_tecnico = db.Column(Text, nullable=True)  # JSON
    checklist_apertura = db.Column(Text, nullable=True)  # JSON
    
    # Información adicional
    djs = db.Column(db.String(200), nullable=True)
    barras_disponibles = db.Column(Text, nullable=True)  # JSON lista
    
    # Timestamps
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    abierto_en = db.Column(db.DateTime, nullable=True)
    abierto_por = db.Column(db.String(200), nullable=True)
    
    # Soft delete (eliminación suave)
    eliminado_en = db.Column(db.DateTime, nullable=True, index=True)
    eliminado_por = db.Column(db.String(200), nullable=True)
    razon_eliminacion = db.Column(Text, nullable=True)  # Explicación de por qué se eliminó
    
    # Índices para mejor rendimiento y estadísticas
    __table_args__ = (
        Index('idx_jornadas_fecha', 'fecha_jornada'),
        Index('idx_jornadas_estado', 'estado_apertura'),
        Index('idx_jornadas_tipo', 'tipo_turno'),  # Para filtrar por tipo de turno
        Index('idx_jornadas_fecha_estado', 'fecha_jornada', 'estado_apertura'),  # Para consultas combinadas
        Index('idx_jornadas_creado', 'creado_en'),  # Para ordenar por fecha de creación
        Index('idx_jornadas_abierto', 'abierto_en'),  # Para estadísticas de apertura
    )
    
    # Relaciones
    planilla_trabajadores = db.relationship('PlanillaTrabajador', backref='jornada', lazy=True, cascade='all, delete-orphan')
    aperturas_cajas = db.relationship('AperturaCaja', backref='jornada', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'fecha_jornada': self.fecha_jornada,
            'tipo_turno': self.tipo_turno,
            'nombre_fiesta': self.nombre_fiesta,
            'horario_apertura_programado': self.horario_apertura_programado,
            'horario_cierre_programado': self.horario_cierre_programado,
            'horario_apertura_real': self.horario_apertura_real.isoformat() if self.horario_apertura_real else None,
            'responsable_cajas': self.responsable_cajas,
            'responsable_puerta': self.responsable_puerta,
            'responsable_seguridad': self.responsable_seguridad,
            'responsable_admin': self.responsable_admin,
            'estado_apertura': self.estado_apertura,
            'checklist_tecnico': json.loads(self.checklist_tecnico) if self.checklist_tecnico else {},
            'checklist_apertura': json.loads(self.checklist_apertura) if self.checklist_apertura else {},
            'djs': self.djs,
            'barras_disponibles': json.loads(self.barras_disponibles) if self.barras_disponibles else [],
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'abierto_en': self.abierto_en.isoformat() if self.abierto_en else None,
            'abierto_por': self.abierto_por
        }
    
    def get_checklist_tecnico_dict(self):
        """Obtiene el checklist técnico como diccionario"""
        if self.checklist_tecnico:
            try:
                return json.loads(self.checklist_tecnico)
            except:
                return {}
        return {}
    
    def set_checklist_tecnico(self, checklist_dict):
        """Establece el checklist técnico desde un diccionario"""
        self.checklist_tecnico = json.dumps(checklist_dict)
    
    def get_checklist_apertura_dict(self):
        """Obtiene el checklist de apertura como diccionario"""
        if self.checklist_apertura:
            try:
                return json.loads(self.checklist_apertura)
            except:
                return {}
        return {}
    
    def set_checklist_apertura(self, checklist_dict):
        """Establece el checklist de apertura desde un diccionario"""
        self.checklist_apertura = json.dumps(checklist_dict)


class PlanillaTrabajador(db.Model):
    """Planilla de trabajadores de una jornada"""
    __tablename__ = 'planilla_trabajadores'
    
    id = db.Column(db.Integer, primary_key=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    id_empleado = db.Column(db.String(50), nullable=False)
    nombre_empleado = db.Column(db.String(200), nullable=False)
    rol = db.Column(db.String(50), nullable=False)  # "cajero", "bartender", "seguridad", "admin", "puerta"
    hora_inicio = db.Column(db.String(10), nullable=False)  # "20:00"
    hora_fin = db.Column(db.String(10), nullable=False)  # "04:00"
    costo_hora = db.Column(Numeric(10, 2), nullable=False)
    costo_total = db.Column(Numeric(10, 2), nullable=False)
    area = db.Column(db.String(100), nullable=True)  # "caja 1", "barra principal", etc.
    
    # SNAPSHOT DE PAGO (congelado al momento de asignar al turno)
    # Estos valores NO cambian aunque el sueldo del cargo se modifique después
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=True, index=True)  # Referencia al cargo
    sueldo_snapshot = db.Column(Numeric(10, 2), nullable=True)  # Sueldo por turno congelado
    bono_snapshot = db.Column(Numeric(10, 2), nullable=True, default=0.0)  # Bono fijo congelado
    pago_total = db.Column(Numeric(10, 2), nullable=True)  # Total congelado (sueldo + bono)
    
    # ORIGEN (programacion o manual)
    origen = db.Column(db.String(20), nullable=True, default='manual', index=True)  # 'programacion' o 'manual'
    
    # OVERRIDE (solo admin/superadmin)
    override = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Si True, el pago fue modificado manualmente
    override_motivo = db.Column(Text, nullable=True)  # Motivo del override
    override_por = db.Column(db.String(200), nullable=True)  # Usuario que hizo el override
    override_en = db.Column(db.DateTime, nullable=True)  # Fecha/hora del override
    
    # Timestamps
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices para consultas eficientes y estadísticas
    __table_args__ = (
        Index('idx_planilla_jornada', 'jornada_id'),
        Index('idx_planilla_empleado', 'id_empleado'),
        Index('idx_planilla_rol', 'rol'),
        Index('idx_planilla_creado', 'creado_en'),
        Index('idx_planilla_jornada_rol', 'jornada_id', 'rol'),  # Para estadísticas por jornada y rol
        Index('idx_planilla_jornada_empleado', 'jornada_id', 'id_empleado'),  # Para evitar duplicados
        Index('idx_planilla_override', 'override'),  # Para filtrar overrides
        Index('idx_planilla_cargo', 'cargo_id'),  # Para consultas por cargo
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'jornada_id': self.jornada_id,
            'id_empleado': self.id_empleado,
            'nombre_empleado': self.nombre_empleado,
            'rol': self.rol,
            'hora_inicio': self.hora_inicio,
            'hora_fin': self.hora_fin,
            'costo_hora': float(self.costo_hora) if self.costo_hora else 0.0,
            'costo_total': float(self.costo_total) if self.costo_total else 0.0,
            'area': self.area,
            'cargo_id': self.cargo_id,
            'sueldo_snapshot': float(self.sueldo_snapshot) if self.sueldo_snapshot else None,
            'bono_snapshot': float(self.bono_snapshot) if self.bono_snapshot else 0.0,
            'pago_total': float(self.pago_total) if self.pago_total else None,
            'origen': self.origen or 'manual',
            'override': self.override,
            'override_motivo': self.override_motivo,
            'override_por': self.override_por,
            'override_en': self.override_en.isoformat() if self.override_en else None,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None
        }
    
    def calcular_y_congelar_pago(self, cargo_nombre: str = None):
        """
        Calcula y congela el pago basado en el cargo del trabajador.
        Este método se llama AL MOMENTO DE ASIGNAR al turno.
        El pago queda congelado y NO cambia aunque el sueldo del cargo se modifique después.
        
        Args:
            cargo_nombre: Nombre del cargo (si no se proporciona, usa self.rol)
        """
        from app.models.cargo_salary_models import CargoSalaryConfig
        from app.models.cargo_models import Cargo
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Usar cargo_nombre o rol como fallback
            cargo_buscar = cargo_nombre or self.rol
            
            if not cargo_buscar:
                logger.warning(f"⚠️ No se puede calcular pago: cargo/rol no especificado para trabajador {self.id_empleado}")
                return
            
            # Buscar configuración de sueldo del cargo
            config_cargo = CargoSalaryConfig.query.filter_by(cargo=cargo_buscar).first()
            
            if not config_cargo:
                logger.warning(f"⚠️ No se encontró configuración de sueldo para cargo '{cargo_buscar}'. Pago no congelado.")
                # No lanzar error, solo registrar warning
                return
            
            # CONGELAR valores (snapshot)
            self.sueldo_snapshot = config_cargo.sueldo_por_turno or 0.0
            self.bono_snapshot = config_cargo.bono_fijo or 0.0
            self.pago_total = float(self.sueldo_snapshot) + float(self.bono_snapshot)
            
            # Buscar cargo_id si existe
            cargo_obj = Cargo.query.filter_by(nombre=cargo_buscar).first()
            if cargo_obj:
                self.cargo_id = cargo_obj.id
            
            # Si no hay override, marcar como calculado automáticamente
            if not self.override:
                self.override = False
                self.override_motivo = None
                self.override_por = None
                self.override_en = None
            
            logger.info(
                f"✅ Pago congelado para {self.nombre_empleado} (cargo: {cargo_buscar}): "
                f"Sueldo=${self.sueldo_snapshot}, Bono=${self.bono_snapshot}, Total=${self.pago_total}"
            )
            
        except Exception as e:
            logger.error(f"Error calculando y congelando pago para planilla {self.id}: {e}", exc_info=True)
            # No lanzar excepción, solo registrar error
    
    def calcular_costo_total(self):
        """
        Calcula el costo total basado en horas trabajadas.
        Maneja correctamente turnos que cruzan medianoche.
        Retorna el costo total calculado (importante para estadísticas).
        """
        try:
            # Parsear horas (formato HH:MM) - normalizar strings
            inicio = datetime.strptime(str(self.hora_inicio).strip(), '%H:%M')
            fin = datetime.strptime(str(self.hora_fin).strip(), '%H:%M')
            
            # Si la hora fin es menor que inicio, asumimos que pasa la medianoche
            # Ejemplo: 22:00 a 05:00 = 7 horas
            if fin < inicio:
                fin = fin.replace(day=fin.day + 1)
            
            diferencia = fin - inicio
            horas_trabajadas = diferencia.total_seconds() / 3600.0
            
            # Asegurar que costo_hora sea numérico
            costo_hora = float(self.costo_hora) if self.costo_hora else 0.0
            
            # Calcular costo total (redondeado a 2 decimales para consistencia en estadísticas)
            self.costo_total = round(costo_hora * horas_trabajadas, 2)
            return self.costo_total
        except Exception as e:
            # En caso de error, retornar 0.0 pero registrar
            import logging
            logging.warning(f"Error calculando costo_total para planilla {self.id}: {e}")
            self.costo_total = 0.0
            return 0.0


class AperturaCaja(db.Model):
    """Apertura de una caja en una jornada"""
    __tablename__ = 'aperturas_cajas'
    
    id = db.Column(db.Integer, primary_key=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    id_caja = db.Column(db.String(50), nullable=False, index=True)
    nombre_caja = db.Column(db.String(200), nullable=False)
    id_empleado = db.Column(db.String(50), nullable=False)
    nombre_empleado = db.Column(db.String(200), nullable=False)
    fondo_inicial = db.Column(Numeric(10, 2), nullable=False)
    fecha_apertura = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    abierto_por = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(50), default='abierta', nullable=False)  # pendiente, abierta, cerrada
    
    # Índices
    __table_args__ = (
        Index('idx_apertura_caja_jornada', 'jornada_id'),
        Index('idx_apertura_caja_id', 'id_caja'),
        Index('idx_apertura_caja_estado', 'estado'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'jornada_id': self.jornada_id,
            'id_caja': self.id_caja,
            'nombre_caja': self.nombre_caja,
            'id_empleado': self.id_empleado,
            'nombre_empleado': self.nombre_empleado,
            'fondo_inicial': float(self.fondo_inicial) if self.fondo_inicial else 0.0,
            'fecha_apertura': self.fecha_apertura.isoformat() if self.fecha_apertura else None,
            'abierto_por': self.abierto_por,
            'estado': self.estado
        }


class SnapshotEmpleados(db.Model):
    """Snapshot de empleados al abrir el turno (para evitar consultas constantes a la API)"""
    __tablename__ = 'snapshot_empleados'
    
    id = db.Column(db.Integer, primary_key=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    empleado_id = db.Column(db.String(50), nullable=False, index=True)
    nombre = db.Column(db.String(200), nullable=False)
    cargo = db.Column(db.String(100), nullable=True)  # "Bartender", "Cajero", etc.
    datos_completos = db.Column(Text, nullable=True)  # JSON con todos los datos del empleado
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_snapshot_jornada', 'jornada_id'),
        Index('idx_snapshot_empleado', 'empleado_id'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        datos = {}
        if self.datos_completos:
            try:
                datos = json.loads(self.datos_completos)
            except:
                pass
        return {
            'id': self.id,
            'jornada_id': self.jornada_id,
            'empleado_id': self.empleado_id,
            'nombre': self.nombre,
            'cargo': self.cargo,
            'datos_completos': datos,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None
        }


class SnapshotCajas(db.Model):
    """Snapshot de cajas al abrir el turno (para evitar consultas constantes a la API)"""
    __tablename__ = 'snapshot_cajas'
    
    id = db.Column(db.Integer, primary_key=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    caja_id = db.Column(db.String(50), nullable=False, index=True)
    nombre_caja = db.Column(db.String(200), nullable=False)
    datos_completos = db.Column(Text, nullable=True)  # JSON con todos los datos de la caja
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_snapshot_cajas_jornada', 'jornada_id'),
        Index('idx_snapshot_cajas_id', 'caja_id'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        datos = {}
        if self.datos_completos:
            try:
                datos = json.loads(self.datos_completos)
            except:
                pass
        return {
            'id': self.id,
            'jornada_id': self.jornada_id,
            'caja_id': self.caja_id,
            'nombre_caja': self.nombre_caja,
            'datos_completos': datos,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None
        }


