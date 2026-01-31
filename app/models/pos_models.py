"""
Modelos de base de datos para el POS propio
Sistema de gestión propio - ventas locales + sincronización con PHP POS
"""
from datetime import datetime
from . import db
from sqlalchemy import Numeric, Text, Index, String
# UUID: Migrado de PostgreSQL UUID a String(36) para compatibilidad MySQL
# from sqlalchemy.dialects.postgresql import UUID  # Legacy PostgreSQL
import json
import uuid


class PosSession(db.Model):
    """Sesión activa del POS (carrito temporal)"""
    __tablename__ = 'pos_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(200), nullable=False)
    register_id = db.Column(db.String(50), nullable=True, index=True)
    register_name = db.Column(db.String(200), nullable=True)
    
    # Carrito temporal (JSON)
    cart_items = db.Column(Text, nullable=True)  # JSON string
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índice compuesto para búsquedas activas
    __table_args__ = (
        Index('idx_pos_sessions_active_register', 'is_active', 'register_id'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'register_id': self.register_id,
            'register_name': self.register_name,
            'cart_items': json.loads(self.cart_items) if self.cart_items else [],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class PosSaleBackup(db.Model):
    """Respaldo de ventas eliminadas/respaldadas del POS"""
    __tablename__ = 'pos_sales_backup'
    
    id = db.Column(db.Integer, primary_key=True)
    original_sale_id = db.Column(db.Integer, nullable=False, index=True)  # ID original de la venta
    sale_id_phppos = db.Column(db.String(50), nullable=True, index=True)
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)
    payment_cash = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    payment_debit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    payment_credit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(200), nullable=False)
    register_id = db.Column(db.String(50), nullable=False, index=True)
    register_name = db.Column(db.String(200), nullable=False)
    shift_date = db.Column(db.String(50), nullable=True, index=True)
    synced_to_phppos = db.Column(db.Boolean, default=False, nullable=False)
    
    # Información del respaldo
    backed_up_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    backed_up_by = db.Column(db.String(200), nullable=True)  # Usuario que hizo el respaldo
    backup_reason = db.Column(db.String(500), nullable=True)  # Razón del respaldo (ej: "Limpieza de cajas")
    
    # Timestamp original de la venta
    original_created_at = db.Column(db.DateTime, nullable=False)
    
    # Relación con items de respaldo
    items = db.relationship('PosSaleItemBackup', backref='sale_backup', lazy=True, cascade='all, delete-orphan')
    
    # Índices
    __table_args__ = (
        Index('idx_pos_sales_backup_shift_date', 'shift_date'),
        Index('idx_pos_sales_backup_backed_up_at', 'backed_up_at'),
        Index('idx_pos_sales_backup_register_date', 'register_id', 'shift_date'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'original_sale_id': self.original_sale_id,
            'sale_id_phppos': self.sale_id_phppos,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'payment_type': self.payment_type,
            'payment_cash': float(self.payment_cash) if self.payment_cash else 0.0,
            'payment_debit': float(self.payment_debit) if self.payment_debit else 0.0,
            'payment_credit': float(self.payment_credit) if self.payment_credit else 0.0,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'register_id': self.register_id,
            'register_name': self.register_name,
            'shift_date': self.shift_date,
            'synced_to_phppos': self.synced_to_phppos,
            'backed_up_at': self.backed_up_at.isoformat() if self.backed_up_at else None,
            'backed_up_by': self.backed_up_by,
            'backup_reason': self.backup_reason,
            'original_created_at': self.original_created_at.isoformat() if self.original_created_at else None,
            'items': [item.to_dict() for item in self.items] if self.items else []
        }


class PosSaleItemBackup(db.Model):
    """Item de una venta respaldada"""
    __tablename__ = 'pos_sale_items_backup'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_backup_id = db.Column(db.Integer, db.ForeignKey('pos_sales_backup.id'), nullable=False, index=True)
    original_item_id = db.Column(db.Integer, nullable=False)  # ID original del item
    product_id = db.Column(db.String(50), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(Numeric(10, 2), nullable=False)
    subtotal = db.Column(Numeric(10, 2), nullable=False)
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'sale_backup_id': self.sale_backup_id,
            'original_item_id': self.original_item_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0.0,
            'subtotal': float(self.subtotal) if self.subtotal else 0.0
        }


class PosSale(db.Model):
    """Venta realizada en el POS (guardada localmente)"""
    __tablename__ = 'pos_sales'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id_phppos = db.Column(db.String(50), unique=True, nullable=True, index=True)  # ID de PHP POS si se sincronizó
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    payment_type = db.Column(db.String(50), nullable=False, index=True)  # Efectivo, Débito, Crédito
    payment_cash = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Monto en efectivo
    payment_debit = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Monto en débito
    payment_credit = db.Column(Numeric(10, 2), default=0.0, nullable=False)  # Monto en crédito
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(200), nullable=False)
    register_id = db.Column(db.String(50), nullable=False, index=True)
    register_name = db.Column(db.String(200), nullable=False)
    
    # Datos adicionales
    shift_date = db.Column(db.String(50), nullable=False, index=True)  # P0-004: NO NULL
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)  # P0-004: Asociación fuerte
    synced_to_phppos = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Si se sincronizó a PHP POS
    
    # BIMBA: Asociación con sesión de caja (trazabilidad)
    register_session_id = db.Column(db.Integer, db.ForeignKey('register_sessions.id'), nullable=True, index=True)
    
    # BIMBA: Payment Stack - Separar método de pago vs proveedor
    # payment_type = método (cash/debit/credit/transfer/prepaid/qr)
    # payment_provider = procesador (GETNET/KLAP/NONE)
    payment_provider = db.Column(db.String(50), nullable=True, index=True)  # GETNET, KLAP, NONE (null = NONE)
    
    # Campos para caja SUPERADMIN
    is_courtesy = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Cortesía (monto 0)
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Prueba de deploy
    no_revenue = db.Column(db.Boolean, default=False, nullable=False, index=True)  # P0-016: No cuenta como ingreso real
    
    # P0-007: Idempotencia de venta
    idempotency_key = db.Column(db.String(64), unique=True, nullable=True, index=True)
    
    # P0-008: Cancelación de venta
    is_cancelled = db.Column(db.Boolean, default=False, nullable=False, index=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.String(200), nullable=True)
    cancelled_reason = db.Column(Text, nullable=True)
    
    # CORRECCIÓN CRÍTICA: Flag para evitar doble descuento de inventario
    inventory_applied = db.Column(db.Boolean, default=False, nullable=False, index=True)
    inventory_applied_at = db.Column(db.DateTime, nullable=True)
    
    # Relación con jornada
    jornada = db.relationship('Jornada', backref='pos_sales', lazy=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relación con items - eager loading por defecto para evitar N+1 queries
    items = db.relationship('PosSaleItem', backref='sale', lazy='joined', cascade='all, delete-orphan')
    
    # Relación con sesión de caja
    register_session = db.relationship('RegisterSession', backref='pos_sales', lazy=True)
    
    # Índices compuestos para consultas comunes
    __table_args__ = (
        Index('idx_pos_sales_register_date', 'register_id', 'shift_date'),
        Index('idx_pos_sales_employee_date', 'employee_id', 'shift_date'),
        Index('idx_pos_sales_created_at', 'created_at'),
        Index('idx_pos_sales_shift_date', 'shift_date'),  # Para consultas por turno
        Index('idx_pos_sales_jornada', 'jornada_id'),  # P0-004
        Index('idx_pos_sales_no_revenue', 'no_revenue', 'is_courtesy', 'is_test'),  # P0-006
        Index('idx_pos_sales_cancelled', 'is_cancelled'),  # P0-008
        Index('idx_pos_sales_register_session', 'register_session_id'),  # BIMBA: Trazabilidad
        Index('idx_pos_sales_payment_provider', 'payment_provider'),  # BIMBA: Conciliación por provider
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'sale_id_phppos': self.sale_id_phppos,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'payment_type': self.payment_type,
            'payment_cash': float(self.payment_cash) if self.payment_cash else 0.0,
            'payment_debit': float(self.payment_debit) if self.payment_debit else 0.0,
            'payment_credit': float(self.payment_credit) if self.payment_credit else 0.0,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'register_id': self.register_id,
            'register_name': self.register_name,
            'shift_date': self.shift_date,
            'jornada_id': self.jornada_id,
            'synced_to_phppos': self.synced_to_phppos,
            # BIMBA: Trazabilidad y Payment Stack
            'register_session_id': self.register_session_id,
            'payment_provider': self.payment_provider,  # GETNET, KLAP, NONE
            'is_courtesy': self.is_courtesy,
            'is_test': self.is_test,
            'no_revenue': self.no_revenue,
            'is_cancelled': self.is_cancelled,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancelled_by': self.cancelled_by,
            'cancelled_reason': self.cancelled_reason,
            'inventory_applied': self.inventory_applied,
            'inventory_applied_at': self.inventory_applied_at.isoformat() if self.inventory_applied_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items] if self.items else []
        }


class PosSaleItem(db.Model):
    """Item de una venta"""
    __tablename__ = 'pos_sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('pos_sales.id'), nullable=False, index=True)
    product_id = db.Column(db.String(50), nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(Numeric(10, 2), nullable=False)
    subtotal = db.Column(Numeric(10, 2), nullable=False)
    
    # Índice compuesto para búsquedas por producto
    __table_args__ = (
        Index('idx_pos_sale_items_product', 'product_id', 'sale_id'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price) if self.unit_price else 0.0,
            'subtotal': float(self.subtotal) if self.subtotal else 0.0
        }


class PaymentIntent(db.Model):
    """
    PaymentIntent - Intención de pago para procesamiento con agente local (GETNET/KLAP)
    """
    __tablename__ = 'payment_intents'

    # Estados válidos (alineados con migrations/2025_01_15_payment_intents.sql)
    STATUS_CREATED = 'CREATED'
    STATUS_READY = 'READY'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_APPROVED = 'APPROVED'
    STATUS_DECLINED = 'DECLINED'
    STATUS_ERROR = 'ERROR'
    STATUS_CANCELLED = 'CANCELLED'

    # UUID migrado a String(36) para compatibilidad MySQL
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Contexto
    register_id = db.Column(db.String(50), nullable=False, index=True)
    register_session_id = db.Column(db.Integer, nullable=True, index=True)
    employee_id = db.Column(db.String(50), nullable=False, index=True)
    employee_name = db.Column(db.String(200), nullable=False)

    # Monto y moneda
    amount_total = db.Column(Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='CLP')

    # Carrito + hash para idempotencia
    cart_json = db.Column(Text, nullable=False)
    cart_hash = db.Column(db.String(64), nullable=False, index=True)

    # Provider y estado
    provider = db.Column(db.String(50), nullable=False, default='GETNET')
    status = db.Column(db.String(20), nullable=False, default=STATUS_CREATED, index=True)

    # Referencias del provider
    provider_ref = db.Column(db.String(200), nullable=True)
    auth_code = db.Column(db.String(50), nullable=True)

    # Errores
    error_code = db.Column(db.String(50), nullable=True)
    error_message = db.Column(Text, nullable=True)

    # Locking para agente
    locked_by_agent = db.Column(db.String(200), nullable=True)
    locked_at = db.Column(db.DateTime, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    approved_at = db.Column(db.DateTime, nullable=True)

    # Metadata adicional (JSON string)
    metadata_json = db.Column(Text, nullable=True)

    __table_args__ = (
        Index('idx_payment_intents_register_status', 'register_id', 'status'),
        Index('idx_payment_intents_pending', 'register_id', 'status', 'created_at'),
    )

    def can_cancel(self) -> bool:
        """Puede cancelarse si aún no está aprobado/declinado/cancelado."""
        return self.status in {self.STATUS_READY, self.STATUS_IN_PROGRESS, self.STATUS_CREATED}


class PosRegister(db.Model):
    """
    TPV (Terminal Punto de Venta) / Caja Registradora del POS
    Representa un punto físico o lógico donde se realizan ventas
    """
    __tablename__ = 'pos_registers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    superadmin_only = db.Column(db.Boolean, default=False, nullable=False, index=True)
    allowed_categories = db.Column(Text, nullable=True)  # JSON array de categorías permitidas (null = todas)
    
    # Nuevos campos para mejor gestión de TPV
    location = db.Column(db.String(200), nullable=True, index=True)  # Ubicación física: "Barra Principal", "Terraza"
    tpv_type = db.Column(db.String(50), nullable=True, index=True)  # Tipo: "barra", "puerta", "kiosko", "movil", "vip", "terraza"
    default_location = db.Column(db.String(100), nullable=True)  # Ubicación para descontar inventario: "barra_principal", "bodega"
    printer_config = db.Column(Text, nullable=True)  # JSON: configuración de impresora
    max_concurrent_sessions = db.Column(db.Integer, default=1, nullable=False)  # Sesiones simultáneas permitidas
    requires_cash_count = db.Column(db.Boolean, default=True, nullable=False)  # Requiere conteo de efectivo al abrir
    
    # MVP1: Campos nuevos para configuración de cajas según plan BIMBA
    register_type = db.Column(db.String(50), nullable=True, index=True)  # TOTEM, HUMANA, OFICINA, VIRTUAL
    devices = db.Column(Text, nullable=True)  # JSON: dispositivos asociados (POS, impresora, gaveta)
    operation_mode = db.Column(Text, nullable=True)  # JSON: modo de operación (venta normal, cortesía, precompra)
    payment_methods = db.Column(Text, nullable=True)  # JSON array: métodos de pago habilitados
    responsible_user_id = db.Column(db.String(50), nullable=True, index=True)  # Usuario responsable
    responsible_role = db.Column(db.String(50), nullable=True)  # Rol del responsable
    operational_status = db.Column(db.String(50), default='active', nullable=False, index=True)  # active, maintenance, offline, error
    fallback_config = db.Column(Text, nullable=True)  # JSON: configuración de fallback
    fast_lane_config = db.Column(Text, nullable=True)  # JSON: configuración de fast lane
    
    # Payment Stack BIMBA: GETNET principal + KLAP backup
    payment_provider_primary = db.Column(db.String(50), default='GETNET', nullable=False)  # GETNET, KLAP, etc.
    payment_provider_backup = db.Column(db.String(50), nullable=True)  # KLAP, null si no hay backup
    provider_config = db.Column(Text, nullable=True)  # JSON: configuración por proveedor (terminal_id, merchant_id, etc)
    fallback_policy = db.Column(Text, nullable=True)  # JSON: reglas de cuándo usar backup
    
    # Test register flag
    is_test = db.Column(db.Boolean, default=False, nullable=False, index=True)  # Caja de prueba (no usar en producción)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_pos_registers_active', 'is_active'),
        Index('idx_pos_registers_superadmin', 'superadmin_only', 'is_active'),
        Index('idx_pos_registers_type', 'tpv_type', 'is_active'),
        Index('idx_pos_registers_location', 'location'),
    )
    
    # Tipos de TPV válidos (legacy)
    TPV_TYPE_BARRA = 'barra'
    TPV_TYPE_PUERTA = 'puerta'
    TPV_TYPE_TERRAZA = 'terraza'
    TPV_TYPE_KIOSKO = 'kiosko'
    TPV_TYPE_MOVIL = 'movil'
    TPV_TYPE_VIP = 'vip'
    
    TPV_TYPES = [
        TPV_TYPE_BARRA,
        TPV_TYPE_PUERTA,
        TPV_TYPE_TERRAZA,
        TPV_TYPE_KIOSKO,
        TPV_TYPE_MOVIL,
        TPV_TYPE_VIP,
    ]
    
    # MVP1: Tipos de caja según plan BIMBA
    REGISTER_TYPE_TOTEM = 'TOTEM'
    REGISTER_TYPE_HUMANA = 'HUMANA'
    REGISTER_TYPE_OFICINA = 'OFICINA'
    REGISTER_TYPE_VIRTUAL = 'VIRTUAL'
    
    REGISTER_TYPES = [
        REGISTER_TYPE_TOTEM,
        REGISTER_TYPE_HUMANA,
        REGISTER_TYPE_OFICINA,
        REGISTER_TYPE_VIRTUAL,
    ]
    
    # Estados operativos
    STATUS_ACTIVE = 'active'
    STATUS_MAINTENANCE = 'maintenance'
    STATUS_OFFLINE = 'offline'
    STATUS_ERROR = 'error'
    
    OPERATIONAL_STATUSES = [
        STATUS_ACTIVE,
        STATUS_MAINTENANCE,
        STATUS_OFFLINE,
        STATUS_ERROR,
    ]
    
    # Payment Providers BIMBA
    PROVIDER_GETNET = 'GETNET'
    PROVIDER_KLAP = 'KLAP'
    PROVIDER_SUMUP = 'SUMUP'  # No recomendado pero disponible
    
    PAYMENT_PROVIDERS = [
        PROVIDER_GETNET,
        PROVIDER_KLAP,
        PROVIDER_SUMUP,
    ]
    
    # Payment Strategy
    STRATEGY_GETNET_PRIMARY_KLAP_BACKUP = 'GETNET_PRIMARY_KLAP_BACKUP'
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        printer_config_dict = None
        if self.printer_config:
            try:
                printer_config_dict = json.loads(self.printer_config)
            except:
                printer_config_dict = None
        
        # Parsear JSON fields
        devices_dict = None
        if self.devices:
            try:
                devices_dict = json.loads(self.devices)
            except:
                devices_dict = None
        
        operation_mode_dict = None
        if self.operation_mode:
            try:
                operation_mode_dict = json.loads(self.operation_mode)
            except:
                operation_mode_dict = None
        
        payment_methods_list = None
        if self.payment_methods:
            try:
                payment_methods_list = json.loads(self.payment_methods)
            except:
                payment_methods_list = None
        
        fallback_config_dict = None
        if self.fallback_config:
            try:
                fallback_config_dict = json.loads(self.fallback_config)
            except:
                fallback_config_dict = None
        
        fast_lane_config_dict = None
        if self.fast_lane_config:
            try:
                fast_lane_config_dict = json.loads(self.fast_lane_config)
            except:
                fast_lane_config_dict = None
        
        provider_config_dict = None
        if self.provider_config:
            try:
                provider_config_dict = json.loads(self.provider_config)
            except:
                provider_config_dict = None
        
        fallback_policy_dict = None
        if self.fallback_policy:
            try:
                fallback_policy_dict = json.loads(self.fallback_policy)
            except:
                fallback_policy_dict = None
        
        return {
            'id': str(self.id),
            'name': self.name,
            'code': self.code,
            'is_active': self.is_active,
            'superadmin_only': self.superadmin_only,
            'location': self.location,
            'tpv_type': self.tpv_type,
            'default_location': self.default_location,
            'printer_config': printer_config_dict,
            'max_concurrent_sessions': self.max_concurrent_sessions,
            'requires_cash_count': self.requires_cash_count,
            'allowed_categories': json.loads(self.allowed_categories) if self.allowed_categories else None,
            # MVP1: Campos nuevos
            'register_type': self.register_type,
            'devices': devices_dict,
            'operation_mode': operation_mode_dict,
            'payment_methods': payment_methods_list,
            'responsible_user_id': self.responsible_user_id,
            'responsible_role': self.responsible_role,
            'operational_status': self.operational_status,
            'fallback_config': fallback_config_dict,
            'fast_lane_config': fast_lane_config_dict,
            # Payment Stack BIMBA
            'payment_provider_primary': self.payment_provider_primary,
            'payment_provider_backup': self.payment_provider_backup,
            'provider_config': provider_config_dict,
            'fallback_policy': fallback_policy_dict,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_type_display_name(self):
        """Retorna el nombre legible del tipo de TPV"""
        type_names = {
            self.TPV_TYPE_BARRA: 'Barra',
            self.TPV_TYPE_PUERTA: 'Puerta',
            self.TPV_TYPE_TERRAZA: 'Terraza',
            self.TPV_TYPE_KIOSKO: 'Kiosko',
            self.TPV_TYPE_MOVIL: 'Móvil',
            self.TPV_TYPE_VIP: 'VIP',
        }
        return type_names.get(self.tpv_type, self.tpv_type or 'Sin tipo')


class RegisterLock(db.Model):
    """Bloqueo de caja por usuario"""
    __tablename__ = 'register_locks'
    
    register_id = db.Column(db.String(50), primary_key=True)
    employee_id = db.Column(db.String(50), nullable=False)
    employee_name = db.Column(db.String(200), nullable=False)
    session_id = db.Column(db.String(200), nullable=True)
    locked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)  # Timeout automático
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'register_id': self.register_id,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'session_id': self.session_id,
            'locked_at': self.locked_at.isoformat() if self.locked_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


class RegisterSession(db.Model):
    """
    Sesión de caja con estado explícito (P0-001, P0-003, P0-010)
    Estado: OPEN, PENDING_CLOSE, CLOSED
    """
    __tablename__ = 'register_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    register_id = db.Column(db.String(50), nullable=False, index=True)
    opened_by_employee_id = db.Column(db.String(50), nullable=False, index=True)
    opened_by_employee_name = db.Column(db.String(200), nullable=False)
    opened_at = db.Column(db.DateTime, nullable=False, index=True)  # Chile TZ
    
    # Estado explícito
    status = db.Column(db.String(20), nullable=False, default='OPEN', index=True)  # OPEN, PENDING_CLOSE, CLOSED
    
    # Asociación con turno/jornada (OBLIGATORIO)
    shift_date = db.Column(db.String(50), nullable=False, index=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=False, index=True)
    
    # Monto inicial (opcional)
    initial_cash = db.Column(Numeric(10, 2), nullable=True)
    
    # MVP1: Campos nuevos para cierre con arqueo y totales
    cash_count = db.Column(Text, nullable=True)  # JSON: conteo de efectivo por denominación
    payment_totals = db.Column(Text, nullable=True)  # JSON: snapshot de totales por método de pago
    ticket_count = db.Column(db.Integer, default=0, nullable=False)  # Contador de tickets emitidos
    cash_difference = db.Column(Numeric(10, 2), nullable=True)  # Diferencia entre efectivo contado y esperado
    incidents = db.Column(Text, nullable=True)  # JSON array: incidentes durante la sesión
    close_notes = db.Column(Text, nullable=True)  # Notas del cierre
    
    # Payment Stack BIMBA: Tracking de uso de providers y fallback
    payment_provider_used_primary_count = db.Column(db.Integer, default=0, nullable=False)  # Transacciones con provider principal
    payment_provider_used_backup_count = db.Column(db.Integer, default=0, nullable=False)  # Transacciones con provider backup
    fallback_events = db.Column(Text, nullable=True)  # JSON array: eventos de fallback [{timestamp, reason, from_provider, to_provider, handled_by_user_id}]
    
    # Cierre
    closed_at = db.Column(db.DateTime, nullable=True)
    closed_by = db.Column(db.String(200), nullable=True)
    
    # Idempotencia de apertura
    idempotency_key_open = db.Column(db.String(64), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relación con jornada
    jornada = db.relationship('Jornada', backref='register_sessions', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_register_sessions_register_status', 'register_id', 'status'),
        Index('idx_register_sessions_jornada', 'jornada_id'),
        Index('idx_register_sessions_shift_date', 'shift_date'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        # Parsear JSON fields
        cash_count_dict = None
        if self.cash_count:
            try:
                cash_count_dict = json.loads(self.cash_count)
            except:
                cash_count_dict = None
        
        payment_totals_dict = None
        if self.payment_totals:
            try:
                payment_totals_dict = json.loads(self.payment_totals)
            except:
                payment_totals_dict = None
        
        incidents_list = None
        if self.incidents:
            try:
                incidents_list = json.loads(self.incidents)
            except:
                incidents_list = None
        
        fallback_events_list = None
        if self.fallback_events:
            try:
                fallback_events_list = json.loads(self.fallback_events)
            except:
                fallback_events_list = None
        
        return {
            'id': self.id,
            'register_id': self.register_id,
            'opened_by_employee_id': self.opened_by_employee_id,
            'opened_by_employee_name': self.opened_by_employee_name,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'status': self.status,
            'shift_date': self.shift_date,
            'jornada_id': self.jornada_id,
            'initial_cash': float(self.initial_cash) if self.initial_cash else None,
            # MVP1: Campos nuevos
            'cash_count': cash_count_dict,
            'payment_totals': payment_totals_dict,
            'ticket_count': self.ticket_count,
            'cash_difference': float(self.cash_difference) if self.cash_difference else None,
            'incidents': incidents_list,
            'close_notes': self.close_notes,
            # Payment Stack BIMBA
            'payment_provider_used_primary_count': self.payment_provider_used_primary_count,
            'payment_provider_used_backup_count': self.payment_provider_used_backup_count,
            'fallback_events': fallback_events_list,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closed_by': self.closed_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def is_open(self) -> bool:
        """Verifica si la sesión está abierta"""
        return self.status == 'OPEN'
    
    def can_sell(self) -> bool:
        """Verifica si se pueden hacer ventas en esta sesión"""
        return self.status == 'OPEN'


class PaymentAgent(db.Model):
    """
    PaymentAgent - Estado del agente de pago (Windows) que comunica con el POS físico Getnet
    """
    __tablename__ = 'payment_agents'

    # UUID migrado a String(36) para compatibilidad MySQL
    id = db.Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Identificación del agente
    register_id = db.Column(db.String(50), nullable=False, index=True)
    agent_name = db.Column(db.String(200), nullable=False)
    
    # Estado de conectividad
    last_heartbeat = db.Column(db.DateTime, nullable=False, index=True)
    last_ip = db.Column(db.String(100), nullable=True)
    
    # Estado del pinpad Getnet
    last_getnet_status = db.Column(db.String(20), nullable=True)  # 'OK', 'ERROR', 'UNKNOWN'
    last_getnet_message = db.Column(Text, nullable=True)
    
    # Healthcheck adicional
    last_healthcheck_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_payment_agents_register_heartbeat', 'register_id', 'last_heartbeat'),
        Index('idx_payment_agents_register_agent', 'register_id', 'agent_name'),
    )

    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': str(self.id),
            'register_id': self.register_id,
            'agent_name': self.agent_name,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'last_ip': self.last_ip,
            'last_getnet_status': self.last_getnet_status,
            'last_getnet_message': self.last_getnet_message,
            'last_healthcheck_at': self.last_healthcheck_at.isoformat() if self.last_healthcheck_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LogIntentoPago(db.Model):
    """
    Log de intentos de pago fallidos con Getnet
    Tabla simple para registrar intentos fallidos sin crear ventas
    """
    __tablename__ = 'logs_intentos_pago'
    
    id = db.Column(db.Integer, primary_key=True)
    caja_codigo = db.Column(db.String(32), nullable=False, index=True)
    cajero = db.Column(db.String(64), nullable=True)
    total = db.Column(Numeric(10, 2), nullable=False)
    items_json = db.Column(db.JSON, nullable=False)  # JSON con lista de items
    motivo = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_logs_intentos_pago_caja_fecha', 'caja_codigo', 'created_at'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        return {
            'id': self.id,
            'caja_codigo': self.caja_codigo,
            'cajero': self.cajero,
            'total': float(self.total) if self.total else 0.0,
            'items_json': self.items_json if isinstance(self.items_json, (dict, list)) else json.loads(self.items_json) if self.items_json else [],
            'motivo': self.motivo,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class RegisterClose(db.Model):
    """Cierre de caja (guardado en base de datos)"""
    __tablename__ = 'register_closes'
    
    id = db.Column(db.Integer, primary_key=True)
    register_id = db.Column(db.String(50), nullable=False)
    register_name = db.Column(db.String(200), nullable=False)
    employee_id = db.Column(db.String(50), nullable=False)
    employee_name = db.Column(db.String(200), nullable=False)
    
    # Fechas
    shift_date = db.Column(db.String(50), nullable=True)
    opened_at = db.Column(db.String(200), nullable=True)
    closed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Totales esperados
    expected_cash = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    expected_debit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    expected_credit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Totales reales
    actual_cash = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    actual_debit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    actual_credit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Diferencias
    diff_cash = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    diff_debit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    diff_credit = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    difference_total = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Estadísticas
    total_sales = db.Column(db.Integer, default=0, nullable=False)
    total_amount = db.Column(Numeric(10, 2), default=0.0, nullable=False)
    
    # Notas y resolución
    notes = db.Column(Text, nullable=True)
    status = db.Column(db.String(50), default='pending', nullable=False)  # pending, balanced, resolved
    resolved_by = db.Column(db.String(200), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(Text, nullable=True)
    
    # P0-011: Idempotencia de cierre
    idempotency_key_close = db.Column(db.String(64), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices para mejor rendimiento
    __table_args__ = (
        Index('idx_register_closes_status', 'status'),
        Index('idx_register_closes_register_id', 'register_id'),
        Index('idx_register_closes_closed_at', 'closed_at'),
        Index('idx_register_closes_employee_id', 'employee_id'),
        Index('idx_register_closes_shift_date', 'shift_date'),  # Para consultas por turno
        Index('idx_register_closes_date_status', 'shift_date', 'status'),  # Índice compuesto para consultas frecuentes
    )
    
    def calculate_total_amount(self):
        """Calcula el total_amount como suma de montos reales si es 0"""
        if self.total_amount == 0:
            actual_cash = float(self.actual_cash or 0)
            actual_debit = float(self.actual_debit or 0)
            actual_credit = float(self.actual_credit or 0)
            total_recaudado = actual_cash + actual_debit + actual_credit
            if total_recaudado > 0:
                self.total_amount = total_recaudado
                return total_recaudado
        return float(self.total_amount or 0)
    
    def calculate_difference_total(self):
        """Calcula difference_total como suma de diferencias individuales si es 0"""
        if self.difference_total == 0:
            diff_cash = float(self.diff_cash or 0)
            diff_debit = float(self.diff_debit or 0)
            diff_credit = float(self.diff_credit or 0)
            total_diff = diff_cash + diff_debit + diff_credit
            if total_diff != 0:
                self.difference_total = total_diff
                return total_diff
        return float(self.difference_total or 0)
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        # Asegurar que los totales estén calculados
        self.calculate_total_amount()
        self.calculate_difference_total()
        
        return {
            'id': self.id,
            'register_id': self.register_id,
            'register_name': self.register_name,
            'employee_id': self.employee_id,
            'employee_name': self.employee_name,
            'shift_date': self.shift_date,
            'opened_at': self.opened_at,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'expected_cash': float(self.expected_cash) if self.expected_cash else 0.0,
            'expected_debit': float(self.expected_debit) if self.expected_debit else 0.0,
            'expected_credit': float(self.expected_credit) if self.expected_credit else 0.0,
            'actual_cash': float(self.actual_cash) if self.actual_cash else 0.0,
            'actual_debit': float(self.actual_debit) if self.actual_debit else 0.0,
            'actual_credit': float(self.actual_credit) if self.actual_credit else 0.0,
            'diff_cash': float(self.diff_cash) if self.diff_cash else 0.0,
            'diff_debit': float(self.diff_debit) if self.diff_debit else 0.0,
            'diff_credit': float(self.diff_credit) if self.diff_credit else 0.0,
            'difference_total': float(self.difference_total) if self.difference_total else 0.0,
            'total_sales': self.total_sales,
            'total_amount': float(self.total_amount) if self.total_amount else 0.0,
            'notes': self.notes,
            'status': self.status,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Employee(db.Model):
    """
    Empleado almacenado localmente.
    
    IMPORTANTE: El campo 'id' es único e INMUTABLE.
    - Se genera automáticamente como número secuencial simple (1, 2, 3, ...) para nuevos trabajadores
    - Los IDs antiguos pueden ser UUIDs (compatibilidad hacia atrás)
    - Nunca se puede cambiar, incluso si el trabajador vuelve a trabajar en el futuro
    - Permite mantener un historial completo del trabajador a través del tiempo
    - Si un trabajador vuelve después de un tiempo, se puede buscar por su ID único
    """
    __tablename__ = 'employees'
    
    id = db.Column(db.String(50), primary_key=True)  # ID único e inmutable - número simple (1, 2, 3...) o UUID (legacy)
    person_id = db.Column(db.String(50), nullable=True, index=True)
    employee_id = db.Column(db.String(50), nullable=True, index=True)
    
    # Información básica
    first_name = db.Column(db.String(200), nullable=True)
    last_name = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(400), nullable=False)  # Nombre completo
    
    # Información de autenticación
    pin = db.Column(db.String(50), nullable=True)  # PIN desde custom_fields.Pin (legacy, mantener para compatibilidad)
    pin_hash = db.Column(db.String(255), nullable=True, index=True)  # PIN hasheado para seguridad
    
    # Campos personalizados (JSON)
    custom_fields = db.Column(Text, nullable=True)  # JSON string con custom_fields de PHP POS
    
    # Información bancaria para transferencias
    rut = db.Column(db.String(20), nullable=True)  # RUT del trabajador
    banco = db.Column(db.String(100), nullable=True)  # Nombre del banco
    tipo_cuenta = db.Column(db.String(20), nullable=True)  # 'Corriente', 'Ahorro', 'Vista'
    numero_cuenta = db.Column(db.String(50), nullable=True)  # Número de cuenta bancaria
    email = db.Column(db.String(200), nullable=True)  # Email para notificaciones
    
    # Filtros
    cargo = db.Column(db.String(100), nullable=True, index=True)  # 'Cajero', 'Bartender', etc.
    is_bartender = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_cashier = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    deleted = db.Column(db.String(10), default='0', nullable=False)  # '0' o '1' desde PHP POS
    
    # Sincronización
    last_synced_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    synced_from_phppos = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índices compuestos para búsquedas comunes
    __table_args__ = (
        Index('idx_employees_cargo_active', 'cargo', 'is_active'),
        Index('idx_employees_bartender', 'is_bartender', 'is_active'),
        Index('idx_employees_cashier', 'is_cashier', 'is_active'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        custom_fields_dict = {}
        if self.custom_fields:
            try:
                custom_fields_dict = json.loads(self.custom_fields)
            except:
                pass
        
        return {
            'id': self.id,
            'person_id': self.person_id,
            'employee_id': self.employee_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'name': self.name,
            'pin': self.pin,
            'custom_fields': custom_fields_dict,
            'cargo': self.cargo,
            'is_bartender': self.is_bartender,
            'is_cashier': self.is_cashier,
            'is_active': self.is_active,
            'deleted': self.deleted,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SaleAuditLog(db.Model):
    """
    Auditoría de eventos críticos del POS (P0-013, P0-014, P1-016)
    Guarda en BD todos los eventos importantes para trazabilidad completa
    """
    __tablename__ = 'sale_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Tipo de evento
    event_type = db.Column(db.String(50), nullable=False, index=True)  # OPEN, BLIND_CLOSE_SUBMITTED, CLOSE_WITH_DIFF, etc.
    severity = db.Column(db.String(20), nullable=False, default='info', index=True)  # info, warning, error, critical
    
    # Actor (quién hizo la acción)
    actor_user_id = db.Column(db.String(50), nullable=True, index=True)
    actor_name = db.Column(db.String(200), nullable=False)
    
    # Contexto
    register_id = db.Column(db.String(50), nullable=True, index=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('pos_sales.id'), nullable=True, index=True)
    jornada_id = db.Column(db.Integer, db.ForeignKey('jornadas.id'), nullable=True, index=True)
    register_session_id = db.Column(db.Integer, db.ForeignKey('register_sessions.id'), nullable=True, index=True)
    
    # Payload JSON con detalles del evento
    payload_json = db.Column(Text, nullable=True)
    
    # IP y sesión
    ip_address = db.Column(db.String(45), nullable=True)
    session_id = db.Column(db.String(200), nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relaciones
    sale = db.relationship('PosSale', backref='audit_logs', lazy=True)
    jornada = db.relationship('Jornada', backref='audit_logs', lazy=True)
    register_session = db.relationship('RegisterSession', backref='audit_logs', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_audit_log_event_type', 'event_type', 'created_at'),
        Index('idx_audit_log_register', 'register_id', 'created_at'),
        Index('idx_audit_log_severity', 'severity', 'created_at'),
    )
    
    def to_dict(self):
        """Convierte el modelo a diccionario"""
        payload = {}
        if self.payload_json:
            try:
                payload = json.loads(self.payload_json)
            except:
                pass
        
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'actor_user_id': self.actor_user_id,
            'actor_name': self.actor_name,
            'register_id': self.register_id,
            'sale_id': self.sale_id,
            'jornada_id': self.jornada_id,
            'register_session_id': self.register_session_id,
            'payload': payload,
            'ip_address': self.ip_address,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

# PaymentAgent ya está definido arriba (línea 694), no duplicar aquí
