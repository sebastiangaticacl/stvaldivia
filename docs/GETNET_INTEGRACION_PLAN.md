# 📋 Plan de Integración Getnet - Basado en Documentación Oficial

**Fuente:** [Documentación Getnet - Banco Santander](https://banco.santander.cl/uploads/000/054/707/ec812630-dcbf-4f52-8883-b3b01d9f985b/original/Documentacion.zip)  
**Fecha:** 2025-12-18

---

## 📚 Documentación Disponible

1. **Documentacion Javascript 1.0.pdf** - SDK JavaScript para integración
2. **Integracion Getnet - Manual de integracion 1.11.pdf** - Manual de integración completo

---

## 🔍 Análisis Necesario

### 1. Revisar SDK JavaScript

El SDK parece estar en JavaScript. Esto es importante porque:

**Opciones de Implementación:**

1. **Opción A: Node.js Agent (Recomendado si el SDK es Node.js)**
   - Agente Node.js en lugar de Java
   - Más fácil de integrar con SDK JavaScript
   - Mejor soporte para comunicación serial en Node.js (paquete `serialport`)

2. **Opción B: Java + JNI Bridge**
   - Mantener agente Java
   - Crear bridge JNI para SDK JavaScript/Node.js
   - Más complejo

3. **Opción C: Java Native (si existe SDK Java)**
   - SDK nativo para Java
   - Más directo

### 2. Revisar Manual de Integración

Necesitamos identificar:
- ¿Qué tipo de comunicación usa? (Serial, USB, TCP/IP)
- ¿Cómo se autentica?
- ¿Qué métodos/APIs expone el SDK?
- ¿Ejemplos de código?
- ¿Configuración del terminal?

---

## 📝 Próximos Pasos Inmediatos

### Paso 1: Extraer y Revisar Documentación

```bash
cd docs/getnet_docs
unzip Documentacion.zip
# Revisar PDFs manualmente o extraer texto
```

### Paso 2: Determinar Tipo de SDK

- Si es SDK JavaScript/Node.js → Migrar agente a Node.js
- Si es SDK Java → Mantener agente Java
- Si es SDK C/C++ → Usar JNI en Java

### Paso 3: Adaptar Agente

Según el SDK disponible:
- Reemplazar función `ejecutarPago()` con llamadas reales al SDK
- Configurar comunicación serial/USB según documentación
- Implementar manejo de respuestas del terminal

### Paso 4: Configurar Terminal

Según documentación:
- Configurar credenciales/autenticación
- Configurar puerto COM (COM4)
- Configurar baudrate (115200)

---

## 🎯 Decisión Requerida

Una vez revisada la documentación, necesitamos decidir:

1. **¿Migrar agente a Node.js?** (si el SDK es JavaScript)
   - Pros: Integración más directa, mejor soporte serial
   - Contras: Cambio de tecnología

2. **¿Mantener Java?** (si existe SDK Java o podemos usar JNI)
   - Pros: Tecnología ya implementada
   - Contras: Puede requerir bridge si SDK es JavaScript

---

## 📁 Archivos de Documentación

Los PDFs están en: `docs/getnet_docs/Documentacion/`

**Siguiente acción:** Revisar manualmente estos PDFs para determinar:
- Tipo de SDK
- Métodos de integración
- Ejemplos de código
- Configuración requerida













