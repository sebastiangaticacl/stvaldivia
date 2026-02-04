# Conectar todos los equipos a la misma base de datos (MySQL en cPanel)

Para que todos los computadores trabajen con la misma data, la app debe usar **MySQL en el servidor** (cPanel) en lugar de SQLite local.

---

## 1. En cPanel: tener la BD MySQL lista

- Ya creaste la base y el usuario en **MySQL Databases**.
- Ya importaste `backups/bimba_mysql_completo.sql` en **phpMyAdmin**.
- Anota: **usuario**, **contraseña**, **nombre de la base**, **host**.

---

## 2. Permitir conexiones remotas a MySQL (cPanel)

Para que tu PC u otro equipo se conecte a esa MySQL:

1. En cPanel → **Remote MySQL®** (o "MySQL Remote").
2. En **Access Hosts** agrega:
   - La IP de tu casa/oficina (recomendado), **o**
   - `%` para permitir cualquier IP (solo si es entorno de desarrollo).
3. Guarda.

**Host para conectarte:** suele ser tu dominio (ej. `stvaldivia.cl`) o el host que cPanel muestre para MySQL remoto (a veces `localhost` solo sirve para la app corriendo en el mismo servidor). Si conectas **desde tu PC**, usa el dominio o la IP del servidor, por ejemplo:

- `stvaldivia.cl`  
- o la IP del servidor si te la dan.

**Puerto:** normalmente `3306`. Algunos proveedores lo bloquean desde fuera; si no conecta, puedes usar un túnel SSH (ver más abajo).

---

## 3. En cada computador: configurar `.env`

En cada PC donde quieras la misma data:

1. Copia el proyecto (git clone o carpeta).
2. Crea o edita el archivo **`.env`** en la raíz del proyecto.
3. **Quita** (o pon en `false`) el reset y el seed local, para no borrar la BD compartida:
   ```env
   RESET_LOCAL_STATE_ON_START=false
   SEED_LOCAL_DATA_ON_START=false
   ```
4. **Pon** la URL de MySQL. Formato:

   ```env
   DATABASE_URL=mysql+mysqlconnector://USUARIO:CONTRASEÑA@HOST:3306/NOMBRE_BASE
   ```

   Ejemplo (reemplaza con tus datos reales):

   ```env
   DATABASE_URL=mysql+mysqlconnector://stvaldivia_user:MiPassword123@stvaldivia.cl:3306/stvaldivia_bimba
   ```

   Si en tu entorno usas **pymysql** en lugar de mysqlconnector:

   ```env
   DATABASE_URL=mysql+pymysql://stvaldivia_user:MiPassword123@stvaldivia.cl:3306/stvaldivia_bimba
   ```

5. Opcional pero recomendado para desarrollo compartido:
   ```env
   LOCAL_ONLY=true
   FLASK_ENV=development
   FLASK_DEBUG=True
   HOST=0.0.0.0
   PORT=5001
   ```

6. Guarda `.env` y **no** lo subas a Git (ya debería estar en `.gitignore`).

---

## 4. Probar la conexión

En la raíz del proyecto:

```bash
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
url = os.environ.get('DATABASE_URL','')
if url.startswith('mysql'):
    from sqlalchemy import create_engine
    e = create_engine(url)
    e.connect()
    print('OK: conexión a MySQL correcta')
else:
    print('Pon DATABASE_URL=mysql+... en .env')
"
```

Si ves `OK: conexión a MySQL correcta`, ese equipo ya está usando la BD compartida.

---

## 5. Arrancar la app

```bash
python3 run_local.py
```

En ese equipo la app usará la MySQL de cPanel; todos los que tengan el mismo `DATABASE_URL` verán la misma data.

---

## Si el puerto 3306 está bloqueado (no conecta)

Algunos hostings no permiten MySQL desde internet. Opciones:

- **Túnel SSH:** si tienes SSH a cPanel/servidor:
  ```bash
  ssh -L 3307:localhost:3306 usuario@stvaldivia.cl
  ```
  Y en `.env`:
  ```env
  DATABASE_URL=mysql+mysqlconnector://usuario:password@127.0.0.1:3307/nombre_base
  ```
- **Solo servidor:** dejar la app y la BD en cPanel y entrar siempre por la URL del sitio (ej. `https://stvaldivia.cl/...`); no conectar desde tu PC a MySQL.

---

## Resumen

| Qué quieres              | Dónde corre la app | Dónde está la BD | Qué poner en `.env` |
|--------------------------|--------------------|------------------|----------------------|
| Misma data en todos los PCs | En cada PC         | MySQL en cPanel  | `DATABASE_URL=mysql+...@servidor:3306/base` y `RESET/SEED=false` |
| Solo usar el sitio web   | En cPanel          | MySQL en cPanel  | En cPanel: `DATABASE_URL=mysql://...@localhost/base` |
