# Estrategia de Pasarelas de Pago

## 📊 Estado Actual del Sistema

### Métodos de Pago Implementados
- ✅ **Efectivo**: Registrado manualmente, sin validación
- ✅ **Débito**: Registrado manualmente, sin pasarela
- ✅ **Crédito**: Registrado manualmente, sin pasarela
- ✅ **Cortesía**: Para superadmin, monto $0

### Infraestructura Existente
- ✅ `KlapClient` parcialmente implementado (`app/infrastructure/external/klap_client.py`)
- ✅ Modelo `KlapTransaction` para almacenar transacciones
- ⚠️ **Problema**: Klap no está integrado en el flujo de ventas del POS
- ❌ No hay webhooks de pagos implementados
- ❌ No hay validación de pagos en tiempo real

---

## 🎯 Objetivos

1. **Integrar pasarelas de pago reales** para validar pagos con tarjeta
2. **Mantener compatibilidad** con pagos manuales (efectivo)
3. **Soporte múltiple** para diferentes pasarelas según necesidad
4. **Trazabilidad completa** de todas las transacciones
5. **Manejo de errores robusto** y reversión de transacciones

---

## 🏗️ Arquitectura Propuesta

### 1. Sistema de Pasarelas Múltiples

```
┌─────────────────────────────────────────┐
│         POS Sales Interface             │
│  (app/blueprints/pos/views/sales.py)   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Payment Gateway Service            │
│  (app/services/payment_gateway_service) │
│  - Route payment to correct gateway     │
│  - Handle retries and errors            │
│  - Process webhooks                    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│ Klap Client │  │ Transbank   │
│             │  │ (futuro)    │
└─────────────┘  └─────────────┘
```

### 2. Modelos de Datos

#### PaymentGateway (NUEVO)
```python
class PaymentGateway(db.Model):
    """Configuración de pasarelas de pago disponibles"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 'klap', 'transbank', etc.
    display_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    config = db.Column(JSON)  # Configuración específica (API keys, URLs, etc.)
    supported_methods = db.Column(JSON)  # ['credit', 'debit', 'cash']
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### PaymentTransaction (NUEVO)
```python
class PaymentTransaction(db.Model):
    """Transacciones de pago (unificadas para todas las pasarelas)"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Relación con venta
    pos_sale_id = db.Column(db.Integer, db.ForeignKey('pos_sales.id'), nullable=True)
    
    # Pasarela utilizada
    gateway_name = db.Column(db.String(50), nullable=False)  # 'klap', 'manual', etc.
    gateway_transaction_id = db.Column(db.String(100), nullable=True)  # ID en la pasarela
    
    # Monto y método
    amount = db.Column(Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='CLP')
    payment_method = db.Column(db.String(50), nullable=False)  # 'cash', 'debit', 'credit'
    
    # Estado
    status = db.Column(db.String(50), nullable=False)  # 'pending', 'approved', 'rejected', 'cancelled'
    status_message = db.Column(db.Text, nullable=True)
    
    # Información adicional
    metadata = db.Column(JSON, nullable=True)  # Datos específicos de la pasarela
    webhook_data = db.Column(JSON, nullable=True)  # Datos del webhook recibido
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)
```

---

## 🔧 Implementación Propuesta

### Fase 1: Infraestructura Base

#### 1.1 Crear Payment Gateway Service
**Archivo**: `app/services/payment_gateway_service.py`

```python
class PaymentGatewayService:
    """Servicio unificado para manejar múltiples pasarelas de pago"""
    
    def __init__(self):
        self.gateways = {}
        self._load_gateways()
    
    def process_payment(self, amount, payment_method, gateway_name=None, **kwargs):
        """Procesa un pago usando la pasarela especificada"""
        # 1. Determinar pasarela a usar
        # 2. Validar método de pago
        # 3. Crear transacción
        # 4. Procesar pago
        # 5. Guardar resultado
        pass
    
    def handle_webhook(self, gateway_name, payload, signature):
        """Procesa webhook de una pasarela"""
        pass
```

#### 1.2 Actualizar PosSale Model
Agregar relación con `PaymentTransaction`:
```python
# En app/models/pos_models.py
class PosSale(db.Model):
    # ... campos existentes ...
    
    # Relación con transacciones de pago
    payment_transactions = db.relationship(
        'PaymentTransaction', 
        backref='sale', 
        lazy=True
    )
```

### Fase 2: Integración Klap

#### 2.1 Completar KlapClient
- ✅ Ya existe `app/infrastructure/external/klap_client.py`
- ⚠️ **Problema conocido**: Campo `payment_methods` no está claro
- 🔧 **Solución**: Contactar soporte de Klap o usar formato alternativo

#### 2.2 Integrar Klap en el Flujo de Ventas
**Modificar**: `app/blueprints/pos/views/sales.py`

```python
# En api_create_sale()
if payment_type_normalized in ['Débito', 'Crédito']:
    # Usar pasarela de pago
    gateway_service = PaymentGatewayService()
    result = gateway_service.process_payment(
        amount=total,
        payment_method=payment_type_normalized.lower(),
        gateway_name='klap',
        customer_email=customer_email,  # Si está disponible
        # ... otros datos
    )
    
    if not result['success']:
        return jsonify({'success': False, 'error': result['error']}), 400
    
    # Guardar transacción
    payment_transaction = PaymentTransaction(...)
    db.session.add(payment_transaction)
else:
    # Pago manual (efectivo)
    payment_transaction = PaymentTransaction(
        gateway_name='manual',
        payment_method='cash',
        status='approved',
        ...
    )
```

#### 2.3 Webhook Handler para Klap
**Crear**: `app/routes/payment_webhooks.py`

```python
@payment_bp.route('/webhook/klap', methods=['POST'])
def klap_webhook():
    """Recibe webhooks de Klap"""
    # 1. Verificar firma
    # 2. Procesar webhook
    # 3. Actualizar transacción
    # 4. Actualizar venta si es necesario
    pass
```

### Fase 3: Interfaz de Usuario

#### 3.1 Actualizar Template de Ventas
**Modificar**: `app/templates/pos/sales.html`

- Agregar indicador de "Procesando pago..." para tarjetas
- Mostrar estado de transacción en tiempo real
- Manejar errores de pago de forma amigable

#### 3.2 Panel de Administración
**Crear**: `app/routes/payment_gateway_admin_routes.py`

- Listar pasarelas configuradas
- Configurar credenciales
- Ver transacciones
- Reintentar transacciones fallidas

---

## 📋 Pasarelas de Pago Recomendadas para Chile

### 1. Klap ✅ (Ya parcialmente implementado)
- **Ventajas**: 
  - API moderna
  - Soporte múltiples métodos (tarjeta, efectivo, transferencia)
  - Documentación disponible
- **Desventajas**:
  - Problema conocido con `payment_methods`
  - Requiere configuración en panel

### 2. Transbank Webpay Plus
- **Ventajas**:
  - Estándar en Chile
  - Ampliamente usado
  - Buena documentación
- **Desventajas**:
  - Requiere certificados
  - Integración más compleja

### 3. Mercado Pago
- **Ventajas**:
  - Fácil integración
  - Buena UX
- **Desventajas**:
  - Comisiones más altas

### 4. Flow
- **Ventajas**:
  - Popular en Chile
  - Múltiples métodos
- **Desventajas**:
  - Menos documentación pública

---

## 🔐 Consideraciones de Seguridad

1. **Nunca almacenar datos de tarjeta** en la base de datos
2. **Validar firmas de webhooks** siempre
3. **Usar HTTPS** para todas las comunicaciones
4. **Implementar idempotencia** en transacciones
5. **Logs de auditoría** para todas las transacciones
6. **Manejo seguro de API keys** (variables de entorno)

---

## 📊 Flujo de Pago Propuesto

### Pago con Tarjeta (Débito/Crédito)
```
1. Usuario selecciona productos y presiona "Pagar"
2. Selecciona método: "Débito" o "Crédito"
3. Sistema crea orden en pasarela (Klap)
4. Redirige a checkout de Klap (si es necesario)
5. Usuario completa pago en Klap
6. Klap envía webhook con resultado
7. Sistema actualiza transacción y venta
8. Muestra confirmación al usuario
```

### Pago en Efectivo (Manual)
```
1. Usuario selecciona productos y presiona "Pagar"
2. Selecciona método: "Efectivo"
3. Sistema crea transacción manual (status: approved)
4. Crea venta inmediatamente
5. Muestra confirmación
```

---

## 🚀 Plan de Implementación

### Sprint 1: Infraestructura Base
- [ ] Crear modelo `PaymentGateway`
- [ ] Crear modelo `PaymentTransaction`
- [ ] Crear `PaymentGatewayService`
- [ ] Migración de base de datos

### Sprint 2: Integración Klap
- [ ] Completar `KlapClient` (resolver problema de `payment_methods`)
- [ ] Integrar Klap en flujo de ventas
- [ ] Crear webhook handler para Klap
- [ ] Probar en sandbox

### Sprint 3: Interfaz de Usuario
- [ ] Actualizar template de ventas
- [ ] Agregar indicadores de estado
- [ ] Manejo de errores mejorado
- [ ] Panel de administración de pasarelas

### Sprint 4: Testing y Producción
- [ ] Pruebas end-to-end
- [ ] Documentación
- [ ] Deploy a producción
- [ ] Monitoreo

---

## ❓ Preguntas para Definir

1. **¿Qué pasarela(s) queremos usar?**
   - Solo Klap
   - Klap + Transbank
   - Otra(s)

2. **¿Cómo manejar pagos con tarjeta en el POS físico?**
   - Integración con terminal físico (TPV)
   - Solo online (redirección a checkout)
   - Ambos

3. **¿Necesitamos soporte para pagos diferidos?**
   - Pagos en cuotas
   - Pagos postergados

4. **¿Qué hacer con pagos fallidos?**
   - Reintentar automáticamente
   - Permitir cambio a otro método
   - Cancelar venta

5. **¿Necesitamos conciliación automática?**
   - Sincronización con extractos bancarios
   - Reportes de conciliación

---

## 📝 Notas Técnicas

### Variables de Entorno Necesarias
```bash
# Klap
KLAP_API_KEY=...
KLAP_SECRET_KEY=...
KLAP_ENVIRONMENT=sandbox|production
KLAP_API_URL=...

# Transbank (si se implementa)
TRANSBANK_COMMERCE_CODE=...
TRANSBANK_API_KEY=...
TRANSBANK_ENVIRONMENT=integration|production
```

### Endpoints de Webhook
```
POST /api/payments/webhook/klap
POST /api/payments/webhook/transbank
```

---

## 🔄 Próximos Pasos

1. **Revisar este documento** y definir prioridades
2. **Decidir pasarelas** a implementar
3. **Resolver problema de Klap** `payment_methods`
4. **Comenzar Sprint 1** (infraestructura base)

---

**Última actualización**: 2024-12-19
**Autor**: Sistema de Auditoría

