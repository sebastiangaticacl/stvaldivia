"""
Modelos de Inventario de Stock
Sistema completo de gestión de inventario de ingredientes con ubicaciones, movimientos y recetas.
"""
from datetime import datetime
from . import db
from sqlalchemy import Index, Numeric, Text, CheckConstraint
from decimal import Decimal


class IngredientCategory(db.Model):
    """Categorías de ingredientes (Destilado, Mixer, Insumo, etc.)"""
    __tablename__ = 'ingredient_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    description = db.Column(Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relación con ingredientes
    ingredients = db.relationship('Ingredient', backref='category', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<IngredientCategory {self.name}>'


class Ingredient(db.Model):
    """
    Ingrediente base (botella, insumo, etc.)
    Representa un tipo de ingrediente que se consume en las recetas.
    """
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('ingredient_categories.id'), nullable=True, index=True)
    
    # Unidad base de medida (ml, gramos, unidades, etc.)
    base_unit = db.Column(db.String(50), nullable=False, default='ml')  # ml, gr, unidad
    
    # Información de botella/empaque (opcional, para conversión)
    package_size = db.Column(Numeric(10, 3), nullable=True)  # Tamaño del empaque en unidad base (ej: 1000 ml)
    package_unit = db.Column(db.String(50), nullable=True)  # Unidad del empaque (ej: "botella", "caja")
    
    # Costo y precio
    cost_per_unit = db.Column(Numeric(10, 3), default=0.0, nullable=False)  # Costo por unidad base
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Metadatos
    description = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    stock_locations = db.relationship('IngredientStock', backref='ingredient', lazy=True, cascade='all, delete-orphan')
    recipe_items = db.relationship('RecipeIngredient', backref='ingredient', lazy=True, cascade='all, delete-orphan')
    movements = db.relationship('InventoryMovement', backref='ingredient', lazy=True)
    
    # Índices
    __table_args__ = (
        Index('idx_ingredients_active', 'is_active'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'base_unit': self.base_unit,
            'package_size': float(self.package_size) if self.package_size else None,
            'package_unit': self.package_unit,
            'cost_per_unit': float(self.cost_per_unit) if self.cost_per_unit else 0.0,
            'is_active': self.is_active,
            'description': self.description
        }
    
    def __repr__(self):
        return f'<Ingredient {self.name} ({self.base_unit})>'


class IngredientStock(db.Model):
    """
    Stock de un ingrediente en una ubicación específica (barra, bodega, etc.)
    """
    __tablename__ = 'ingredient_stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)  # "barra_principal", "bodega", etc.
    
    # Cantidad actual en unidad base (ej: ml)
    quantity = db.Column(Numeric(12, 3), nullable=False, default=0.0)
    
    # Información de lote/botella (opcional)
    batch_number = db.Column(db.String(100), nullable=True, index=True)
    expiry_date = db.Column(db.Date, nullable=True)
    
    # Metadatos
    notes = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_stock_ingredient_location', 'ingredient_id', 'location'),
        Index('idx_stock_location', 'location'),
        CheckConstraint('quantity >= 0', name='check_quantity_non_negative'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'location': self.location,
            'quantity': float(self.quantity) if self.quantity else 0.0,
            'batch_number': self.batch_number,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<IngredientStock {self.ingredient.name if self.ingredient else "?"} @ {self.location}: {self.quantity}>'


class Recipe(db.Model):
    """
    Receta: define qué ingredientes y cantidades se usan para un producto.
    Un producto puede tener una receta (si usa ingredientes) o no (ej: entradas).
    """
    __tablename__ = 'recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, unique=True, index=True)
    name = db.Column(db.String(200), nullable=True)  # Nombre opcional de la receta
    
    # Estado
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # Metadatos
    description = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relaciones
    product = db.relationship('Product', backref=db.backref('recipe', uselist=False, cascade='all, delete-orphan'))
    ingredients = db.relationship('RecipeIngredient', backref='recipe', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else None,
            'name': self.name,
            'is_active': self.is_active,
            'description': self.description,
            'ingredients': [ri.to_dict() for ri in self.ingredients] if self.ingredients else []
        }
    
    def __repr__(self):
        return f'<Recipe for Product {self.product_id}>'


class RecipeIngredient(db.Model):
    """
    Relación entre Receta e Ingrediente: define cuánto de cada ingrediente se usa por porción.
    """
    __tablename__ = 'recipe_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipes.id'), nullable=False, index=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    
    # Cantidad de ingrediente por porción (en unidad base del ingrediente)
    quantity_per_portion = db.Column(Numeric(10, 3), nullable=False)  # ej: 50 ml por trago
    
    # Tolerancia/merma estándar (opcional, en porcentaje)
    tolerance_percent = db.Column(Numeric(5, 2), default=0.0, nullable=False)  # ej: 5% de merma esperada
    
    # Orden de agregado (opcional, para mostrar orden en receta)
    order = db.Column(db.Integer, default=0, nullable=False)
    
    # Metadatos
    notes = db.Column(Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Índices
    __table_args__ = (
        Index('idx_recipe_ingredient', 'recipe_id', 'ingredient_id'),
        CheckConstraint('quantity_per_portion > 0', name='check_quantity_positive'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'recipe_id': self.recipe_id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'quantity_per_portion': float(self.quantity_per_portion) if self.quantity_per_portion else 0.0,
            'tolerance_percent': float(self.tolerance_percent) if self.tolerance_percent else 0.0,
            'order': self.order,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<RecipeIngredient {self.ingredient.name if self.ingredient else "?"}: {self.quantity_per_portion} per portion>'


class InventoryMovement(db.Model):
    """
    Movimiento de inventario: registra todas las entradas, salidas, ajustes y mermas.
    Proporciona trazabilidad completa del inventario.
    """
    __tablename__ = 'inventory_movements'
    
    # Tipos de movimiento
    TYPE_ENTRY = 'entrada'  # Entrada de stock (compra, reposición)
    TYPE_SALE = 'venta'  # Salida por venta
    TYPE_ADJUSTMENT = 'ajuste'  # Ajuste manual (conteo físico)
    TYPE_WASTE = 'merma'  # Merma registrada
    TYPE_CORRECTION = 'correccion'  # Corrección de error
    
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False, index=True)
    location = db.Column(db.String(100), nullable=False, index=True)
    
    # Tipo de movimiento
    movement_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Cantidad: positiva = entra, negativa = sale
    quantity = db.Column(Numeric(12, 3), nullable=False)
    
    # Referencia: ID de venta, compra, conteo, etc.
    reference_type = db.Column(db.String(50), nullable=True)  # 'sale', 'purchase', 'count', etc.
    reference_id = db.Column(db.String(100), nullable=True, index=True)  # ID de la referencia
    
    # Turno asociado (opcional, para movimientos durante turnos de bartender)
    turno_id = db.Column(db.Integer, db.ForeignKey('bartender_turnos.id'), nullable=True, index=True)
    
    # Usuario/responsable
    user_id = db.Column(db.String(100), nullable=True, index=True)
    user_name = db.Column(db.String(200), nullable=True)
    
    # Motivo/notas
    reason = db.Column(Text, nullable=True)
    notes = db.Column(Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Índices
    __table_args__ = (
        Index('idx_movements_ingredient_date', 'ingredient_id', 'created_at'),
        Index('idx_movements_location_date', 'location', 'created_at'),
        Index('idx_movements_type_date', 'movement_type', 'created_at'),
        Index('idx_movements_reference', 'reference_type', 'reference_id'),
        Index('idx_movements_turno', 'turno_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else None,
            'location': self.location,
            'movement_type': self.movement_type,
            'quantity': float(self.quantity) if self.quantity else 0.0,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'reason': self.reason,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        sign = '+' if self.quantity >= 0 else ''
        return f'<InventoryMovement {self.movement_type} {sign}{self.quantity} @ {self.location}>'



























