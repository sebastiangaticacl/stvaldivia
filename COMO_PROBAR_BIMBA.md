# 🧪 Cómo Probar el Agente BIMBA

## 🎯 Opciones para Probar el Agente

### 1️⃣ **Panel de Administración Web** (Recomendado)

**URL:** `https://stvaldivia.cl/admin/bot/logs`

**Pasos:**
1. Inicia sesión como administrador
2. Navega a **Panel de Control** → **Logs del Agente BIMBA**
3. En la sección **"🧪 Consola de Prueba"**:
   - Escribe un mensaje en el campo de texto
   - Selecciona el canal (Interno, Web, Instagram, WhatsApp)
   - Haz clic en **"Probar Respuesta"**
4. La respuesta aparecerá en los logs debajo

**Ventajas:**
- ✅ Interfaz visual
- ✅ Ve los logs completos
- ✅ Prueba en tiempo real
- ✅ Registra todas las conversaciones

---

### 2️⃣ **Script de Prueba Local**

**Ejecutar:**
```bash
python3 test_bimba_agent.py
```

Este script prueba el agente con varias preguntas predefinidas sobre el sistema.

**Nota:** Si no tienes la API key de OpenAI configurada, algunas respuestas mostrarán `None` (el agente necesita OpenAI para generar respuestas creativas cuando no hay match en reglas).

---

### 3️⃣ **API Directa (cURL o Postman)**

**Endpoint:** `POST https://stvaldivia.cl/api/v1/bot/responder`

**Ejemplo con cURL:**
```bash
curl -X POST https://stvaldivia.cl/api/v1/bot/responder \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "¿Cómo funciona el sistema de pedidos?",
    "canal": "web"
  }'
```

**Ejemplo de respuesta:**
```json
{
  "status": "ok",
  "respuesta": "En BIMBA, cuando haces un pedido en el bar...",
  "source": "rule_based",
  "intent": "consultar_flujo",
  "modelo": null,
  "tokens": null
}
```

---

## 📋 Preguntas de Prueba Sugeridas

### **Sobre el Sistema:**
- "¿Cómo funciona el sistema de pedidos?"
- "Explícame el flujo de una venta"
- "¿Qué es una jornada?"
- "¿Cómo se entregan los productos?"
- "¿Qué es un ticket QR?"

### **Sobre Funcionalidades:**
- "¿Qué información puedo ver en el dashboard?"
- "¿Cómo funciona el inventario?"
- "¿Qué es una barra en el sistema?"
- "Explícame cómo funciona el POS"

### **Sobre Eventos (si hay evento cargado):**
- "¿Qué hay hoy en BIMBA?"
- "¿A qué hora es el evento?"
- "¿Cuánto cuesta la entrada?"

### **Sobre Operaciones (debe responder vagamente):**
- "¿Cómo está la noche?"
- "¿Hay mucha gente?"
- "¿Está movido?"

---

## ✅ Qué Verificar

1. **El agente entiende el sistema:**
   - ✅ Puede explicar procesos (ventas, entregas, jornadas)
   - ✅ Usa términos correctos (ticket, barra, jornada, etc.)
   - ✅ Describe flujos de forma clara

2. **Respeta la privacidad:**
   - ❌ NO comparte números específicos de ventas
   - ❌ NO comparte métricas internas
   - ✅ Puede usar contexto operativo de forma vaga ("está movido", "buen ambiente")

3. **Mantiene el tono:**
   - ✅ Tono cálido y queer-friendly
   - ✅ Usa emojis apropiadamente
   - ✅ Responde en español chileno
   - ✅ Mantiene la identidad de BIMBA

4. **Es útil:**
   - ✅ Responde de forma relevante
   - ✅ Ofrece información útil sin ser técnico
   - ✅ Guía a usuarios cuando no sabe algo

---

## 🔍 Verificar el Conocimiento del Sistema

Para verificar que el conocimiento del sistema está incluido, puedes hacer:

```bash
python3 -c "
from app.prompts.prompts_bimba import get_prompt_maestro_bimba
prompt = get_prompt_maestro_bimba('null', 'None')
print('POS:', 'SISTEMA DE VENTAS (POS)' in prompt)
print('Inventario:', 'INVENTARIO Y RECETAS' in prompt)
print('Entregas:', 'SISTEMA DE ENTREGAS' in prompt)
print('Longitud:', len(prompt), 'caracteres')
"
```

Si todo está correcto, deberías ver:
```
POS: True
Inventario: True
Entregas: True
Longitud: ~14400 caracteres
```

---

## 🚀 Próximos Pasos

1. **Probar con preguntas reales** de clientes
2. **Ajustar el conocimiento** según feedback
3. **Agregar más ejemplos** si es necesario
4. **Monitorear logs** para ver cómo responde en producción

---

## 📞 Soporte

Si encuentras problemas:
- Revisa los logs en `/admin/bot/logs`
- Verifica que la API key de OpenAI esté configurada
- Revisa que el prompt se esté cargando correctamente









