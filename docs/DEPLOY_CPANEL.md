# Despliegue en cPanel

Guía para subir y configurar la app Flask (BIMBA/stvaldivia) en cPanel cuando **ya creaste la aplicación** en "Setup Python App".

---

## 1. Qué subir al servidor

Sube todo el proyecto **excepto**:

- `venv/`, `env/` (el entorno virtual lo crea cPanel)
- `.env` (no subir; las variables se configuran en cPanel)
- `__pycache__/`, `*.pyc`, `instance/`, `*.db`, `node_modules/`, `backups/`

**Importante:** En la raíz del proyecto debe estar:

- `passenger_wsgi.py` (entrada para cPanel)
- `requirements.txt`
- carpeta `app/`
- `run_local.py`, `wsgi.py`, etc.

Si usas **File Manager** o **Git**: el directorio de la app en cPanel (Application root) debe ser la carpeta que contiene `passenger_wsgi.py` y `app/`.

---

## 2. Configuración en cPanel → Setup Python App

Con la app ya creada:

1. **Application root:** ruta donde está `passenger_wsgi.py` (ej. `stvaldivia` o `public_html/stvaldivia`).
2. **Application URL:** la URL donde se sirve la app. Si la app queda en un **subpath** (ej. `https://stvaldivia.cl/stvaldivia/`), debes configurar la variable de entorno **`APPLICATION_ROOT=/stvaldivia`** (ver sección 3). Si la app está en la raíz del dominio (ej. `https://stvaldivia.cl/`), no hace falta `APPLICATION_ROOT`.
3. **Application startup file:** debe ser `passenger_wsgi.py` (por defecto cPanel lo usa si existe).
4. **Python version:** 3.10 o 3.11 recomendado.

---

## 3. Variables de entorno obligatorias

En la misma pantalla de "Setup Python App" → **Configuration files** / **Environment variables**, define:

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Entorno de producción. |
| `FLASK_SECRET_KEY` | (string largo aleatorio) | Clave secreta para sesiones y cookies. Genera una con: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `DATABASE_URL` | `mysql+mysqlconnector://usuario:password@localhost:3306/nombre_bd` | Conexión MySQL. En cPanel suele ser `localhost` como host. |
| `APPLICATION_ROOT` | `/stvaldivia` | **Obligatorio si la app está en un subpath.** Para `https://stvaldivia.cl/stvaldivia/` usa `APPLICATION_ROOT=/stvaldivia`. Sin barra final. Si la app está en la raíz del dominio, no definas esta variable. |

**Ejemplo DATABASE_URL en cPanel (app en el mismo servidor):**

```bash
mysql+mysqlconnector://usuario_cpanel:TuPassword@localhost:3306/cpanel_nombre_bd
```

Si en el servidor usas **pymysql**:

```bash
mysql+pymysql://usuario_cpanel:TuPassword@localhost:3306/cpanel_nombre_bd
```

Opcionales útiles:

- `RESET_LOCAL_STATE_ON_START` = `false`
- `SEED_LOCAL_DATA_ON_START` = `false`

---

## 4. Base de datos MySQL en cPanel

1. **MySQL Databases:** crea la base y el usuario; asígnalo a la base.
2. **phpMyAdmin:** si tienes un `.sql` de exportación (por ejemplo el de `scripts/export_sqlite_to_mysql_full.py`), impórtalo en esa base.
3. En `DATABASE_URL` usa ese usuario, contraseña y nombre de base, con host `localhost`.

Ver también: `docs/CONEXION_BD_COMPARTIDA.md`.

---

## 5. Instalar dependencias

En "Setup Python App", usa el botón **Run pip install** (o equivalente) y ejecuta:

```bash
pip install -r requirements.txt
```

O por SSH, dentro del directorio de la app y con el virtualenv activado:

```bash
source /home/tu_usuario/virtualenv/stvaldivia/3.10/bin/activate
pip install -r requirements.txt
```

(La ruta del `virtualenv` puede variar; cPanel la muestra en la pantalla de la app.)

---

## 6. Reiniciar la aplicación

En "Setup Python App" → **Restart** (o "Restart application"). Tras subir código o cambiar variables, conviene reiniciar.

---

## 7. Comprobar que funciona

- Abre la URL de la aplicación (ej. `https://stvaldivia.cl`).
- Revisa los logs en cPanel (por ejemplo "Logs" de la aplicación o "Errors" del dominio) si hay 500 o errores de importación.

---

## Resumen rápido

1. Subir código (con `passenger_wsgi.py` y `app/` en la raíz de la app).
2. App root = carpeta que contiene `passenger_wsgi.py`.
3. Variables: `FLASK_ENV=production`, `FLASK_SECRET_KEY`, `DATABASE_URL` (MySQL en localhost).
4. MySQL en cPanel creada y, si aplica, datos importados.
5. `pip install -r requirements.txt` y **Restart**.

Si ya tienes la app creada en cPanel, con estos pasos deberías tener el sitio arriba. Si algo falla, el mensaje en los logs de cPanel suele indicar si falta variable de entorno o dependencia.
