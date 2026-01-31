# Mejoras de Lógica de Inventario

## 📊 Análisis del Sistema Actual

### Flujo Actual
1. **Venta creada** → No descuenta inventario automáticamente
2. **Entrega por bartender** → Descuenta inventario al entregar
3. **Método `apply_inventory_for_sale`** → Existe pero no se usa en flujo principal

### Problemas Identificados

1. **No hay validación previa de stock** antes de crear venta
2. **Queries N+1** en `apply_inventory_for_sale` (busca productos uno por uno)
3. **Mapeo hardcodeado** de ubicaciones desde `register_id`
4. **No hay cache** de recetas (se consultan cada vez)
5. **Permite stock negativo** sin validación adecuada
6. **No hay alertas** de stock bajo en tiempo real
7. **Transacciones no atómicas** en algunos casos
8. **Validación de recetas incompleta** (no valida que todos los ingredientes existan)
9. **No hay validación de unidades** de medida compatibles
10. **Logging insuficiente** para debugging

---

## 🎯 Mejoras Propuestas

### 1. Validación Previa de Stock
**Objetivo**: Validar stock disponible antes de permitir venta

**Implementación**:
- Crear método `validate_stock_availability(cart, location)`
- Verificar stock de todos los ingredientes necesarios
- Retornar lista de productos con stock insuficiente
- Mostrar alertas en frontend antes de confirmar venta

### 2. Cache de Recetas
**Objetivo**: Mejorar rendimiento evitando queries repetidas

**Implementación**:
- Cachear recetas en memoria (TTL: 5 minutos)
- Invalidar cache cuando se modifica receta
- Usar `functools.lru_cache` o Redis si está disponible

### 3. Optimización de Queries
**Objetivo**: Evitar N+1 queries

**Implementación**:
- Cargar todos los productos de una vez con `query.filter(id.in_(ids))`
- Usar `joinedload` para cargar relaciones
- Batch loading de recetas e ingredientes

### 4. Mapeo Dinámico de Ubicaciones
**Objetivo**: Usar configuración de PosRegister en lugar de hardcode

**Implementación**:
- Leer `location` desde `PosRegister` si existe
- Fallback a mapeo por defecto si no está configurado
- Permitir configuración por TPV

### 5. Validación de Recetas Completas
**Objetivo**: Validar que todas las recetas estén completas antes de procesar

**Implementación**:
- Validar que todos los ingredientes de la receta existan
- Validar que todos los ingredientes tengan stock configurado
- Validar unidades de medida compatibles

### 6. Sistema de Alertas de Stock Bajo
**Objetivo**: Alertar cuando el stock está bajo

**Implementación**:
- Configurar umbrales mínimos por ingrediente
- Verificar stock al aplicar inventario
- Generar alertas en dashboard de admin

### 7. Transacciones Atómicas Mejoradas
**Objetivo**: Garantizar consistencia de datos

**Implementación**:
- Usar `db.session.begin_nested()` para savepoints
- Rollback automático en caso de error
- Validar stock con lock de fila para evitar race conditions

### 8. Validación de Unidades de Medida
**Objetivo**: Validar compatibilidad de unidades

**Implementación**:
- Definir unidades compatibles (ml ↔ ml, gr ↔ gr)
- Validar conversiones si es necesario
- Alertar si hay incompatibilidad

### 9. Mejor Logging y Trazabilidad
**Objetivo**: Facilitar debugging y auditoría

**Implementación**:
- Log detallado de cada movimiento
- Incluir contexto completo (venta, producto, ingrediente)
- Generar reportes de consumo

### 10. Manejo de Errores Granular
**Objetivo**: Proporcionar mensajes de error específicos

**Implementación**:
- Excepciones específicas por tipo de error
- Mensajes de error claros y accionables
- Códigos de error para frontend

---

## 🚀 Plan de Implementación

### Fase 1: Optimizaciones Críticas
1. ✅ Cache de recetas
2. ✅ Optimización de queries (evitar N+1)
3. ✅ Mapeo dinámico de ubicaciones

### Fase 2: Validaciones
4. ✅ Validación previa de stock
5. ✅ Validación de recetas completas
6. ✅ Validación de unidades

### Fase 3: Mejoras de UX
7. ✅ Sistema de alertas de stock bajo
8. ✅ Mejor logging y trazabilidad
9. ✅ Manejo de errores granular

### Fase 4: Robustez
10. ✅ Transacciones atómicas mejoradas
11. ✅ Lock de filas para evitar race conditions

---

## 📝 Notas Técnicas

### Cache de Recetas
```python
from functools import lru_cache
from datetime import datetime, timedelta

@lru_cache(maxsize=1000)
def get_recipe_cached(product_id: int, cache_time: str):
    # cache_time cambia cada 5 minutos para invalidar
    return Recipe.query.filter_by(product_id=product_id).first()
```

### Validación de Stock
```python
def validate_stock_availability(cart, location):
    """
    Valida stock disponible para todos los productos del carrito.
    Retorna lista de productos con stock insuficiente.
    """
    issues = []
    for item in cart:
        product = get_product(item['product_id'])
        if product.is_kit:
            recipe = get_recipe(product.id)
            for ingredient in recipe.ingredients:
                stock = get_stock(ingredient.id, location)
                required = ingredient.quantity_per_portion * item['quantity']
                if stock.quantity < required:
                    issues.append({
                        'product': product.name,
                        'ingredient': ingredient.name,
                        'required': required,
                        'available': stock.quantity
                    })
    return issues
```

---

**Última actualización**: 2024-12-19

