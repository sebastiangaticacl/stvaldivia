"""
Modelos para recetas y productos compuestos.
"""
from . import db

class LegacyIngredient(db.Model):
    """Modelo de Ingrediente (lo que se descuenta del inventario) - LEGACY"""
    __tablename__ = 'recipe_ingredients_legacy'  # Renombrado para evitar conflicto con inventory_stock_models
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True, index=True)
    unit = db.Column(db.String(50)) # ml, gr, unidad, etc.
    volume_ml = db.Column(db.Float, default=750.0) # Capacidad de la botella en ml
    cost = db.Column(db.Float, default=0.0)
    stock_quantity = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<LegacyIngredient {self.name}>'

class ProductRecipe(db.Model):
    """Relación entre Producto (Kit) e Ingredientes"""
    __tablename__ = 'product_recipes'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('recipe_ingredients_legacy.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False) # Cantidad de ingrediente usada
    
    # Relaciones
    product = db.relationship('Product', backref=db.backref('recipe_items', lazy=True))
    ingredient = db.relationship('LegacyIngredient', backref=db.backref('used_in', lazy=True))
    
    def __repr__(self):
        return f'<Recipe {self.product.name} uses {self.quantity} of {self.ingredient.name}>'
