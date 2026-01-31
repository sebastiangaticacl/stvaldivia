# 📊 EVALUACIÓN: Integración SumUp para TPV Kiosko

**Fecha:** 2025-01-15  
**Objetivo:** Evaluar viabilidad de implementar SumUp para pagos sin contacto (Apple Pay/Google Pay) en TPV Kiosko, donde los clientes paguen desde su móvil sin ir a caja, y reciban un QR al finalizar.

---

## 🎯 FLUJO DESEADO vs ACTUAL

### Flujo Actual (Manual)
```
1. Cliente selecciona productos en kiosko
2. Ve resumen en checkout
3. Va físicamente a la caja
4. Paga en efectivo/tarjeta en caja
5. Cajero marca pago como completado
6. Cliente recibe QR/ticket para recoger producto
```

### Flujo Deseado (SumUp)
```
1. Cliente selecciona productos en kiosko
2. Ve resumen en checkout
3. Sistema genera checkout SumUp y muestra QR
4. Cliente escanea QR con su móvil
5. Paga con Apple Pay/Google Pay desde su móvil
6. Sistema detecta pago completado
7. Cliente recibe QR/ticket para recoger en caja
```

---

## ✅ CAPACIDADES DE SUMUP API

### 1. Creación de Checkouts
- ✅ **Soporte confirmado:** API permite crear checkouts con `POST /v0.1/checkouts`
- ✅ **Campos relevantes:**
  - `amount`: Monto del pago
  - `currency`: Moneda (CLP soportado)
  - `checkout_reference`: ID único del checkout
  - `return_url`: URL de callback cuando se complete el pago
  - `description`: Descripción del pago

### 2. Métodos de Pago Sin Contacto
- ✅ **Apple Pay:** SumUp soporta Apple Pay a través de su API
- ✅ **Google Pay:** SumUp soporta Google Pay a través de su API
- ⚠️ **QR Codes:** SumUp tiene funcionalidad de QR codes, pero principalmente orientada a códigos estáticos del comerciante
- ⚠️ **Checkout dinámico:** Los checkouts de SumUp típicamente redirigen a una página de pago, no generan QR directamente

### 3. Verificación de Estado
- ✅ **Estados de checkout:** `PENDING`, `FAILED`, `PAID`, `EXPIRED`
- ✅ **API para consultar:** `GET /v0.1/checkouts/{checkout_id}`
- ✅ **Webhooks:** SumUp soporta webhooks para notificaciones de pago

### 4. Procesamiento de Pagos
- ✅ **API para procesar:** `POST /v0.1/checkouts/{checkout_id}/process`
- ⚠️ **Flujo típico:** Checkout → Redirección a página SumUp → Cliente paga → Webhook/Callback → Verificar estado

---

## 🔍 ANÁLISIS DE VIABILIDAD

### ✅ ASPECTOS VIABLES

#### 1. **Infraestructura Existente Compatible**
- El modelo `Pago` ya tiene campos para almacenar `transaction_id` (SumUp checkout ID)
- El sistema ya genera QR codes (aunque actualmente para tickets post-pago)
- Existe flujo de verificación de estado de pago (`api_pago_status`)
- El sistema ya integra con APIs externas (PHP POS, GETNET)

#### 2. **Integración Técnica Posible**
- SumUp API es RESTful y compatible con el stack actual (Python/Flask)
- Autenticación mediante API keys (similar a otras APIs integradas)
- Soporte para webhooks (se pueden implementar endpoints de callback)

#### 3. **Flujo Alternativo Factible**
Aunque SumUp no genera QR directos para checkouts dinámicos, hay alternativas:

**Opción A: Checkout con Redirección**
```
1. Cliente en checkout → Clic "Pagar con SumUp"
2. Sistema crea checkout SumUp → Obtiene URL de pago
3. Redirección a URL SumUp (abre en nueva ventana/iframe)
4. Cliente completa pago con Apple Pay/Google Pay
5. SumUp redirige a return_url con estado
6. Sistema verifica estado y genera ticket QR
```

**Opción B: Checkout + QR Personalizado**
```
1. Cliente en checkout → Sistema crea checkout SumUp
2. Sistema genera QR con URL del checkout SumUp
3. Cliente escanea QR → Abre checkout en móvil
4. Cliente paga con Apple Pay/Google Pay en móvil
5. Webhook de SumUp notifica pago completado
6. Sistema actualiza estado y genera ticket QR para recoger
```

### ⚠️ LIMITACIONES Y CONSIDERACIONES

#### 1. **SumUp QR Codes vs Checkouts Dinámicos**
- SumUp tiene códigos QR estáticos del comerciante (para recibir pagos)
- Los checkouts dinámicos generan URLs de pago, no QR codes directamente
- **Solución:** Generar QR propio que contenga la URL del checkout SumUp

#### 2. **Flujo de Usuario**
El flujo deseado requiere:
- Cliente debe tener dispositivo móvil con Apple Pay/Google Pay configurado
- Cliente debe escanear QR (requiere app de cámara)
- Cliente completa pago en móvil, pero está en kiosko
- **Consideración:** Experiencia UX puede ser compleja (pasar de pantalla táctil a móvil)

#### 3. **Integración con PHP POS**
- Actualmente los pagos se registran en PHP POS después de crear el `Pago`
- Con SumUp, el pago se procesa externamente primero
- **Necesario:** Modificar flujo para crear venta en PHP POS solo después de confirmar pago SumUp

#### 4. **Verificación de Estado**
- SumUp soporta webhooks pero también requiere polling como backup
- El sistema actual tiene polling básico que se puede mejorar
- **Necesario:** Implementar webhook endpoint + polling como fallback

#### 5. **Moneda y Región**
- ✅ SumUp soporta CLP (Chile)
- ⚠️ Verificar que SumUp esté disponible/comercialmente activo en Chile
- ⚠️ Verificar comisiones y tarifas para mercado chileno

---

## 🏗️ ARQUITECTURA PROPUESTA

### Componentes Necesarios

```
┌─────────────────────────────────────────────┐
│         Kiosko Frontend (Tótem)            │
│  - Selección productos                      │
│  - Checkout con botón "Pagar con SumUp"    │
│  - Pantalla QR para escanear               │
│  - Pantalla espera de pago                 │
│  - Pantalla éxito con ticket QR            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│      Flask Backend (Nuevo Módulo)          │
│  ┌──────────────────────────────────────┐  │
│  │  SumUp Client Service                │  │
│  │  - create_checkout()                 │  │
│  │  - get_checkout_status()             │  │
│  │  - process_checkout()                │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │  Kiosk Payment Service               │  │
│  │  - create_pago_with_sumup()          │  │
│  │  - generate_checkout_qr()            │  │
│  │  - handle_sumup_webhook()            │  │
│  │  - sync_to_php_pos()                 │  │
│  └──────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│  SumUp API   │      │  PHP POS API │
│  - Checkouts │      │  - Sales     │
│  - Webhooks  │      │              │
└──────────────┘      └──────────────┘
```

### Modelo de Datos - Actualizaciones Necesarias

**Tabla `pagos`:**
- ✅ `transaction_id` - Ya existe, almacenar SumUp checkout ID
- ⚠️ Agregar: `sumup_checkout_id` (más específico)
- ⚠️ Agregar: `sumup_checkout_url` (URL para generar QR)
- ⚠️ Agregar: `payment_method` más específico ('SUMUP_APPLE_PAY', 'SUMUP_GOOGLE_PAY')
- ✅ Estados actuales son compatibles (PENDING → PAID/FAILED)

---

## 📋 PASOS DE IMPLEMENTACIÓN (Si se aprueba)

### Fase 1: Infraestructura Base
1. Crear `SumUpClient` service (similar a `PHPPosKioskClient`)
2. Configurar API keys de SumUp (sandbox y producción)
3. Crear endpoint para crear checkouts SumUp
4. Actualizar modelo `Pago` con campos SumUp

### Fase 2: Flujo de Pago
1. Modificar `kiosk_checkout.html` para agregar botón "Pagar con SumUp"
2. Crear endpoint que genera checkout y retorna URL/QR
3. Crear pantalla para mostrar QR del checkout
4. Implementar polling/verificación de estado del checkout

### Fase 3: Webhooks y Sincronización
1. Crear endpoint webhook para recibir notificaciones de SumUp
2. Implementar sincronización con PHP POS después de pago confirmado
3. Generar ticket QR después de confirmar pago

### Fase 4: Testing y Refinamiento
1. Probar flujo completo en sandbox de SumUp
2. Probar con diferentes métodos de pago (Apple Pay, Google Pay, tarjeta)
3. Probar manejo de errores y timeouts
4. Optimizar UX del flujo

---

## ⚠️ PUNTOS CRÍTICOS A VERIFICAR

### 1. **Disponibilidad Comercial en Chile**
- ⚠️ **CRÍTICO:** Verificar que SumUp esté disponible y operativo en Chile
- ⚠️ Verificar requisitos legales y regulatorios
- ⚠️ Verificar tasas y comisiones para mercado chileno

### 2. **Experiencia de Usuario**
- El flujo requiere que cliente tenga móvil con Apple Pay/Google Pay
- Cliente debe cambiar de pantalla táctil del kiosko a su móvil
- **Pregunta:** ¿Es más conveniente que pagar directamente en caja?

### 3. **Costo vs Beneficio**
- Comisiones de SumUp (verificar tasas)
- Tiempo de desarrollo vs beneficio operativo
- Mantenimiento de integración adicional

### 4. **Alternativas**
- **GETNET:** Ya integrado, pero requiere terminal físico
- **KLAP:** Ya considerado como backup, tap-on-phone
- **SumUp:** Nuevo provider, requiere evaluación comercial

---

## 💡 RECOMENDACIÓN

### ✅ VIABILIDAD TÉCNICA: **ALTA**
- La API de SumUp es compatible técnicamente
- El sistema actual tiene infraestructura base compatible
- La implementación es factible con esfuerzo moderado

### ⚠️ VIABILIDAD COMERCIAL: **PENDIENTE DE VERIFICACIÓN**
- **CRÍTICO:** Verificar disponibilidad de SumUp en Chile
- Verificar tasas y comisiones
- Comparar con alternativas existentes (GETNET, KLAP)

### 📝 PRÓXIMOS PASOS RECOMENDADOS

1. **Verificación Comercial (ANTES de implementar):**
   - Contactar a SumUp para verificar disponibilidad en Chile
   - Solicitar información de tasas y comisiones
   - Verificar requisitos de cuenta comercial
   - Comparar con GETNET/KLAP existentes

2. **Prueba de Concepto (Si comercialmente viable):**
   - Implementar SumUpClient básico
   - Crear un checkout de prueba
   - Probar flujo completo en sandbox
   - Evaluar UX del flujo

3. **Decisión Final:**
   - Evaluar costo-beneficio vs alternativas
   - Decidir si SumUp agrega valor único vs GETNET/KLAP
   - Considerar si el flujo QR mejora realmente la experiencia vs pago directo

---

## 🔄 COMPARACIÓN CON ALTERNATIVAS

### SumUp vs GETNET
| Aspecto | SumUp | GETNET |
|---------|-------|--------|
| Hardware | No requiere (pago móvil) | Requiere terminal |
| Integración | API REST | API REST + Terminal físico |
| Métodos de pago | Apple Pay, Google Pay, Tarjeta | Tarjeta (contacto/sin contacto) |
| Flujo cliente | Escanear QR → Pagar en móvil | Pasar tarjeta en terminal |
| Ya integrado | ❌ No | ✅ Sí (POS) |

### SumUp vs KLAP
| Aspecto | SumUp | KLAP |
|---------|-------|------|
| Hardware | No requiere | Usa móvil del comerciante |
| Métodos de pago | Apple Pay, Google Pay | NFC (tap on phone) |
| Flujo cliente | Escanear QR → Pagar en móvil | Pasar tarjeta sobre móvil |
| Ya considerado | ❌ No | ✅ Sí (backup) |

---

## ✅ CONCLUSIÓN

**Viabilidad Técnica:** ✅ **SÍ, es técnicamente viable**  
**Viabilidad Comercial:** ⚠️ **Pendiente de verificación**  
**Recomendación:** ⚠️ **Verificar disponibilidad comercial en Chile ANTES de implementar**

El sistema puede soportar la integración de SumUp, pero se recomienda:
1. Verificar disponibilidad comercial primero
2. Comparar con alternativas existentes (GETNET/KLAP)
3. Evaluar si el flujo QR realmente mejora la experiencia vs pago directo
4. Considerar costo-beneficio de agregar un tercer procesador

Si SumUp está disponible comercialmente en Chile y ofrece ventajas claras, la implementación es factible con esfuerzo moderado (2-3 semanas de desarrollo).

