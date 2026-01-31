# 📦 Análisis SDK Getnet Java

**Fuente:** [SDK Getnet Java - Banco Santander](https://banco.santander.cl/uploads/000/054/702/e6038e13-44f5-4f62-a943-895a7358c7ca/original/Java.zip)  
**Fecha:** 2025-12-18

---

## 📚 Archivos del SDK

### JARs Incluidos:

1. **POSIntegradoGetnet.jar** - SDK principal de Getnet
2. **jSerialComm-2.9.3.jar** - Librería para comunicación serial (COM ports)
3. **gson-2.10.1.jar** - Librería JSON de Google (parsing JSON)

---

## ✅ DECISIÓN: Mantener Agente Java

**Perfecto!** El SDK es nativo Java, lo que significa:

- ✅ **No necesitamos migrar a Node.js**
- ✅ **Podemos usar el agente Java que ya tenemos**
- ✅ **Solo necesitamos integrar el SDK real**

---

## 🔧 Integración Requerida

### 1. Agregar JARs al Classpath

El agente necesita incluir estos JARs:

```bash
java -cp .:json.jar:POSIntegradoGetnet.jar:jSerialComm-2.9.3.jar:gson-2.10.1.jar GetnetAgent
```

### 2. Reemplazar Función `ejecutarPago()`

**Archivo:** `getnet_agent/java/GetnetAgent.java`

**Código actual (simulado):**
```java
private static JSONObject ejecutarPago(double amount, String currency) {
    // TODO: reemplazar por SDK/DLL real de Getnet
    boolean aprobado = true; // <-- SIMULACIÓN
    // ...
}
```

**Necesitamos:**
- Importar clases del SDK (`POSIntegradoGetnet.jar`)
- Inicializar conexión serial usando `jSerialComm` (COM4, 115200)
- Llamar métodos del SDK para procesar pago
- Manejar respuesta (aprobado/rechazado/código de autorización)

### 3. Configuración Serial

El SDK usa `jSerialComm` para comunicación serial:
- Puerto: COM4 (desde `provider_config` en BD)
- Baudrate: 115200 (desde `provider_config` en BD)
- Timeout: 30000ms (desde `provider_config` en BD)

---

## 📝 Próximos Pasos

### Paso 1: Revisar Documentación del SDK

Necesitamos identificar:
- ¿Qué clases/métodos expone `POSIntegradoGetnet.jar`?
- ¿Cómo se inicializa el SDK?
- ¿Cómo se procesa una transacción?
- ¿Qué parámetros necesita?
- ¿Qué respuesta devuelve?

### Paso 2: Actualizar Script de Setup

Modificar `getnet_agent/java/setup_getnet_agent_java.sh` para:
- Descargar/copiar los JARs del SDK
- Actualizar classpath en `run.sh`
- Incluir JARs en compilación

### Paso 3: Implementar Integración Real

Reemplazar `ejecutarPago()` con:
- Inicialización del SDK Getnet
- Configuración de puerto serial (COM4, 115200)
- Procesamiento de transacción
- Manejo de respuesta

### Paso 4: Testing

- Probar comunicación serial
- Probar transacción de prueba
- Verificar integración end-to-end

---

## 🎯 Archivos a Modificar

1. **`getnet_agent/java/setup_getnet_agent_java.sh`**
   - Agregar descarga/copia de JARs del SDK
   - Actualizar classpath

2. **`getnet_agent/java/GetnetAgent.java`**
   - Importar clases del SDK
   - Implementar `ejecutarPago()` real
   - Configurar comunicación serial

3. **`getnet_agent/java/build.sh`**
   - Incluir JARs del SDK en classpath de compilación

4. **`getnet_agent/java/run.sh`**
   - Incluir JARs del SDK en classpath de ejecución

---

## 📚 Referencias

- SDK JARs: `docs/getnet_docs/Java/`
- Documentación: `docs/getnet_docs/Documentacion/`
- Agente actual: `getnet_agent/java/GetnetAgent.java`

---

## ⚠️ Nota Importante

**Necesitamos revisar la documentación del SDK** para saber:
- Nombres de clases
- Métodos disponibles
- Ejemplos de uso
- Configuración requerida

**Siguiente acción:** Revisar documentación PDF para identificar APIs del SDK.













