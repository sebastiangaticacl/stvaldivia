# TESTS POS - VERIFICACIONES P0

**Fecha:** 2025-12-12  
**Sistema:** BIMBA POS  
**Objetivo:** Verificar que todos los hallazgos P0 están correctamente implementados

---

## PREPARACIÓN

1. **Ejecutar migración:**
   ```bash
   cd /Users/sebagatica/tickets_cursor_clean
   python3 migrate_p0_hardening.py
   ```

2. **Verificar que el servidor esté corriendo:**
   ```bash
   python3 run_local.py
   ```

3. **Abrir navegador:**
   - URL: `http://127.0.0.1:5001`
   - Login como admin: `sebagatica` (o el usuario configurado)

---

## TESTS P0-001, P0-003, P0-010: ESTADO EXPLÍCITO DE CAJA

### Test 1.1: Abrir caja sin jornada activa → DEBE FALLAR

**Pasos:**
1. Asegurarse de que NO hay jornada abierta (o cerrar la existente)
2. Ir a `/admin/jornada` y verificar que no hay jornada con `estado_apertura='abierto'`
3. Intentar abrir una caja desde `/caja/register`
4. Seleccionar una caja y confirmar apertura

**Resultado Esperado:**
- ❌ Debe mostrar error: "No hay jornada abierta. Debes abrir una jornada antes de abrir una caja."
- ❌ NO debe crear `RegisterSession`
- ❌ NO debe bloquear la caja

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models import db
from app.models.pos_models import RegisterSession
from app.models.jornada_models import Jornada

app = create_app()
with app.app_context():
    # Verificar que no hay sesiones sin jornada
    sessions_sin_jornada = RegisterSession.query.filter(
        ~RegisterSession.jornada_id.in_(db.session.query(Jornada.id))
    ).count()
    print(f'Sesiones sin jornada válida: {sessions_sin_jornada} (debe ser 0)')
"
```

---

### Test 1.2: Abrir caja con jornada activa → DEBE CREAR RegisterSession

**Pasos:**
1. Crear/abrir una jornada desde `/admin/jornada`
2. Ir a `/caja/register`
3. Seleccionar una caja y confirmar apertura

**Resultado Esperado:**
- ✅ Debe crear `RegisterSession` con `status='OPEN'`
- ✅ Debe tener `jornada_id` válido
- ✅ Debe tener `shift_date` de la jornada
- ✅ Debe redirigir a `/caja/ventas`

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import RegisterSession

app = create_app()
with app.app_context():
    open_sessions = RegisterSession.query.filter_by(status='OPEN').all()
    print(f'Sesiones abiertas: {len(open_sessions)}')
    for s in open_sessions:
        print(f'  - Caja {s.register_id}, Jornada {s.jornada_id}, Abierta por {s.opened_by_employee_name}')
"
```

---

## TESTS P0-002, P0-004: VALIDACIÓN TURNO/JORNADA

### Test 2.1: Crear venta sin jornada activa → DEBE FALLAR

**Pasos:**
1. Cerrar todas las jornadas activas
2. Intentar crear una venta desde `/caja/ventas`
3. Agregar productos al carrito
4. Intentar procesar pago

**Resultado Esperado:**
- ❌ Debe mostrar error: "No hay sesión abierta para esta caja" o "La jornada no está abierta"
- ❌ NO debe crear `PosSale`
- ❌ Debe registrar evento de auditoría `SALE_BLOCKED_NO_SESSION`

---

### Test 2.2: Crear venta con jornada activa → DEBE FUNCIONAR

**Pasos:**
1. Abrir jornada desde `/admin/jornada`
2. Abrir caja desde `/caja/register`
3. Ir a `/caja/ventas`
4. Agregar productos y procesar pago

**Resultado Esperado:**
- ✅ Debe crear `PosSale` con `jornada_id` válido (NO NULL)
- ✅ Debe tener `shift_date` válido
- ✅ Debe asociarse a `RegisterSession` activa

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import PosSale

app = create_app()
with app.app_context():
    ventas_sin_jornada = PosSale.query.filter(PosSale.jornada_id.is_(None)).count()
    print(f'Ventas sin jornada_id: {ventas_sin_jornada} (debe ser 0 después de migración)')
    
    ventas_recientes = PosSale.query.order_by(PosSale.created_at.desc()).limit(5).all()
    print(f'\nÚltimas 5 ventas:')
    for v in ventas_recientes:
        print(f'  - ID {v.id}: jornada_id={v.jornada_id}, shift_date={v.shift_date}')
"
```

---

## TESTS P0-005: IMPEDIR VENTAS EN CAJA CERRADA

### Test 5.1: Crear venta sin RegisterSession OPEN → DEBE FALLAR

**Pasos:**
1. Abrir jornada y caja
2. Cerrar la caja (sin cerrar jornada)
3. Intentar crear una venta

**Resultado Esperado:**
- ❌ Debe mostrar error: "No hay sesión abierta para esta caja. Debe abrir la caja antes de vender."
- ❌ NO debe crear venta
- ❌ Debe registrar auditoría `SALE_BLOCKED_NO_SESSION`

---

## TESTS P0-006, P0-016: EXCLUIR CORTESÍA/PRUEBA DE TOTALES

### Test 6.1: Verificar que cortesías NO cuentan en totales

**Pasos:**
1. Abrir jornada y caja SUPERADMIN
2. Crear venta de cortesía (tipo_operacion='CORTESIA')
3. Crear venta normal en otra caja
4. Ver resumen de cierre de la caja normal

**Resultado Esperado:**
- ✅ La venta de cortesía NO debe aparecer en `api_register_summary` de otras cajas
- ✅ `total_cash`, `total_debit`, `total_credit` NO deben incluir cortesías
- ✅ La venta de cortesía debe tener `is_courtesy=True` y `no_revenue=True`

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import PosSale

app = create_app()
with app.app_context():
    cortesias = PosSale.query.filter_by(is_courtesy=True).all()
    pruebas = PosSale.query.filter_by(is_test=True).all()
    no_revenue = PosSale.query.filter_by(no_revenue=True).all()
    
    print(f'Ventas de cortesía: {len(cortesias)}')
    print(f'Ventas de prueba: {len(pruebas)}')
    print(f'Ventas no_revenue: {len(no_revenue)}')
    
    # Verificar que todas las cortesías y pruebas tienen no_revenue=True
    cortesias_sin_no_revenue = [v for v in cortesias if not v.no_revenue]
    pruebas_sin_no_revenue = [v for v in pruebas if not v.no_revenue]
    
    if cortesias_sin_no_revenue:
        print(f'⚠️  {len(cortesias_sin_no_revenue)} cortesías sin no_revenue=True')
    if pruebas_sin_no_revenue:
        print(f'⚠️  {len(pruebas_sin_no_revenue)} pruebas sin no_revenue=True')
"
```

---

## TESTS P0-007: IDEMPOTENCIA DE VENTA

### Test 7.1: Doble-click en crear venta → NO DEBE DUPLICAR

**Pasos:**
1. Abrir jornada y caja
2. Agregar productos al carrito
3. Hacer doble-click rápido en botón "Procesar Pago"
4. Verificar en BD

**Resultado Esperado:**
- ✅ Solo debe crear UNA venta
- ✅ La segunda petición debe retornar la venta existente (200 OK)
- ✅ Ambas ventas deben tener el mismo `idempotency_key`

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import PosSale
from collections import Counter

app = create_app()
with app.app_context():
    # Buscar ventas con idempotency_key duplicado
    ventas_con_key = PosSale.query.filter(PosSale.idempotency_key.isnot(None)).all()
    keys = [v.idempotency_key for v in ventas_con_key]
    duplicados = [k for k, count in Counter(keys).items() if count > 1]
    
    if duplicados:
        print(f'❌ ERROR: {len(duplicados)} idempotency_keys duplicados encontrados')
        for key in duplicados[:5]:
            ventas = [v for v in ventas_con_key if v.idempotency_key == key]
            print(f'  Key {key}: {len(ventas)} ventas')
    else:
        print('✅ No hay idempotency_keys duplicados')
"
```

---

## TESTS P0-008: CANCELACIÓN DE VENTAS

### Test 8.1: Cancelar venta como admin → DEBE FUNCIONAR

**Pasos:**
1. Crear una venta normal
2. Como admin, hacer POST a `/caja/api/sale/<sale_id>/cancel`
3. Enviar `{"reason": "Error en la venta, cliente canceló"}`
4. Verificar en BD

**Resultado Esperado:**
- ✅ La venta debe tener `is_cancelled=True`
- ✅ Debe tener `cancelled_at`, `cancelled_by`, `cancelled_reason`
- ✅ Debe crear registro en `SaleAuditLog` con `event_type='SALE_CANCELLED'`
- ✅ La venta NO debe contar en totales de cierre

**Comando de verificación:**
```bash
curl -X POST http://127.0.0.1:5001/caja/api/sale/1/cancel \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"reason": "Prueba de cancelación"}'
```

---

### Test 8.2: Cancelar venta como cajero → DEBE FALLAR

**Pasos:**
1. Login como cajero (no admin)
2. Intentar cancelar una venta

**Resultado Esperado:**
- ❌ Debe retornar 403 "No autorizado. Solo administradores pueden cancelar ventas."

---

## TESTS P0-009: CIERRE A CIEGAS

### Test 9.1: Cajero NO ve totales esperados

**Pasos:**
1. Login como cajero
2. Crear algunas ventas
3. Ir a cierre de caja
4. Verificar que NO se muestren `expected_cash`, `expected_debit`, `expected_credit`
5. Ingresar montos reales y enviar

**Resultado Esperado:**
- ✅ El frontend NO debe llamar a `/caja/api/register-summary` antes de enviar
- ✅ Solo debe mostrar inputs: efectivo, débito, crédito
- ✅ Después de enviar, solo debe mostrar "Cierre recibido correctamente"
- ✅ NO debe mostrar diferencias ni comparación

**Verificación manual:**
- Abrir DevTools → Network
- Verificar que NO hay llamada a `register-summary` en el flujo de cierre
- Verificar que la respuesta del backend NO incluye `expected_*` para cajero

---

### Test 9.2: Admin SÍ ve comparación

**Pasos:**
1. Login como admin
2. Ver cierres pendientes desde vista admin
3. Verificar que se muestran `expected` vs `actual` y diferencias

**Resultado Esperado:**
- ✅ Admin puede ver comparación completa
- ✅ Se muestran diferencias y alertas

---

## TESTS P0-011: IDEMPOTENCIA DE CIERRE

### Test 11.1: Doble-submit de cierre → NO DEBE DUPLICAR

**Pasos:**
1. Abrir jornada y caja
2. Crear algunas ventas
3. Ir a cierre de caja
4. Ingresar montos y hacer doble-click en "Verificar Cierre"
5. Verificar en BD

**Resultado Esperado:**
- ✅ Solo debe crear UN `RegisterClose`
- ✅ La segunda petición debe retornar el cierre existente (200 OK)
- ✅ Ambos cierres deben tener el mismo `idempotency_key_close`

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import RegisterClose
from collections import Counter

app = create_app()
with app.app_context():
    cierres_con_key = RegisterClose.query.filter(
        RegisterClose.idempotency_key_close.isnot(None)
    ).all()
    keys = [c.idempotency_key_close for c in cierres_con_key]
    duplicados = [k for k, count in Counter(keys).items() if count > 1]
    
    if duplicados:
        print(f'❌ ERROR: {len(duplicados)} idempotency_keys de cierre duplicados')
    else:
        print('✅ No hay idempotency_keys de cierre duplicados')
"
```

---

## TESTS P0-013, P0-014: AUDITORÍA EN BD

### Test 13.1: Verificar que eventos críticos se registran

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import SaleAuditLog

app = create_app()
with app.app_context():
    eventos_criticos = [
        'REGISTER_SESSION_OPENED',
        'BLIND_CLOSE_SUBMITTED',
        'CLOSE_WITH_DIFF',
        'SALE_BLOCKED_NO_SESSION',
        'SALE_CANCELLED'
    ]
    
    print('Eventos de auditoría registrados:')
    for evento in eventos_criticos:
        count = SaleAuditLog.query.filter_by(event_type=evento).count()
        print(f'  - {evento}: {count}')
    
    # Verificar que hay registros recientes
    recientes = SaleAuditLog.query.order_by(
        SaleAuditLog.created_at.desc()
    ).limit(10).all()
    
    print(f'\nÚltimos 10 eventos:')
    for e in recientes:
        print(f'  - {e.event_type} ({e.severity}) por {e.actor_name} a las {e.created_at}')
"
```

---

## TESTS P0-015: SOCKETIO SEGURO

### Test 15.1: Verificar que eventos NO exponen datos sensibles

**Pasos:**
1. Abrir DevTools → Console
2. Conectarse a SocketIO namespace `/pos`
3. Escuchar evento `pos_sale_created`
4. Crear una venta
5. Verificar payload del evento

**Resultado Esperado:**
- ✅ El evento público NO debe incluir `total_amount`, `payment_cash`, etc.
- ✅ Solo debe incluir: `register_id`, `event`, `sale_id`, `created_at`
- ✅ El evento admin (`/admin`) SÍ puede incluir datos completos

**Verificación manual:**
```javascript
// En consola del navegador
const socket = io('/pos');
socket.on('pos_sale_created', (data) => {
    console.log('Evento público:', data);
    // Verificar que NO tiene total_amount, payment_cash, etc.
});
```

---

## TESTS BUG PLANILLA

### Test Planilla 1: Agregar trabajador desde formulario

**Pasos:**
1. Ir a `/admin/jornada` (con jornada creada)
2. Seleccionar cargo y trabajador
3. Hacer clic en "➕ Agregar"
4. Verificar que aparece en la tabla inmediatamente
5. Recargar página y verificar que persiste

**Resultado Esperado:**
- ✅ Debe hacer POST a `/admin/jornada/planilla/agregar`
- ✅ Debe retornar `success: true`
- ✅ Debe refrescar la tabla desde BD
- ✅ Debe persistir en `PlanillaTrabajador`
- ✅ Debe calcular y congelar sueldo/bono automáticamente

**Comando de verificación:**
```bash
python3 -c "
from app import create_app
from app.models.jornada_models import PlanillaTrabajador

app = create_app()
with app.app_context():
    planilla = PlanillaTrabajador.query.order_by(
        PlanillaTrabajador.creado_en.desc()
    ).limit(5).all()
    
    print('Últimos 5 trabajadores en planilla:')
    for p in planilla:
        print(f'  - {p.nombre_empleado} ({p.rol}) - Jornada {p.jornada_id}')
        print(f'    Sueldo: {p.sueldo_snapshot}, Bono: {p.bono_snapshot}, Total: {p.pago_total}')
"
```

---

## TESTS INTEGRACIÓN COMPLETA

### Test Integración 1: Flujo completo de venta y cierre

**Pasos:**
1. Abrir jornada desde `/admin/jornada`
2. Abrir caja desde `/caja/register`
3. Crear 3 ventas (efectivo, débito, crédito)
4. Cerrar caja ingresando montos reales
5. Verificar que:
   - Las ventas tienen `jornada_id` válido
   - El cierre calcula correctamente (excluyendo cortesías/pruebas)
   - Se crea `RegisterClose` con `idempotency_key_close`
   - Se cierra `RegisterSession`
   - Se registran eventos de auditoría

**Comando de verificación completa:**
```bash
python3 -c "
from app import create_app
from app.models.pos_models import (
    RegisterSession, PosSale, RegisterClose, SaleAuditLog
)
from app.models.jornada_models import Jornada

app = create_app()
with app.app_context():
    print('=== VERIFICACIÓN INTEGRACIÓN ===\n')
    
    # 1. Jornadas abiertas
    jornadas_abiertas = Jornada.query.filter_by(estado_apertura='abierto').count()
    print(f'✅ Jornadas abiertas: {jornadas_abiertas}')
    
    # 2. Sesiones abiertas
    sesiones_abiertas = RegisterSession.query.filter_by(status='OPEN').count()
    print(f'✅ Sesiones de caja abiertas: {sesiones_abiertas}')
    
    # 3. Ventas con jornada_id
    ventas_con_jornada = PosSale.query.filter(
        PosSale.jornada_id.isnot(None)
    ).count()
    ventas_sin_jornada = PosSale.query.filter(
        PosSale.jornada_id.is_(None)
    ).count()
    print(f'✅ Ventas con jornada_id: {ventas_con_jornada}')
    print(f'⚠️  Ventas sin jornada_id: {ventas_sin_jornada} (solo históricas)')
    
    # 4. Cierres con idempotency
    cierres_con_key = RegisterClose.query.filter(
        RegisterClose.idempotency_key_close.isnot(None)
    ).count()
    print(f'✅ Cierres con idempotency_key: {cierres_con_key}')
    
    # 5. Eventos de auditoría
    eventos = SaleAuditLog.query.count()
    print(f'✅ Eventos de auditoría registrados: {eventos}')
    
    print('\n=== VERIFICACIÓN COMPLETA ===')
"
```

---

## RESULTADOS ESPERADOS

Todos los tests deben pasar. Si algún test falla:

1. **Revisar logs del servidor** para ver errores
2. **Verificar migración** se ejecutó correctamente
3. **Verificar que las tablas existen** con las columnas correctas
4. **Revisar código** según el test que falla

---

## NOTAS

- Los tests manuales requieren interacción del usuario
- Los tests automáticos se pueden ejecutar con los comandos Python proporcionados
- Algunos tests requieren datos de prueba (jornadas, ventas, etc.)
- Los tests de SocketIO requieren abrir DevTools en el navegador

---

**FIN DE TESTS_POS.md**











