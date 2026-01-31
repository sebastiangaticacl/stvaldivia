# ✅ Comando curl Correcto para OpenAI

## ⚠️ Corrección del Comando Original

El comando que compartiste tenía algunos errores. Aquí está la versión correcta:

### ❌ Comando Original (Incorrecto):
```bash
curl https://api.openai.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-..." \
  -d '{
    "model": "gpt-5-nano",
    "input": "write a haiku about ai",
    "store": true
  }'
```

**Problemas:**
1. ❌ Endpoint incorrecto: `/v1/responses` no existe
2. ❌ Modelo inexistente: `gpt-5-nano` no existe
3. ❌ Formato incorrecto: debería usar `messages` en lugar de `input`

### ✅ Comando Correcto:

#### Opción 1: Chat Completions (Recomendado)
```bash
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "Escribe un haiku sobre IA"}
    ],
    "max_tokens": 100
  }'
```

#### Opción 2: Listar Modelos Disponibles
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer ${OPENAI_API_KEY}"
```

## 📋 Modelos Disponibles

Los modelos actuales de OpenAI incluyen:

- ✅ `gpt-4o` - Más potente y reciente
- ✅ `gpt-4o-mini` - Más económico, recomendado para chatbots (el que usa BIMBA)
- ✅ `gpt-4` - Versión anterior de GPT-4
- ✅ `gpt-3.5-turbo` - Más económico, buena opción
- ❌ `gpt-5-nano` - No existe

## 🎯 Ejemplo de Respuesta Exitosa

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1766214610,
  "model": "gpt-4o-mini-2024-07-18",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "¡Hola!"
    }
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

## 🔧 Formato Correcto para Chat Completions

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "Eres un asistente útil."},
    {"role": "user", "content": "Hola, ¿cómo estás?"}
  ],
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Campos importantes:**
- `model`: Nombre del modelo a usar
- `messages`: Array de mensajes con `role` (system/user/assistant) y `content`
- `temperature`: 0.0-2.0 (0.7 es un buen balance)
- `max_tokens`: Límite de tokens en la respuesta

## ✅ Verificación

Para verificar que tu API key funciona:

```bash
# Debería devolver una lista de modelos
curl -s https://api.openai.com/v1/models \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" | grep -o '"id": "[^"]*"' | head -5
```

## 📚 Documentación Oficial

- API Reference: https://platform.openai.com/docs/api-reference
- Chat Completions: https://platform.openai.com/docs/api-reference/chat
- Models: https://platform.openai.com/docs/models

