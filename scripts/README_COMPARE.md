# Scripts de Comparación Local vs Servidor

## Scripts Disponibles

### 1. `compare_db_simple.py` - Comparación Simple (Recomendado)

Script simple y rápido para comparar cajas, productos y ventas entre local y servidor.

**Uso local (conectándose al servidor):**
```bash
# Opción 1: Pasar URL como argumento
python3 scripts/compare_db_simple.py "postgresql://user:pass@stvaldivia.cl:5432/dbname"

# Opción 2: Variable de entorno
export SERVER_DATABASE_URL="postgresql://user:pass@stvaldivia.cl:5432/dbname"
python3 scripts/compare_db_simple.py
```

**Uso en servidor (comparando con local):**
```bash
# En el servidor, ejecutar:
cd /var/www/stvaldivia
python3 scripts/compare_db_simple.py
# (mostrará solo datos del servidor si no hay URL de local)
```

### 2. `compare_local_vs_server_db.py` - Comparación Completa

Script más completo que compara estructura de tablas, columnas y datos.

**Uso:**
```bash
export SERVER_DATABASE_URL="postgresql://user:pass@stvaldivia.cl:5432/dbname"
python3 scripts/compare_local_vs_server_db.py
```

### 3. `diagnose_sales_and_registers.py` - Diagnóstico Local

Script para diagnosticar qué hay en la base de datos local (o servidor si se ejecuta allí).

**Uso:**
```bash
# Local
python3 scripts/diagnose_sales_and_registers.py

# En servidor
cd /var/www/stvaldivia
python3 scripts/diagnose_sales_and_registers.py
```

## Obtener URL de Base de Datos del Servidor

Para comparar desde local, necesitas la URL de conexión de la BD del servidor:

```bash
# En el servidor, ver .env
cd /var/www/stvaldivia
cat .env | grep DATABASE_URL
```

O desde la aplicación:
```bash
# En el servidor
cd /var/www/stvaldivia
python3 -c "from app import create_app; app = create_app(); print(app.config['SQLALCHEMY_DATABASE_URI'])"
```

## Ejemplo de Salida

```
================================================================================
🔍 COMPARACIÓN: BASE DE DATOS LOCAL vs SERVIDOR
================================================================================

================================================================================
  📦 CAJAS (pos_registers)
================================================================================

✅ LOCAL: 3 cajas activas
   - ID: 1 | Código: SUPERADMIN | Nombre: caja-superadmin
   - ID: 2 | Código: PUERTA | Nombre: Puerta
   - ID: 5 | Código: TEST001 | Nombre: CAJA TEST BIMBA 🧪 TEST

✅ SERVIDOR: 2 cajas activas
   - ID: 1 | Código: SUPERADMIN | Nombre: caja-superadmin
   - ID: 2 | Código: PUERTA | Nombre: Puerta

⚠️  Solo en LOCAL (1):
   - CAJA TEST BIMBA (ID: 5)
```

## Notas

- Los scripts requieren acceso a ambas bases de datos
- Asegúrate de tener las credenciales correctas
- Las comparaciones no modifican datos, solo leen
- Los scripts muestran diferencias pero no las sincronizan automáticamente

