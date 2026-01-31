# 🔐 AUTENTICACIÓN MANUAL - PASO A PASO

## ✅ PROCESO COMPLETO

### Paso 1: Generar Link de Autenticación

Ya tienes el link. Si necesitas generarlo de nuevo:

```bash
gcloud auth login --no-launch-browser
```

**IMPORTANTE:** Copia el link completo que aparece (es muy largo).

### Paso 2: Abrir en Navegador

1. **NO uses Safari** - Tiene problemas con HTTP/HTTPS
2. **Usa Chrome o Firefox**
3. **Pega el link completo** en la barra de direcciones
4. **Presiona Enter**

### Paso 3: Autenticarse

1. Google te pedirá que inicies sesión
2. Selecciona tu cuenta de Google (la que tiene acceso a `stvaldiviacl`)
3. Acepta los permisos solicitados
4. **IMPORTANTE:** Después de aceptar, Google te mostrará un **código de verificación**

### Paso 4: Copiar Código de Verificación

El código será algo como: `4/0ATX87IPV90JnIC_ZCxsKgEQ0At...` (muy largo)

### Paso 5: Pegar Código en Terminal

1. Vuelve a la terminal
2. Pega el código
3. Presiona Enter

### Paso 6: Verificar

```bash
gcloud auth list
```

Deberías ver tu cuenta activa.

---

## 🚀 DESPUÉS DE AUTENTICARSE

Una vez autenticado, ejecuta:

```bash
cd /Users/sebagatica/tickets_cursor_clean
bash deploy_cloud_run.sh
```

---

## ⚠️ SI EL CÓDIGO EXPIRA

Si el código expira (típicamente después de 10 minutos):

1. Vuelve a ejecutar: `gcloud auth login --no-launch-browser`
2. Obtén un nuevo link
3. Repite el proceso

---

## 🔄 ALTERNATIVA: USAR CUENTA DE SERVICIO

Si la autenticación interactiva sigue fallando, puedes usar una Service Account:

1. Crear Service Account desde consola web
2. Descargar JSON key
3. Usar: `gcloud auth activate-service-account --key-file=key.json`

Pero esto requiere acceso a la consola web, que también tiene el error de seguridad.

---

**ESTADO ACTUAL:** ⏳ Esperando que completes la autenticación manual en el navegador


