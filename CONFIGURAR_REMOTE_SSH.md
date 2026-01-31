# 🔌 Configurar Remote-SSH en Cursor/VS Code

## ✅ Configuración SSH ya lista

Tu configuración SSH ya está lista en `~/.ssh/config`:

```
Host stvaldivia
    HostName 34.176.144.166
    User stvaldiviazal
    IdentityFile ~/.ssh/id_ed25519_gcp
    StrictHostKeyChecking no
    IdentitiesOnly yes
```

## 🚀 Conectar desde Cursor/VS Code

### Opción 1: Command Palette (Recomendado)

1. Presiona `Cmd+Shift+P` (Mac) o `Ctrl+Shift+P` (Windows/Linux)
2. Escribe: `Remote-SSH: Connect to Host`
3. Selecciona: `stvaldivia`
4. Se abrirá una nueva ventana conectada al servidor

### Opción 2: Desde la barra lateral

1. Haz clic en el ícono de "Remote Explorer" en la barra lateral (o `Cmd+Shift+E` luego busca "Remote")
2. En "SSH TARGETS", verás `stvaldivia`
3. Haz clic en el ícono de conexión junto a `stvaldivia`
4. O haz clic derecho → "Connect to Host in New Window"

## 📁 Abrir carpeta en el servidor

Una vez conectado:

1. `File` → `Open Folder...` (o `Cmd+O` / `Ctrl+O`)
2. Navega a: `/var/www/stvaldivia`
3. Haz clic en "OK"

## 🔧 Configuración recomendada para el servidor

Crea o edita `.vscode/settings.json` en el servidor (`/var/www/stvaldivia/.vscode/settings.json`):

```json
{
  "python.defaultInterpreterPath": "/var/www/stvaldivia/venv/bin/python3",
  "python.terminal.activateEnvironment": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/venv": false
  },
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true
}
```

## 🐍 Configurar Python en el servidor

1. Una vez conectado, presiona `Cmd+Shift+P`
2. Escribe: `Python: Select Interpreter`
3. Selecciona: `/var/www/stvaldivia/venv/bin/python3`

## ✅ Verificar conexión

Una vez conectado, abre una terminal integrada (`Ctrl+`` o `View` → `Terminal`) y ejecuta:

```bash
pwd
# Debería mostrar: /var/www/stvaldivia (o tu directorio actual)

python3 --version
# Debería mostrar la versión de Python del venv

ps aux | grep gunicorn
# Debería mostrar los procesos de gunicorn
```

## 🔍 Troubleshooting

### Si no aparece `stvaldivia` en la lista:

1. Verifica que `~/.ssh/config` tiene la configuración correcta
2. Reinicia Cursor/VS Code
3. Verifica permisos: `chmod 600 ~/.ssh/id_ed25519_gcp`

### Si falla la conexión:

1. Prueba desde terminal: `ssh stvaldivia`
2. Si funciona en terminal pero no en Cursor, verifica la extensión "Remote - SSH"
3. Revisa los logs: `View` → `Output` → Selecciona "Remote-SSH"

### Si no encuentra Python:

1. Verifica que el venv existe: `ls -la /var/www/stvaldivia/venv/bin/python3`
2. Selecciona manualmente el intérprete: `Cmd+Shift+P` → `Python: Select Interpreter`

## 📝 Extensiones recomendadas (se instalan automáticamente en el servidor)

- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Git (si necesitas trabajar con git)

## 🎯 Uso típico

1. Conecta a `stvaldivia` desde Cursor
2. Abre `/var/www/stvaldivia`
3. Edita archivos directamente en el servidor
4. Los cambios se guardan automáticamente
5. Reinicia gunicorn si es necesario: `sudo systemctl restart gunicorn`

## ⚠️ Notas importantes

- Los cambios se guardan directamente en el servidor
- No necesitas hacer commit/push para ver cambios (solo reinicia el servicio)
- El proyecto en el servidor NO es un repositorio git
- Para actualizar desde git, usa el script de deploy o copia archivos manualmente

