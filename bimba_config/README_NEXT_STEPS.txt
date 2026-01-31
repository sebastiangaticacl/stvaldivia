BIMBA CONFIG GENERATED ✅

FILES:
- system_prompt.txt  -> pega esto como System Prompt del agente OpenAI
- intents.json       -> pega estas respuestas en tu capa de reglas por intención
- settings.json      -> usa estos settings (especialmente temperature 0.3)

MINIMUM INTEGRATION (1 sola regla extra):
- Si la intención detectada es "saludo" y NO es primer mensaje de sesión:
  NO vuelvas a enviar el saludo completo.
  Devuelve "Te leo." o no respondas.

NOTAS:
- Reemplaza $X y el horario con datos reales.
- Evita que el bot diga "Soy BIMBA…" después del primer mensaje.
