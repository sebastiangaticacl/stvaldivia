# 🔑 Guía: Obtener API Key de SumUp

**Referencia:** [SumUp Authentication Documentation](https://developer.sumup.com/api/authentication)

---

## 📋 Pasos para Obtener API Key

### 1. Acceder al Dashboard de SumUp

1. Ve a: **https://me.sumup.com/developers/api-keys**
2. O accede al dashboard y navega a: **Developers → API Keys**

### 2. Crear API Key

1. **Para Sandbox/Testing:**
   - Las API keys de test mode tienen prefijo `sk_test_`
   - Crear cuenta de sandbox si no tienes una
   - Las transacciones en sandbox no son reales

2. **Para Producción:**
   - Las API keys de live mode tienen prefijo `sk_live_`
   - Requiere cuenta de comerciante activa
   - Las transacciones son reales

3. **Restricted API Keys (Opcional):**
   - Permisos granulares para mayor seguridad
   - Útil para limitar acceso a funciones específicas

### 3. Configurar en el Sistema

Una vez obtenida la API key, configurarla como variable de entorno:

```bash
# Para sandbox/testing
export SUMUP_API_KEY="sk_test_xxxxx"

# Para producción
export SUMUP_API_KEY="sk_live_xxxxx"
```

O agregar al archivo `.env`:

```bash
SUMUP_API_KEY=sk_test_xxxxx  # O sk_live_xxxxx para producción
```

---

## 🔐 Seguridad de API Keys

**Importante según la documentación oficial:**

- ✅ **Mantener secretas:** No compartir API keys
- ✅ **No exponer en código cliente:** No usar en JavaScript del navegador
- ✅ **No subir a GitHub:** Usar variables de entorno o secretos
- ✅ **HTTPS obligatorio:** Todos los requests deben ser HTTPS
- ✅ **Rotar periódicamente:** Cambiar API keys regularmente

---

## 🧪 Probar API Key

### Verificar que la API Key funciona:

```bash
# Probar con curl
curl https://api.sumup.com/v0.1/me \
  -H "Authorization: Bearer sk_test_xxxxx"
```

Si funciona, deberías recibir información del perfil del comerciante.

---

## 📚 Recursos Adicionales

- **Documentación de Autenticación:** https://developer.sumup.com/api/authentication
- **Dashboard de API Keys:** https://me.sumup.com/developers/api-keys
- **Documentación General:** https://developer.sumup.com/api
- **Soporte:** Contactar a SumUp si tienes problemas

---

## ⚠️ Troubleshooting

### Error: "Invalid API key"
- Verificar que la key esté copiada correctamente (sin espacios)
- Verificar que uses `sk_test_` para sandbox o `sk_live_` para producción
- Verificar que la key no haya expirado o sido revocada

### Error: "Unauthorized"
- Verificar formato: `Authorization: Bearer {api_key}`
- Verificar que uses HTTPS (no HTTP)
- Verificar que la key tenga los permisos necesarios

---

## ✅ Checklist

- [ ] Cuenta de SumUp creada
- [ ] API key obtenida desde dashboard
- [ ] API key agregada a variables de entorno
- [ ] API key probada con curl o script de prueba
- [ ] API key configurada en el sistema
- [ ] Variables de entorno cargadas correctamente

---

**Nota:** Para desarrollo inicial, usar siempre API keys de test mode (`sk_test_`) antes de usar keys de producción.

