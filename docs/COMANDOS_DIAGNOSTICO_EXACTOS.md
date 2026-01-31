# Comandos Exactos para Diagnóstico de BD en Servidor Linux

## ⚠️ IMPORTANTE

**Estos comandos deben ejecutarse EN EL SERVIDOR LINUX en `/var/www/stvaldivia`**

No ejecutar en entorno local macOS.

---

## 📋 COMANDOS EXACTOS

### 1. Verificar archivo .env

```bash
cd /var/www/stvaldivia
ls -la .env
cat .env | grep "^DATABASE_URL="
```

**Salida esperada:** Ruta del archivo y contenido de DATABASE_URL

---

### 2. Verificar PostgreSQL instalado

```bash
psql --version
which psql
```

**Salida esperada:** Versión de psql y ruta del binario

---

### 3. Verificar servicio PostgreSQL

```bash
systemctl status postgresql
```

**Alternativa si el servicio tiene otro nombre:**
```bash
systemctl list-units --type=service | grep -i postgres
```

**Salida esperada:** Estado del servicio (active/inactive)

---

### 4. Verificar puerto 5432

```bash
ss -lntp | grep 5432
```

**Alternativa si `ss` no está disponible:**
```bash
netstat -lntp | grep 5432
```

**Salida esperada:** Proceso escuchando en puerto 5432

---

### 5. Extraer y parsear DATABASE_URL

```bash
cd /var/www/stvaldivia
DATABASE_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
echo "$DATABASE_URL" | sed 's/:[^:@]*@/:***@/g'
```

**Parsear componentes con Python:**
```bash
python3 << 'PYEOF'
import re
import os

try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
                if match:
                    user, password, host, port, dbname = match.groups()
                    print(f"Usuario: {user}")
                    print(f"Host: {host}")
                    print(f"Puerto: {port}")
                    print(f"Base de datos: {dbname}")
                    break
                else:
                    match = re.match(r'postgresql://([^@]+)@([^:]+):(\d+)/(.+)', db_url)
                    if match:
                        user, host, port, dbname = match.groups()
                        print(f"Usuario: {user}")
                        print(f"Host: {host}")
                        print(f"Puerto: {port}")
                        print(f"Base de datos: {dbname}")
                        print("⚠️ Sin password en URL")
                        break
except Exception as e:
    print(f"Error: {e}")
PYEOF
```

**Salida esperada:** Componentes parseados de DATABASE_URL

---

### 6. Probar conexión con DATABASE_URL

```bash
cd /var/www/stvaldivia
export $(grep "^DATABASE_URL=" .env | xargs)
psql "$DATABASE_URL" -c "SELECT 1 as test, current_database(), current_user;"
```

**Salida esperada:** 
- Si exitoso: Resultado de la query
- Si falla: Mensaje de error (autenticación, conexión, etc.)

---

### 7. Probar conexión como postgres local (si falla la anterior)

```bash
# Extraer nombre de BD
DB_NAME=$(python3 << 'PYEOF'
import re
import os
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.split('=', 1)[1].strip().strip('"').strip("'")
                match = re.match(r'postgresql://[^@]+@[^:]+:\d+/(.+)', db_url)
                if not match:
                    match = re.match(r'postgresql://[^:]+:[^@]+@[^:]+:\d+/(.+)', db_url)
                if match:
                    print(match.group(1))
                    break
except:
    pass
PYEOF
)

# Probar conexión
sudo -u postgres psql -d "$DB_NAME" -c "SELECT current_user, current_database();"
```

**Si falla, listar bases disponibles:**
```bash
sudo -u postgres psql -l
```

**Salida esperada:** 
- Si exitoso: Usuario y base de datos actual
- Si falla: Lista de bases disponibles o error

---

### 8. Verificar pg_dump

```bash
which pg_dump
pg_dump --version
```

**Si no existe, comando para instalar (NO ejecutar aún):**

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install -y postgresql-client
```

**CentOS/RHEL:**
```bash
sudo yum install -y postgresql
```

**Fedora:**
```bash
sudo dnf install -y postgresql
```

---

## 📊 GENERAR REPORTE COMPLETO

Para generar el reporte completo en `docs/ESTADO_DB_REAL.md`, ejecutar:

```bash
cd /var/www/stvaldivia
./scripts/diagnostico_db_servidor.sh
```

O copiar todos los comandos anteriores y ejecutarlos manualmente, guardando la salida.

---

## 📝 FORMATO DEL REPORTE

El reporte `docs/ESTADO_DB_REAL.md` debe incluir:

1. ✅ Estado del archivo `.env`
2. ✅ Versión de PostgreSQL instalada
3. ✅ Estado del servicio PostgreSQL
4. ✅ Puerto 5432 escuchando
5. ✅ Componentes de DATABASE_URL (usuario, host, puerto, BD)
6. ✅ Resultado de prueba de conexión
7. ✅ Resultado de conexión como postgres
8. ✅ Estado de `pg_dump`
9. ✅ Comando para instalar `pg_dump` si falta

---

## ⚠️ NOTAS IMPORTANTES

- **Solo lectura:** Todos los comandos son de diagnóstico, no modifican nada
- **Sin cambios:** No se cambian credenciales ni configuraciones
- **Permisos:** Algunos comandos pueden requerir `sudo`
- **Errores esperados:** Si la conexión falla, documentar el error exacto

