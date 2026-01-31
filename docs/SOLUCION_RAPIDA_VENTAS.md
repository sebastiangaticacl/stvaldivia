# 🚀 Solución Rápida para Habilitar Ventas

**Fecha:** 2025-12-18

---

## ✅ CAMBIOS APLICADOS

1. **Backend mejorado:**
   - El endpoint `/api/payment/intents/<id>/status` ahora devuelve `status` directamente Y también en formato `intent.status` para compatibilidad
   - Logging mejorado para rastrear el flujo completo
   - Cuando el agente reporta `APPROVED`, se loguea claramente

2. **Frontend ya está correcto:**
   - Busca `CONFIRMED` o `APPROVED` en `statusData.status` o `statusData.intent?.status`
   - Cuando detecta `APPROVED`, crea la venta automáticamente

---

## 🔧 ACCIÓN REQUERIDA: Recompilar Agente Java

El agente Java necesita recompilarse para parsear correctamente la respuesta JSON del SDK Getnet:

```bash
# En la máquina Windows (CAJA TEST)
cd ~/getnet_agent/java
./build.sh
# Reiniciar el agente
```

---

## 📊 FLUJO COMPLETO (Cómo Debe Funcionar)

1. **Usuario inicia pago** en la UI (CAJA TEST, método != cash)
2. **Frontend crea PaymentIntent** con `status: READY`
3. **Agente Java consulta** `/caja/api/payment/agent/pending?register_id=1`
4. **Agente procesa pago** con SDK Getnet
5. **SDK devuelve JSON** con `ResponseCode=0, ResponseMessage="Aprobado"`
6. **Agente parsea JSON** y extrae `AuthorizationCode`
7. **Agente reporta** `status: "APPROVED"` a `/caja/api/payment/agent/result`
8. **Backend actualiza** PaymentIntent a `APPROVED`
9. **Frontend detecta** `APPROVED` en polling
10. **Frontend crea venta** con `payment_intent_id`

---

## 🐛 DEBUGGING

Si las ventas no funcionan, revisa:

### 1. Logs del Backend (VM Linux)
```bash
tail -f /var/www/stvaldivia/logs/error.log | grep PAYMENT_INTENT
```

Deberías ver:
- `[PAYMENT_INTENT] READY→ id=... register=1 amount=...`
- `[PAYMENT_INTENT] APPROVED→ id=... auth_code=...`

### 2. Logs del Agente Java (Windows)
Revisa la consola donde corre el agente. Deberías ver:
- `💳 Procesando pago Getnet...`
- `📄 Respuesta JSON del SDK: ...`
- `✅ Pago aprobado (ResponseCode=0)`
- `✅ Resultado reportado: intent=... status=APPROVED`

### 3. Frontend (Browser Console)
Abre DevTools (F12) y revisa la consola. Deberías ver:
- `🔄 Flujo GETNET Agent: Creando PaymentIntent...`
- `📊 PaymentIntent ... status: READY`
- `📊 PaymentIntent ... status: APPROVED`
- `✅ PaymentIntent confirmado, creando venta...`

---

## ⚠️ PROBLEMAS COMUNES

### Problema: "El agente no detecta el PaymentIntent"
**Solución:** Verifica que:
- El agente esté corriendo
- El `register_id` coincida (debe ser "1" o "TEST001")
- El `AGENT_API_KEY` sea el mismo en servidor y agente

### Problema: "El agente procesa pero no reporta APPROVED"
**Solución:** 
- Recompila el agente con `./build.sh`
- Verifica que el SDK devuelva JSON (no objeto Java)
- Revisa los logs del agente para ver qué está recibiendo

### Problema: "El frontend no detecta APPROVED"
**Solución:**
- Abre DevTools y revisa la consola
- Verifica que el polling esté funcionando
- Revisa la respuesta del endpoint `/caja/api/payment/intents/<id>`

---

## ✅ CHECKLIST FINAL

- [ ] Agente Java recompilado con código actualizado
- [ ] Agente corriendo y enviando heartbeat
- [ ] Backend recibiendo heartbeat (verificar en admin panel)
- [ ] Crear PaymentIntent desde UI funciona
- [ ] Agente detecta PaymentIntent pendiente
- [ ] Agente procesa pago con Getnet
- [ ] Agente reporta APPROVED al backend
- [ ] Frontend detecta APPROVED
- [ ] Frontend crea venta automáticamente
- [ ] Ticket se muestra correctamente

---

## 🎯 PRÓXIMO PASO INMEDIATO

**Recompilar el agente Java** con el código actualizado que parsea correctamente la respuesta JSON del SDK Getnet.













