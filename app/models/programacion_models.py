"""
Modelos de base de datos para la Programación de Eventos
Gestión de eventos públicos e internos
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Text, Index, Date, Time
import json


class ProgramacionEvento(db.Model):
    """Programación de eventos - Información pública e interna"""
    __tablename__ = 'programacion_eventos'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos básicos
    fecha = db.Column(Date, nullable=False, index=True)  # Fecha del evento
    nombre_evento = db.Column(db.String(200), nullable=False)
    tipo_noche = db.Column(db.String(100), nullable=True)  # "Techno", "House", "Reggaeton", etc.
    
    # Campos públicos - Información para comunicación
    dj_principal = db.Column(db.String(200), nullable=True)
    otros_djs = db.Column(db.String(500), nullable=True)  # Lista separada por comas
    estilos_musica = db.Column(db.String(200), nullable=True)  # "Techno, House, Minimal"
    horario_apertura_publico = db.Column(Time, nullable=True)  # Hora de apertura para público
    horario_cierre_publico = db.Column(Time, nullable=True)  # Hora de cierre para público
    tiers_precios_json = db.Column(Text, nullable=True)  # JSON con tramos de precios
    info_lista = db.Column(Text, nullable=True)  # Información sobre lista de invitados
    descripcion_corta = db.Column(Text, nullable=True)  # Descripción breve del evento
    copy_ig_corto = db.Column(Text, nullable=True)  # Copy para Instagram
    copy_whatsapp_corto = db.Column(Text, nullable=True)  # Copy para WhatsApp
    hashtags_sugeridos = db.Column(Text, nullable=True)  # Hashtags sugeridos
    estado_publico = db.Column(
        db.String(50), 
        default='borrador', 
        nullable=False,
        index=True
    )  # 'borrador', 'publicado', 'cancelado'
    
    # Campos internos - Gestión de producción
    estado_produccion = db.Column(
        db.String(50), 
        default='idea', 
        nullable=False,
        index=True
    )  # 'idea', 'en_gestion', 'confirmado', 'cancelado', 'realizado'
    dj_confirmado = db.Column(db.Boolean, default=False, nullable=False)
    cache_dj_principal = db.Column(Numeric(10, 2), nullable=True)  # Cache del DJ principal
    cache_otros_djs = db.Column(Numeric(10, 2), nullable=True)  # Cache de otros DJs
    costos_produccion_estimados = db.Column(Numeric(10, 2), nullable=True)  # Costos estimados totales
    presupuesto_marketing = db.Column(Numeric(10, 2), nullable=True)  # Presupuesto para marketing
    ingresos_estimados = db.Column(Numeric(10, 2), nullable=True)  # Ingresos estimados
    aforo_objetivo = db.Column(db.Integer, nullable=True)  # Aforo objetivo
    notas_internas = db.Column(Text, nullable=True)  # Notas internas de producción
    
    # Timestamps
    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    creado_por = db.Column(db.String(200), nullable=True)
    actualizado_por = db.Column(db.String(200), nullable=True)
    
    # Soft delete
    eliminado_en = db.Column(db.DateTime, nullable=True, index=True)
    eliminado_por = db.Column(db.String(200), nullable=True)
    
    # Índices para mejor rendimiento
    __table_args__ = (
        Index('idx_programacion_fecha', 'fecha'),
        Index('idx_programacion_estado_publico', 'estado_publico'),
        Index('idx_programacion_estado_produccion', 'estado_produccion'),
        Index('idx_programacion_fecha_estado', 'fecha', 'estado_publico'),
    )
    
    def get_tiers_precios(self):
        """Obtiene los tiers de precios como lista de diccionarios"""
        if not self.tiers_precios_json:
            return []
        try:
            return json.loads(self.tiers_precios_json)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_tiers_precios(self, tiers_list):
        """Establece los tiers de precios desde una lista de diccionarios"""
        if tiers_list:
            self.tiers_precios_json = json.dumps(tiers_list, ensure_ascii=False)
        else:
            self.tiers_precios_json = None
    
    def to_dict(self, include_internal=False):
        """
        Convierte el modelo a diccionario
        
        Args:
            include_internal: Si True, incluye campos internos. Si False, solo campos públicos.
        """
        data = {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'nombre_evento': self.nombre_evento,
            'tipo_noche': self.tipo_noche,
            'dj_principal': self.dj_principal,
            'otros_djs': self.otros_djs,
            'estilos_musica': self.estilos_musica,
            'horario_apertura_publico': self.horario_apertura_publico.strftime('%H:%M') if self.horario_apertura_publico else None,
            'horario_cierre_publico': self.horario_cierre_publico.strftime('%H:%M') if self.horario_cierre_publico else None,
            'precios': self.get_tiers_precios(),
            'info_lista': self.info_lista,
            'descripcion_corta': self.descripcion_corta,
            'copy_ig_corto': self.copy_ig_corto,
            'copy_whatsapp_corto': self.copy_whatsapp_corto,
            'hashtags_sugeridos': self.hashtags_sugeridos,
            'estado_publico': self.estado_publico,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
        }
        
        if include_internal:
            data.update({
                'estado_produccion': self.estado_produccion,
                'dj_confirmado': self.dj_confirmado,
                'cache_dj_principal': float(self.cache_dj_principal) if self.cache_dj_principal else None,
                'cache_otros_djs': float(self.cache_otros_djs) if self.cache_otros_djs else None,
                'costos_produccion_estimados': float(self.costos_produccion_estimados) if self.costos_produccion_estimados else None,
                'presupuesto_marketing': float(self.presupuesto_marketing) if self.presupuesto_marketing else None,
                'ingresos_estimados': float(self.ingresos_estimados) if self.ingresos_estimados else None,
                'aforo_objetivo': self.aforo_objetivo,
                'notas_internas': self.notas_internas,
                'creado_por': self.creado_por,
                'actualizado_por': self.actualizado_por,
            })
        
        return data
    
    def to_public_dict(self):
        """
        Convierte el modelo a diccionario solo con campos públicos
        Formato optimizado para IA
        """
        horario_str = None
        if self.horario_apertura_publico and self.horario_cierre_publico:
            horario_str = f"{self.horario_apertura_publico.strftime('%H:%M')} a {self.horario_cierre_publico.strftime('%H:%M')}"
        elif self.horario_apertura_publico:
            horario_str = f"{self.horario_apertura_publico.strftime('%H:%M')} (cierre por confirmar)"
        
        return {
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'nombre_evento': self.nombre_evento,
            'tipo_noche': self.tipo_noche,
            'horario': horario_str,
            'precios': self.get_tiers_precios(),
            'dj_principal': self.dj_principal,
            'otros_djs': self.otros_djs,
            'musica': self.estilos_musica,
            'lista': self.info_lista,
            'descripcion_corta': self.descripcion_corta,
            'copy_ig_corto': self.copy_ig_corto,
            'copy_whatsapp_corto': self.copy_whatsapp_corto,
            'hashtags_sugeridos': self.hashtags_sugeridos,
        }


class ProgramacionAsignacion(db.Model):
    """
    Asignación de personal por turno en Programación.
    Define "quién debería estar" en cada turno.
    Separado de PlanillaTrabajador (que asigna pagos al momento de apertura).
    """
    __tablename__ = 'programacion_asignaciones'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos principales
    fecha = db.Column(Date, nullable=False, index=True)  # Fecha del turno
    tipo_turno = db.Column(db.String(20), nullable=False, index=True)  # 'NOCHE' o 'DIA'
    cargo_id = db.Column(db.Integer, db.ForeignKey('cargos.id'), nullable=False, index=True)
    trabajador_id = db.Column(db.String(50), db.ForeignKey('employees.id'), nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relaciones
    cargo = db.relationship('Cargo', backref='programacion_asignaciones', lazy=True)
    trabajador = db.relationship('Employee', backref='programacion_asignaciones', lazy=True)
    
    # Índices únicos para evitar duplicados
    __table_args__ = (
        Index('idx_programacion_fecha_turno_cargo_trabajador', 'fecha', 'tipo_turno', 'cargo_id', 'trabajador_id', unique=True),
        Index('idx_programacion_fecha_turno', 'fecha', 'tipo_turno'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'tipo_turno': self.tipo_turno,
            'cargo_id': self.cargo_id,
            'cargo_nombre': self.cargo.nombre if self.cargo else None,
            'trabajador_id': self.trabajador_id,
            'trabajador_nombre': self.trabajador.name if self.trabajador else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


