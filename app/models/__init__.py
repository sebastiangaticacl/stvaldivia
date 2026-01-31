"""
Modelos de base de datos para el sistema BIMBA
"""
from flask_sqlalchemy import SQLAlchemy

# Instancia global de SQLAlchemy
db = SQLAlchemy()

# Importar modelos del kiosko
from .kiosk_models import Pago, PagoItem

# Importar modelos del POS
from .pos_models import (
    PosSession, PosSale, PosSaleItem, PosRegister, RegisterLock, RegisterSession, RegisterClose, 
    SaleAuditLog, Employee, PaymentIntent, PaymentAgent, LogIntentoPago
)

# Importar modelos de jornadas
from .jornada_models import Jornada, PlanillaTrabajador, AperturaCaja, SnapshotEmpleados, SnapshotCajas, SnapshotEmpleados, SnapshotCajas

# Importar modelos de turnos
from .shift_models import Shift

# Importar modelos de log de API
from .api_log_models import ApiConnectionLog

# Importar modelos de turnos de empleados
from .employee_payment_models import EmployeePayment
from .employee_shift_models import EmployeeShift, EmployeeSalaryConfig, FichaReviewLog

# Importar modelos de sueldos por cargo
from .cargo_salary_models import CargoSalaryConfig

# Importar modelos de cargos
from .cargo_models import Cargo

# Importar modelo de auditoría de cargos y sueldos
from .cargo_audit_models import CargoSalaryAuditLog

# Importar modelos de abonos y pagos excepcionales
from .employee_advance_models import EmployeeAdvance

# Importar modelo de auditoría
from .audit_log_models import AuditLog

# Importar modelo de notificaciones
# Importar modelos de inventario y recetas
from .inventory_models import InventoryItem
from .product_models import Product
from .recipe_models import LegacyIngredient, ProductRecipe

# Importar modelos de inventario de stock (nuevo sistema)
from .inventory_stock_models import (
    IngredientCategory, Ingredient as StockIngredient, IngredientStock,
    Recipe, RecipeIngredient, InventoryMovement
)

# Importar modelos de guardarropía
from .guardarropia_models import GuardarropiaItem

# Importar modelos de entregas y tracking de tickets
from .delivery_models import Delivery, FraudAttempt, TicketScan
from .sale_delivery_models import SaleDeliveryStatus, DeliveryItem

# Importar modelos de turnos de bartender
from .bartender_turno_models import (
    BartenderTurno, TurnoStockInicial, TurnoStockFinal,
    MermaInventario, TurnoDesviacionInventario, AlertaFugaTurno
)

# Importar modelos de programación de eventos
from .programacion_models import ProgramacionEvento, ProgramacionAsignacion

# Importar modelos de auditoría de caja superadmin
from .superadmin_sale_audit_models import SuperadminSaleAudit

# Importar modelos de logs del bot
from .bot_log_models import BotLog

# Importar modelos de tickets de entrega con QR
from .ticket_entrega_models import TicketEntrega, TicketEntregaItem, DeliveryLog

# Importar modelos de tickets de guardarropía con QR
from .guardarropia_ticket_models import GuardarropiaTicket, GuardarropiaTicketLog

# Importar modelos de ecommerce (venta de entradas)
from .ecommerce_models import Entrada, CheckoutSession

# Importar modelos de configuración del sistema
from .system_config_models import SystemConfig


__all__ = [
    'db', 
    'Pago', 'PagoItem',
    'PosSession', 'PosSale', 'PosSaleItem', 'PosRegister', 'RegisterLock', 'RegisterSession',
    'PaymentIntent', 'PaymentAgent', 
    'RegisterClose', 'SaleAuditLog', 'Employee', 'LogIntentoPago',
    'Jornada', 'PlanillaTrabajador', 'AperturaCaja', 'SnapshotEmpleados', 'SnapshotCajas',
    'Shift',
    'ApiConnectionLog',
    'EmployeeShift', 'EmployeeSalaryConfig', 'FichaReviewLog', 'EmployeePayment',
    'CargoSalaryConfig',
    'Cargo',
    'EmployeeAdvance',
    'AuditLog',
    'Notification',
    'InventoryItem', 'Product',
    'LegacyIngredient', 'ProductRecipe',
    # Nuevos modelos de inventario de stock
    'IngredientCategory', 'StockIngredient', 'IngredientStock',
    'Recipe', 'RecipeIngredient', 'InventoryMovement',
    # Modelos de guardarropía
    'GuardarropiaItem',
    # Modelos de entregas y tracking
    'Delivery', 'FraudAttempt', 'TicketScan',
    'SaleDeliveryStatus', 'DeliveryItem',
    # Modelos de turnos de bartender
    'BartenderTurno', 'TurnoStockInicial', 'TurnoStockFinal',
    'MermaInventario', 'TurnoDesviacionInventario', 'AlertaFugaTurno',
    # Modelos de programación de eventos
    'ProgramacionEvento', 'ProgramacionAsignacion',
    # Modelos de auditoría de caja superadmin
    'SuperadminSaleAudit',
    # Modelos de logs del bot
    'BotLog',
    # Modelos de tickets de entrega con QR
    'TicketEntrega', 'TicketEntregaItem', 'DeliveryLog',
    # Modelos de tickets de guardarropía con QR
    'GuardarropiaTicket', 'GuardarropiaTicketLog',
    # Modelos de ecommerce (venta de entradas)
    'Entrada', 'CheckoutSession',
    # Modelos de configuración del sistema
    'SystemConfig',
]

