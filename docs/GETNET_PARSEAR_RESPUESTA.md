# 🔧 Cómo Parsear la Respuesta de Getnet

**Fecha:** 2025-12-18

---

## 📋 PROBLEMA IDENTIFICADO

El SDK Getnet está devolviendo la respuesta en formato JSON (como muestra el log del usuario), pero el código del agente Java intentaba usar reflexión para llamar métodos como `isApproved()`, `getAuthCode()`, etc., que no existen.

---

## ✅ SOLUCIÓN IMPLEMENTADA

Se actualizó la función `ejecutarPago()` para:

1. **Detectar si la respuesta es String (JSON) o objeto Java**
2. **Si es JSON**, parsearlo directamente usando `JSONObject`
3. **Buscar el campo `JsonSerialized`** (como aparece en el log)
4. **Extraer campos relevantes**:
   - `ResponseCode`: 0 = aprobado
   - `ResponseMessage`: "Aprobado" = aprobado
   - `AuthorizationCode`: código de autorización
   - `OperationId` y `TerminalId`: para referencia

---

## 📝 FORMATO DE RESPUESTA DEL SDK

Según el log del usuario, el SDK devuelve:

```json
{
  "JsonSerialized": {
    "ResponseCode": 0,
    "ResponseMessage": "Aprobado",
    "AuthorizationCode": "532976",
    "CardType": "DB",
    "CardBrand": "VI",
    "Amount": 100,
    "OperationId": 0,
    "TerminalId": "20129179",
    ...
  },
  "Sign": "..."
}
```

---

## 🔄 CÓDIGO ACTUALIZADO

El código ahora:

1. Verifica si `saleResult instanceof String`
2. Si es String, lo parsea como JSON
3. Busca `JsonSerialized` dentro del JSON
4. Verifica `ResponseCode == 0` y `ResponseMessage == "Aprobado"`
5. Extrae `AuthorizationCode` y otros campos relevantes

---

## 🚀 PRÓXIMOS PASOS

**IMPORTANTE:** El agente Java necesita recompilarse para aplicar estos cambios:

```bash
cd ~/getnet_agent/java
./build.sh
# Reiniciar el agente
```

---

## 🧪 VERIFICACIÓN

Después de recompilar, cuando el agente procese un pago, debería:

1. ✅ Detectar correctamente que la respuesta es JSON
2. ✅ Parsear `JsonSerialized`
3. ✅ Identificar que `ResponseCode=0` significa aprobado
4. ✅ Extraer `AuthorizationCode` correctamente
5. ✅ Reportar `status: "APPROVED"` al backend
6. ✅ El backend actualizar el PaymentIntent a `APPROVED`
7. ✅ El frontend detectar el cambio y crear la venta

---

## 📊 FLUJO COMPLETO

1. Frontend crea PaymentIntent con `status: READY`
2. Agente Java consulta `/caja/api/payment/agent/pending`
3. Agente procesa pago con SDK Getnet
4. SDK devuelve JSON con `ResponseCode=0`
5. Agente parsea JSON y extrae datos
6. Agente reporta `status: APPROVED` a `/caja/api/payment/agent/result`
7. Backend actualiza PaymentIntent a `APPROVED`
8. Frontend detecta cambio y crea la venta

---

## ⚠️ NOTA

Si el SDK devuelve la respuesta como objeto Java (no JSON string), el código tiene fallback para usar reflexión, pero basado en el log del usuario, parece que devuelve JSON string.













