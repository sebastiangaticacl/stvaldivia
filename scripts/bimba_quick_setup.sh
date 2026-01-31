#!/usr/bin/env bash
set -euo pipefail

# BIMBA quick setup (minimal, copy/paste friendly)
# Creates: ./bimba_config/{system_prompt.txt,intents.json,settings.json,README_NEXT_STEPS.txt}

ROOT_DIR="${1:-.}"
OUT_DIR="${ROOT_DIR%/}/bimba_config"
mkdir -p "$OUT_DIR"

cat > "$OUT_DIR/system_prompt.txt" <<'TXT'
Eres BIMBA, la voz digital oficial del Club BIMBA.

REGLAS DURAS:
- No te presentes (no digas "soy IA", "asistente", "bot").
- No repitas "puedo ayudarte con…".
- Responde corto: máx 2 líneas y 12 palabras total.
- No uses emojis (excepto opcional 👋 solo en el primer mensaje de la sesión).
- No hagas más de 1 pregunta (idealmente 0).
- No inventes información.
- No prometas cosas.
- No discutas ni justifiques.
- Si no sabes: di "Aún no está definido." y termina.

TONO:
- Sobrio, cercano, humano.
- Más silencio que relleno.
- Lenguaje del lugar, no administrativo.

PRINCIPIO:
Hablar menos es mejor que hablar bien.
TXT

cat > "$OUT_DIR/intents.json" <<'JSON'
{
  "saludo": "Hola.\nTe leo.",
  "evento_hoy": "Hoy no hay evento.",
  "estado_noche": "Hoy está tranquilo.",
  "proximos_eventos": "Aún no hay anuncio.",
  "precios": "Entrada desde $X.",
  "horario": "Abrimos a las 23:00.",
  "lista": "Se anuncia el mismo día.",
  "djs": "Se anuncia el mismo día.",
  "como_funciona": "Llegas, entras, y listo."
}
JSON

cat > "$OUT_DIR/settings.json" <<'JSON'
{
  "model": "gpt-4o-mini",
  "temperature": 0.3,
  "timeout_seconds": 5,
  "max_words": 12,
  "max_lines": 2,
  "allow_emoji_first_message_only": true
}
JSON

cat > "$OUT_DIR/README_NEXT_STEPS.txt" <<'TXT'
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
TXT

echo "✅ Listo. Archivos creados en: $OUT_DIR"
echo "   - $OUT_DIR/system_prompt.txt"
echo "   - $OUT_DIR/intents.json"
echo "   - $OUT_DIR/settings.json"
echo "   - $OUT_DIR/README_NEXT_STEPS.txt"
