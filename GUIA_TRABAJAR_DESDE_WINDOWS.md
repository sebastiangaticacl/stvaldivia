# 🪟 Guía: Trabajar desde Cursor en Windows

## Opción 1: Clonar desde GitHub (RECOMENDADO) ✅

### Pasos:

1. **Abrir Cursor en Windows**

2. **Clonar el repositorio**:
   - En Cursor: `File` → `Clone Repository`
   - O desde terminal:
   ```bash
   git clone https://github.com/stvaldivia/stvaldivia.git
   cd stvaldivia
   ```

3. **Abrir la carpeta en Cursor**:
   - `File` → `Open Folder`
   - Selecciona la carpeta `stvaldivia`

4. **Configurar el entorno**:
   ```bash
   # Crear entorno virtual
   python -m venv venv
   
   # Activar entorno virtual
   venv\Scripts\activate
   
   # Instalar dependencias
   pip install -r requirements.txt
   ```

5. **Ejecutar el proyecto**:
   ```bash
   python run_local.py
   ```

---

## Opción 2: Usar GitHub Desktop (Más Visual)

1. **Instalar GitHub Desktop**: https://desktop.github.com/
2. **Clonar el repositorio** desde GitHub Desktop
3. **Abrir en Cursor**: Click derecho → `Open in Cursor`

---

## Opción 3: Sincronizar con Git (Si ya tienes el proyecto)

```bash
# En Windows, en la carpeta del proyecto:
git pull origin main
```

---

## 🔄 Flujo de Trabajo Recomendado

### Para trabajar en equipo:

1. **Antes de empezar a trabajar**:
   ```bash
   git pull origin main
   ```

2. **Crear una rama para tu trabajo**:
   ```bash
   git checkout -b mi-nueva-funcionalidad
   ```

3. **Hacer cambios y commits**:
   ```bash
   git add .
   git commit -m "feat: descripción de cambios"
   ```

4. **Subir tus cambios**:
   ```bash
   git push origin mi-nueva-funcionalidad
   ```

5. **Crear Pull Request en GitHub** para revisar antes de mergear a `main`

---

## 📋 Checklist para Windows

- [ ] Git instalado (`git --version`)
- [ ] Python 3 instalado (`python --version`)
- [ ] Cursor instalado
- [ ] Repositorio clonado
- [ ] Entorno virtual creado y activado
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Proyecto ejecutándose (`python run_local.py`)

---

## 🚨 Problemas Comunes

### Error: "git no se reconoce como comando"
**Solución**: Instalar Git desde https://git-scm.com/download/win

### Error: "python no se reconoce"
**Solución**: Instalar Python desde https://www.python.org/downloads/

### Error al activar venv
**Solución**: Usar `venv\Scripts\activate` (con backslash en Windows)

### Conflictos al hacer pull
**Solución**: 
```bash
git stash  # Guardar cambios locales
git pull origin main
git stash pop  # Recuperar cambios
```

---

## 💡 Mejores Prácticas

1. **Siempre hacer `git pull` antes de empezar** a trabajar
2. **Crear ramas** para cada funcionalidad nueva
3. **Hacer commits frecuentes** con mensajes descriptivos
4. **Usar Pull Requests** para revisar código antes de mergear
5. **Comunicarse con el equipo** antes de hacer cambios grandes

---

## 🔗 Enlaces Útiles

- Repositorio: https://github.com/stvaldivia/stvaldivia
- Cursor: https://cursor.sh/
- Git para Windows: https://git-scm.com/download/win
- Python para Windows: https://www.python.org/downloads/


