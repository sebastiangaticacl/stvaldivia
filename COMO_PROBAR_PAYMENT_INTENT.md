# 🧪 CÓMO PROBAR PaymentIntent API

## Resumen

Se creó/modificó la ruta `POST /caja/api/payment/intents` que:
- Crea un PaymentIntent con status `READY`
- Valida que `register_id` existe en PosRegister
- Valida que `amount_total > 0`
- Retorna `{success: true, intent_id: <uuid>}`
- Escribe log: `[PAYMENT_INTENT] READY→ id=<uuid> register=<id> amount=<total>`

---

## Opción 1: Prueba desde el Frontend (MÁS FÁCIL) ✅

### Pasos:

1. **Inicia el servidor local** (si no está corriendo):
   ```bash
   python run_local.py
   # o
   flask run
   ```

2. **Abre el navegador y haz login en el POS**:
   - Ve a `http://127.0.0.1:5001/caja/login`
   - Haz login con tus credenciales
   - Selecciona la caja **TEST001** (register_id = "1")

3. **Abre la consola del navegador** (F12 → Console)

4. **Agrega productos al carrito** desde la UI

5. **Ejecuta este código en la consola**:
   ```javascript
   // Probar crear PaymentIntent para TEST001
   fetch('/caja/api/payment/intents', {
     method: 'POST',
     headers: {
       'Content-Type': 'application/json'
     },
     body: JSON.stringify({
       register_id: "1",
       provider: "GETNET",
       amount_total: 1500.0
     })
   })
   .then(r => r.json())
   .then(data => {
     console.log('✅ Respuesta:', data);
     if (data.success) {
       console.log('✅ PaymentIntent creado con ID:', data.intent_id);
       console.log('📋 Verifica logs del servidor para: [PAYMENT_INTENT] READY→');
     }
   })
   .catch(err => console.error('❌ Error:', err));
   ```

6. **Verifica los logs del servidor**:
   - Deberías ver: `[PAYMENT_INTENT] READY→ id=<uuid> register=1 amount=1500.0`

---

## Opción 2: Prueba con curl (requiere cookie de sesión)

### Paso 1: Obtener cookie de sesión

1. Abre el navegador y haz login en `/caja/login`
2. Abre DevTools (F12) → Application → Cookies
3. Copia el valor de la cookie `session`

### Paso 2: Ejecutar curl

```bash
curl -X POST "http://127.0.0.1:5001/caja/api/payment/intents" \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<TU_COOKIE_AQUI>" \
  -d '{
    "register_id": "1",
    "provider": "GETNET",
    "amount_total": 1500.0
  }' | jq '.'
```

**Respuesta esperada:**
```json
{
  "success": true,
  "intent_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

## Opción 3: Prueba con script Python

```bash
# Prueba básica (sin auth - verás error 401)
python test_payment_intent_api.py

# Prueba con cookie de sesión
python test_payment_intent_api.py --session "<cookie_value>"

# Prueba en producción
python test_payment_intent_api.py --url https://stvaldivia.cl --session "<cookie_value>"
```

---

## Opción 4: Prueba con script bash

```bash
# Prueba básica (muestra instrucciones)
./test_payment_intent_curl.sh

# Con URL personalizada
./test_payment_intent_curl.sh https://stvaldivia.cl
```

---

## ✅ Casos de Prueba

### Test 1: Crear PaymentIntent válido
```json
POST /caja/api/payment/intents
{
  "register_id": "1",
  "provider": "GETNET",
  "amount_total": 1500.0
}
```
**Esperado:** `201 Created` + `{success: true, intent_id: <uuid>}`

### Test 2: register_id no existe
```json
{
  "register_id": "999",
  "provider": "GETNET",
  "amount_total": 1500.0
}
```
**Esperado:** `400 Bad Request` + `{success: false, error: "register_id 999 no existe"}`

### Test 3: amount_total <= 0
```json
{
  "register_id": "1",
  "provider": "GETNET",
  "amount_total": 0
}
```
**Esperado:** `400 Bad Request` + `{success: false, error: "amount_total debe ser mayor a 0"}`

### Test 4: Sin autenticación
```json
# Request sin cookie de sesión
```
**Esperado:** `401 Unauthorized` + `{success: false, error: "No autenticado"}`

---

## 🔍 Verificar Logs

Después de crear un PaymentIntent exitosamente, deberías ver en los logs:

```
[PAYMENT_INTENT] READY→ id=a1b2c3d4-e5f6-7890-abcd-ef1234567890 register=1 amount=1500.0
```

**Ubicación de logs:**
- **Local:** Terminal donde corre `run_local.py` o `flask run`
- **Producción:** `journalctl -u stvaldivia.service -f` o logs de Cloud Run

---

## 🔄 Flujo Completo (Prueba End-to-End)

Para probar el flujo completo con el agente Getnet:

1. **Crear PaymentIntent** (desde frontend o API)
2. **Verificar que el agente lo detecta** (GET /caja/api/payment/agent/pending)
3. **El agente procesa el pago** (simulado o real)
4. **El agente reporta resultado** (POST /caja/api/payment/agent/result)
5. **Verificar log CONFIRMED**:
   ```
   [PAYMENT_INTENT] CONFIRMED→ id=<uuid> auth_code=<auth_code>
   ```

---

## 📝 Notas

- La ruta requiere autenticación POS activa (`pos_logged_in` en sesión)
- `register_id` debe existir en la tabla `pos_registers`
- `amount_total` debe ser un número positivo
- El log se escribe usando `current_app.logger.info()`
- El PaymentIntent se crea con `status='READY'` para que el agente lo detecte

---

## 🐛 Troubleshooting

### Error: "No autenticado"
- **Causa:** No hay sesión POS activa
- **Solución:** Haz login en `/caja/login` primero

### Error: "register_id X no existe"
- **Causa:** El register_id no existe en `pos_registers`
- **Solución:** Verifica que la caja existe o usa `register_id="1"` (TEST001)

### Error: "amount_total debe ser mayor a 0"
- **Causa:** El monto es 0 o negativo
- **Solución:** Usa un `amount_total > 0`

### No veo el log `[PAYMENT_INTENT] READY→`
- **Causa:** El log se escribe en `current_app.logger`
- **Solución:** Verifica que los logs estén configurados correctamente














