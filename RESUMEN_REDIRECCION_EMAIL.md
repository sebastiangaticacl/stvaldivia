# 📧 RESUMEN: Redirigir hola@stvaldivia.cl a hostingdelsur.cl

## 🎯 OBJETIVO
Redirigir todos los emails que lleguen a `hola@stvaldivia.cl` hacia una dirección de email en hostingdelsur.cl

## 📋 PASOS RÁPIDOS

### 1️⃣ Configurar Registro MX en Google Domains

**URL:** https://domains.google.com

1. Selecciona `stvaldivia.cl`
2. Ve a **DNS** → **Registros de recursos personalizados**
3. Elimina cualquier registro MX existente
4. Agrega nuevo registro:
   - **Tipo:** `MX`
   - **Nombre:** `@`
   - **Valor:** `0 hostingdelsur.cl`
   - **TTL:** `3600`

### 2️⃣ Verificar dominio en cPanel

**URL:** https://hostingdelsur.cl:2083

1. Ve a **Addon Domains** (Dominios adicionales)
2. Verifica que `stvaldivia.cl` esté listado
3. Si NO está, agrégalo como dominio adicional

### 3️⃣ Configurar Forwarder en cPanel

**URL:** https://hostingdelsur.cl:2083

1. Ve a **Email** → **Forwarders**
2. Click en **Add Forwarder**
3. Configura:
   - **Address:** `hola`
   - **Domain:** `stvaldivia.cl`
   - **Destination:** `[email]@hostingdelsur.cl` ⚠️ **CONFIRMAR ESTA DIRECCIÓN**

### 4️⃣ Verificar

```bash
# Verificar que el registro MX esté activo
dig stvaldivia.cl MX +short

# Debe mostrar: 0 hostingdelsur.cl.
```

## ⚠️ IMPORTANTE

**Necesitas confirmar la dirección de email destino exacta:**
- ¿A qué email en hostingdelsur.cl quieres que lleguen los correos?
- Ejemplo: info@hostingdelsur.cl, contacto@hostingdelsur.cl, etc.

## ⏱️ TIEMPO

- **Propagación MX:** 5-30 minutos (máximo 48 horas)
- **Forwarder:** Inmediato una vez que MX está activo

## 📄 DOCUMENTACIÓN COMPLETA

Ver archivo: `CONFIGURAR_REDIRECCION_EMAIL_GOOGLE.md`










