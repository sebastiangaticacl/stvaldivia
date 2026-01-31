# INSTRUCCIONES PARA COMPLETAR IMPLEMENTACIÓN P0

## PASO 1: Ejecutar Migración

```bash
cd /Users/sebagatica/tickets_cursor_clean
python3 migrate_p0_hardening.py
```

Esto creará:
- Tabla `register_sessions`
- Tabla `sale_audit_logs`
- Columnas en `pos_sales` (jornada_id, no_revenue, idempotency_key, is_cancelled, etc.)
- Columna `idempotency_key_close` en `register_closes`

## PASO 2: Actualizar Rutas Críticas

### 2.1 Actualizar `app/blueprints/pos/views/sales.py`

En la función `api_create_sale()`, agregar después de la línea 486:

```python
# ==========================================
# P0-005: Validar RegisterSession OPEN
# ==========================================
from app.helpers.register_session_service import RegisterSessionService
from app.helpers.idempotency_helper import generate_sale_idempotency_key

# Validar que existe sesión abierta
can_sell, error_msg = RegisterSessionService.can_sell_in_register(register_id)
if not can_sell:
    # Registrar auditoría
    from app.models.pos_models import SaleAuditLog
    import json
    audit = SaleAuditLog(
        event_type='SALE_BLOCKED_NO_SESSION',
        severity='warning',
        actor_user_id=employee_id,
        actor_name=employee_name,
        register_id=register_id,
        payload_json=json.dumps({'error': error_msg})
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({'success': False, 'error': error_msg}), 403

# Obtener sesión activa
active_session = RegisterSessionService.get_active_session(register_id)
if not active_session:
    return jsonify({'success': False, 'error': 'No hay sesión abierta para esta caja'}), 403

# P0-002, P0-004: Validar jornada activa
jornada = Jornada.query.get(active_session.jornada_id)
if not jornada or jornada.estado_apertura != 'abierto':
    return jsonify({'success': False, 'error': 'La jornada no está abierta'}), 403

jornada_id = active_session.jornada_id
shift_date = active_session.shift_date

# P0-007: Idempotencia de venta
idempotency_key = generate_sale_idempotency_key(cart, register_id, employee_id, payment_type, total)
existing_sale = PosSale.query.filter_by(idempotency_key=idempotency_key).first()
if existing_sale:
    # Retornar venta existente (idempotencia)
    return jsonify({
        'success': True,
        'sale_id': existing_sale.id,
        'sale_id_local': existing_sale.id,
        'message': 'Venta ya procesada (idempotencia)',
        'ticket_printed': 'no_intentado'
    }), 200
```

Luego, en la creación de `PosSale` (alrededor de línea 669), actualizar:

```python
# Crear venta local
local_sale = PosSale(
    sale_id_phppos=None,
    total_amount=round_currency(to_decimal(total)) if not is_courtesy else 0.0,
    payment_type=payment_type_normalized,
    payment_cash=payment_cash,
    payment_debit=payment_debit,
    payment_credit=payment_credit,
    employee_id=employee_id,
    employee_name=employee_name,
    register_id=register_id,
    register_name=session.get('pos_register_name', 'Caja'),
    shift_date=shift_date,  # Ya validado desde active_session
    jornada_id=jornada_id,  # P0-004: Asociación fuerte
    synced_to_phppos=False,
    is_courtesy=is_courtesy,
    is_test=is_test,
    no_revenue=(is_superadmin_register or is_courtesy or is_test),  # P0-016
    idempotency_key=idempotency_key  # P0-007
)
```

### 2.2 Actualizar `app/blueprints/pos/views/register.py`

En `api_register_summary()`, filtrar ventas no revenue (P0-006):

```python
# Obtener ventas locales de esta sesión/caja
register_sales = PosSale.query.filter_by(
    register_id=str(register_id),
    shift_date=shift_date
).filter(
    PosSale.is_cancelled == False,  # P0-008
    PosSale.no_revenue == False,  # P0-006, P0-016
    PosSale.is_courtesy == False,  # P0-006
    PosSale.is_test == False  # P0-006
).all()
```

En `api_close_register()`, agregar:
- Validación de RegisterSession
- Idempotencia de cierre
- Cierre a ciegas (no mostrar expected al cajero)

### 2.3 Crear endpoint de cancelación (P0-008)

Agregar en `app/blueprints/pos/views/sales.py`:

```python
@caja_bp.route('/api/sale/<int:sale_id>/cancel', methods=['POST'])
def api_cancel_sale(sale_id):
    """API: Cancelar una venta (P0-008) - Solo admin/superadmin"""
    # Validar permisos
    is_admin = session.get('admin_logged_in', False)
    if not is_admin:
        return jsonify({'success': False, 'error': 'No autorizado'}), 403
    
    data = request.get_json()
    reason = data.get('reason', '').strip()
    
    if not reason or len(reason) < 5:
        return jsonify({'success': False, 'error': 'Motivo obligatorio (mínimo 5 caracteres)'}), 400
    
    try:
        sale = PosSale.query.get(sale_id)
        if not sale:
            return jsonify({'success': False, 'error': 'Venta no encontrada'}), 404
        
        if sale.is_cancelled:
            return jsonify({'success': False, 'error': 'La venta ya está cancelada'}), 400
        
        # Cancelar venta
        sale.is_cancelled = True
        sale.cancelled_at = datetime.now(CHILE_TZ).replace(tzinfo=None)
        sale.cancelled_by = session.get('admin_username', 'Admin')
        sale.cancelled_reason = reason
        
        db.session.commit()
        
        # Registrar auditoría
        from app.models.pos_models import SaleAuditLog
        import json as json_lib
        audit = SaleAuditLog(
            event_type='SALE_CANCELLED',
            severity='warning',
            actor_user_id=session.get('admin_username'),
            actor_name=session.get('admin_username', 'Admin'),
            register_id=sale.register_id,
            sale_id=sale.id,
            jornada_id=sale.jornada_id,
            payload_json=json_lib.dumps({'reason': reason})
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Venta cancelada correctamente'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error al cancelar venta: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

## PASO 3: Actualizar Frontend para Cierre a Ciegas (P0-009)

En `app/templates/pos/close_register.html`, modificar para que el cajero NO vea `expected_*`:

1. Ocultar sección de "Totales Esperados" para rol cajero
2. Solo mostrar inputs: efectivo, débito, crédito
3. Después de enviar, mostrar solo "Cierre recibido correctamente"
4. Admin ve comparación en vista separada

## PASO 4: Actualizar SocketIO (P0-015)

En `app/blueprints/pos/views/sales.py`, modificar emisión de eventos:

```python
# En lugar de emitir datos completos:
socketio.emit('pos_sale_created', {
    'register_id': register_id,
    'event': 'sale_created',
    'sale_id': local_sale.id,
    'created_at': datetime.now(CHILE_TZ).isoformat()
}, namespace='/pos')

# Para admin, emitir en namespace separado con datos agregados
if is_admin:
    socketio.emit('pos_sale_created_admin', {
        'sale': local_sale.to_dict(),
        'register_id': register_id
    }, namespace='/admin')
```

## PASO 5: Corregir Bug de Planilla

Investigar en `app/routes.py` función `api_agregar_trabajador_planilla()`:
- Verificar nombres de inputs en template
- Verificar endpoint receptor
- Verificar CSRF token
- Verificar que se hace commit

## PASO 6: Crear Tests

Crear `TESTS_POS.md` con verificaciones manuales para cada P0.

## PASO 7: Actualizar Auditoría

Actualizar `AUDITORIA_POS.md` marcando cada P0 como:
- ✅ RESUELTO
- ⚠️ PARCIAL
- ❌ PENDIENTE











