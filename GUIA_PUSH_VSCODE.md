# 🚀 Guía Completa: Push a GitHub desde VS Code

## 📦 Estado Actual del Repositorio

- **Commit listo:** `4824efd`
- **Mensaje:** "Ajustar dashboard admin: diseño edge-to-edge sin bordes, 100% ancho, estructura como imagen de referencia"
- **Branch:** `main` (1 commit adelante de origin/main)
- **Ubicación:** `/Users/sebagatica/stvaldivia/stvaldivia`
- **Remoto:** `https://github.com/stvaldivia/stvaldivia.git`

---

## 📋 PASO 1: Abrir VS Code y el Repositorio

### 1.1 Abrir VS Code
- Abre Visual Studio Code desde Aplicaciones o Spotlight (Cmd+Space, escribe "code")

### 1.2 Abrir la carpeta del proyecto
- **Opción A - Desde VS Code:**
  - File → Open Folder (Cmd+O)
  - Navega a: `/Users/sebagatica/stvaldivia/stvaldivia`
  - Click en "Open"

- **Opción B - Desde Finder:**
  - Abre Finder
  - Navega a la carpeta del proyecto
  - Click derecho → "Open with Code" (si está disponible)

- **Opción C - Desde Terminal (si code está en PATH):**
  ```bash
  cd /Users/sebagatica/stvaldivia/stvaldivia
  code .
  ```

### 1.3 Verificar que se abrió correctamente
- Deberías ver la estructura del proyecto en el explorador lateral
- Deberías ver archivos como `app/`, `requirements.txt`, `Dockerfile`, etc.

---

## 📋 PASO 2: Instalar Extensión de GitHub

### 2.1 Abrir el panel de Extensiones
- Presiona `Cmd+Shift+X` (o View → Extensions)

### 2.2 Buscar la extensión
- En el buscador, escribe: `GitHub Pull Requests and Issues`
- Autor: **GitHub**

### 2.3 Instalar
- Click en el botón **"Install"** (azul)
- Espera a que termine la instalación
- Puede pedirte reiniciar VS Code → Click en "Reload"

### 2.4 Verificar instalación
- Deberías ver un nuevo ícono en la barra lateral izquierda (Pull Requests)
- El ícono tiene forma de "PR" o un símbolo de GitHub

---

## 📋 PASO 3: Iniciar Sesión en GitHub

### 3.1 Abrir el panel de Pull Requests
- Click en el ícono de **Pull Requests** en la barra lateral izquierda
- O presiona `Cmd+Shift+P` y escribe "GitHub: Focus on Pull Requests View"

### 3.2 Iniciar sesión
- Verás un botón o mensaje que dice **"Sign in to GitHub"**
- Click en ese botón

### 3.3 Autenticación en el navegador
- Se abrirá tu navegador predeterminado
- Si no estás logueado en GitHub, inicia sesión
- GitHub te pedirá autorizar VS Code
- Click en **"Authorize Visual Studio Code"** o **"Authorize"**

### 3.4 Verificar autenticación
- Deberías ver tu nombre de usuario de GitHub en VS Code
- El panel de Pull Requests debería mostrar "Signed in as [tu_usuario]"

### 3.5 Si hay problemas de autenticación
- Ve a: Settings → Accounts → GitHub
- O usa: `Cmd+Shift+P` → "GitHub: Sign in"

---

## 📋 PASO 4: Configurar Remotes (si es necesario)

### 4.1 Verificar remotes actuales
- Abre la terminal integrada: `` Ctrl+` `` (backtick) o Terminal → New Terminal
- Ejecuta:
  ```bash
  git remote -v
  ```
- Deberías ver:
  ```
  origin  https://github.com/stvaldivia/stvaldivia.git (fetch)
  origin  https://github.com/stvaldivia/stvaldivia.git (push)
  ```

### 4.2 Configurar remotes en VS Code (si es necesario)
- Abre Settings: `Cmd+,` (Command + Coma)
- Busca: `githubPullRequests.remotes`
- Asegúrate que incluya: `["origin", "upstream"]`
- O agrega los remotes que uses

### 4.3 Si no aparece la configuración
- Por defecto, VS Code busca PRs en `origin` y `upstream`
- Si tu remoto se llama diferente, agrégalo a la lista

---

## 📋 PASO 5: Hacer Push del Commit

### 5.1 Ver el estado de Git
- Click en el ícono de **Source Control** en la barra lateral (Ctrl+Shift+G)
- O presiona `Ctrl+Shift+G`
- Deberías ver:
  - "main" con un indicador de que hay 1 commit adelante
  - El commit `4824efd` listo para push

### 5.2 Opción A - Push desde Source Control Panel
1. En el panel de Source Control, verás la branch `main`
2. Arriba del panel, verás un ícono de **sincronización** (dos flechas circulares)
3. Click en ese ícono
4. O click en los **3 puntos (...)** → **"Push"**

### 5.3 Opción B - Push desde Command Palette
1. Presiona `Cmd+Shift+P` (Command Palette)
2. Escribe: `Git: Push`
3. Selecciona "Git: Push" de la lista
4. Presiona Enter

### 5.4 Opción C - Push desde la barra de estado
1. Mira la barra de estado en la parte inferior de VS Code
2. Verás algo como: `main ↑1` (indicando 1 commit adelante)
3. Click en ese texto o en el ícono de sincronización
4. Selecciona "Push"

### 5.5 Si pide credenciales
- **Username:** Tu nombre de usuario de GitHub
- **Password:** Usa un **Personal Access Token** (no tu contraseña)
  - Obtener token en: https://github.com/settings/tokens
  - Generar nuevo token (classic)
  - Permisos: `repo`
  - Copiar y pegar el token como password

### 5.6 Confirmar push
- VS Code mostrará un mensaje de progreso
- Cuando termine, verás "Pushed to origin/main" o similar

---

## 📋 PASO 6: Verificar el Push

### 6.1 Verificar en VS Code
- En Source Control, la branch `main` ya no debería mostrar "↑1"
- Debería mostrar "✓" o estar sincronizada

### 6.2 Verificar en GitHub
1. Abre tu navegador
2. Ve a: https://github.com/stvaldivia/stvaldivia
3. Deberías ver:
   - El commit `4824efd` en la lista de commits
   - El mensaje: "Ajustar dashboard admin: diseño edge-to-edge sin bordes, 100% ancho, estructura como imagen de referencia"
   - La fecha/hora del commit

### 6.3 Verificar desde terminal
- En la terminal integrada de VS Code:
  ```bash
  git log origin/main -1
  ```
- Deberías ver el commit `4824efd`

---

## 🎯 Resumen de Atajos de Teclado

- **Abrir Source Control:** `Ctrl+Shift+G`
- **Command Palette:** `Cmd+Shift+P`
- **Abrir Extensions:** `Cmd+Shift+X`
- **Nueva Terminal:** `` Ctrl+` ``
- **Settings:** `Cmd+,`

---

## ❓ Solución de Problemas

### Problema: No veo el ícono de Pull Requests
- **Solución:** Asegúrate de que la extensión está instalada y VS Code está reiniciado

### Problema: "Sign in to GitHub" no funciona
- **Solución:** 
  - Ve a Settings → Accounts → GitHub
  - O usa Command Palette: "GitHub: Sign in"

### Problema: Push falla con error de autenticación
- **Solución:** 
  - Usa un Personal Access Token en lugar de tu contraseña
  - Obtener en: https://github.com/settings/tokens

### Problema: No veo el commit en Source Control
- **Solución:**
  - Verifica que estás en la branch `main`: `git branch`
  - Verifica el estado: `git status`

### Problema: VS Code no reconoce el repositorio Git
- **Solución:**
  - Asegúrate de estar en la carpeta correcta
  - Verifica que existe `.git`: `ls -la .git`

---

## ✅ Checklist Final

- [ ] VS Code abierto con la carpeta del proyecto
- [ ] Extensión de GitHub instalada
- [ ] Autenticado en GitHub desde VS Code
- [ ] Remotes configurados correctamente
- [ ] Commit `4824efd` visible en Source Control
- [ ] Push completado exitosamente
- [ ] Commit visible en GitHub.com

---

## 🎉 ¡Listo!

Una vez completado el push, el commit estará en GitHub y podrás:
- Hacer deploy a Google Cloud desde el servidor
- Crear Pull Requests
- Ver el historial de cambios
- Colaborar con otros desarrolladores

**¿Necesitas ayuda con algún paso específico?** Solo pregunta.

