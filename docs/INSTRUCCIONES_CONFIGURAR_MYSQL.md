# Instrucciones para Configurar MySQL y Ejecutar Migración

**Fecha:** 2025-12-25  
**Entorno:** macOS Local

---

## ⚠️ ESTADO ACTUAL

El script de verificación detectó que faltan algunos requisitos:

1. ❌ MySQL client no instalado
2. ❌ DATABASE_URL no configurado
3. ✅ mysql-connector-python (instalando...)
4. ✅ Migraciones MySQL listas (6 archivos)
5. ✅ Scripts de migración listos

---

## 📋 PASOS PARA COMPLETAR LA MIGRACIÓN

### Paso 1: Instalar MySQL (macOS)

**Opción A: Homebrew (Recomendado)**
```bash
brew install mysql
brew services start mysql
```

**Opción B: MySQL Installer**
- Descargar desde: https://dev.mysql.com/downloads/mysql/
- Instalar el paquete .dmg
- Seguir el asistente de instalación

**Verificar instalación:**
```bash
mysql --version
# Debe mostrar: mysql Ver 8.0.x o similar
```

---

### Paso 2: Crear Base de Datos MySQL

```bash
# Conectar a MySQL
mysql -u root -p

# Crear base de datos
CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Crear usuario (opcional, puedes usar root)
CREATE USER 'bimba_user'@'localhost' IDENTIFIED BY 'password_seguro';
GRANT ALL PRIVILEGES ON bimba_db.* TO 'bimba_user'@'localhost';
FLUSH PRIVILEGES;

# Salir
EXIT;
```

---

### Paso 3: Configurar DATABASE_URL

**Opción A: Variable de entorno (temporal)**
```bash
export DATABASE_URL="mysql://bimba_user:password_seguro@localhost:3306/bimba_db"
```

**Opción B: Archivo .env (permanente)**
```bash
# Crear .env en el directorio raíz del proyecto
cat > .env << 'EOF'
DATABASE_URL=mysql://bimba_user:password_seguro@localhost:3306/bimba_db
FLASK_ENV=development
SECRET_KEY=tu_secret_key_aqui
EOF
```

**⚠️ IMPORTANTE:** 
- Reemplazar `bimba_user` y `password_seguro` con tus credenciales reales
- No commitear el archivo `.env` (debe estar en `.gitignore`)

---

### Paso 4: Instalar Dependencias Python

```bash
cd /Users/sebagatica/stvaldivia
pip3 install -r requirements.txt
```

**Verificar:**
```bash
python3 -c "import mysql.connector; print('✅ mysql-connector-python instalado')"
```

---

### Paso 5: Verificar Preparación

```bash
./scripts/verificar_preparacion_mysql.sh
```

**Debe mostrar:**
- ✅ MySQL client encontrado
- ✅ DATABASE_URL configurado
- ✅ Conexión a MySQL exitosa
- ✅ Base de datos existe
- ✅ mysql-connector-python instalado
- ✅ Migraciones MySQL encontradas
- ✅ Scripts de migración listos

---

### Paso 6: Ejecutar Migración

```bash
./scripts/migrar_a_mysql.sh
```

**El script:**
1. Verifica requisitos
2. Crea backup automático
3. Pide confirmación
4. Aplica todas las migraciones
5. Verifica resultado

---

### Paso 7: Validar Migración

```bash
./scripts/validar_migracion_mysql.sh
```

**Verifica:**
- Tablas creadas
- Columnas correctas (UUID → CHAR(36))
- Índices creados
- Conectividad desde Python

---

### Paso 8: Probar Aplicación

```bash
python3 run_local.py
```

**Verificar:**
- Aplicación inicia sin errores
- Endpoints responden
- Queries funcionan correctamente

---

## 🔧 TROUBLESHOOTING

### Error: "mysql: command not found"

**Solución:**
```bash
# macOS con Homebrew
brew install mysql
export PATH="/usr/local/bin:$PATH"

# O agregar al .zshrc/.bashrc
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Error: "Access denied for user"

**Solución:**
- Verificar credenciales en DATABASE_URL
- Verificar que el usuario tiene permisos:
  ```sql
  GRANT ALL PRIVILEGES ON bimba_db.* TO 'bimba_user'@'localhost';
  FLUSH PRIVILEGES;
  ```

### Error: "Can't connect to MySQL server"

**Solución:**
- Verificar que MySQL está corriendo:
  ```bash
  brew services list | grep mysql
  # O
  mysql.server start
  ```
- Verificar host y puerto en DATABASE_URL

### Error: "Unknown database 'bimba_db'"

**Solución:**
```sql
CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 📊 CHECKLIST RÁPIDO

- [ ] MySQL instalado y corriendo
- [ ] Base de datos `bimba_db` creada
- [ ] Usuario MySQL creado (o usar root)
- [ ] DATABASE_URL configurado en .env o export
- [ ] mysql-connector-python instalado
- [ ] Script de verificación pasa sin errores
- [ ] Backup de datos existentes (si aplica)
- [ ] Listo para ejecutar migración

---

## 🚀 COMANDOS RÁPIDOS

```bash
# 1. Instalar MySQL (macOS)
brew install mysql && brew services start mysql

# 2. Crear BD
mysql -u root -p -e "CREATE DATABASE bimba_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 3. Configurar .env
echo "DATABASE_URL=mysql://root:password@localhost:3306/bimba_db" > .env

# 4. Instalar dependencias
pip3 install -r requirements.txt

# 5. Verificar
./scripts/verificar_preparacion_mysql.sh

# 6. Migrar
./scripts/migrar_a_mysql.sh

# 7. Validar
./scripts/validar_migracion_mysql.sh

# 8. Probar
python3 run_local.py
```

---

**Última actualización:** 2025-12-25

