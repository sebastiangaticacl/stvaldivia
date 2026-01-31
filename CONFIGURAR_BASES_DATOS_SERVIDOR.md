# Configuración de Bases de Datos en Servidor VM (Desarrollo Multi-Equipo)

## 📋 Resumen

Este sistema permite que **múltiples desarrolladores** trabajen desde diferentes computadoras, todos conectándose a las bases de datos que están **guardadas en el servidor VM de Google**. 

Las dos bases de datos (desarrollo y producción) están en el servidor, no localmente.

## 🏗️ Arquitectura

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Computadora 1  │     │  Computadora 2  │     │  Computadora 3   │
│  (Desarrollador)│     │  (Desarrollador)│     │  (Desarrollador) │
└────────┬────────┘     └────────┬────────┘     └────────┬─────────┘
         │                      │                       │
         │                      │                       │
         └──────────────────────┼───────────────────────┘
                                │
                                │ (Internet/VPN)
                                │
                    ┌───────────▼────────────┐
                    │   Servidor VM Google    │
                    │                        │
                    │  ┌──────────────────┐ │
                    │  │  bimba_prod (BD)  │ │
                    │  └──────────────────┘ │
                    │  ┌──────────────────┐ │
                    │  │  bimba_dev (BD)  │ │
                    │  └──────────────────┘ │
                    └────────────────────────┘
```

## 🔧 Configuración en el Servidor VM

### Paso 1: Crear las Bases de Datos en el Servidor

Conectarse al servidor VM y crear ambas bases de datos:

```bash
# Conectar al servidor VM
ssh usuario@[ip_servidor_vm]

# Conectar a MySQL
mysql -u root -p

# Crear base de datos de PRODUCCIÓN
CREATE DATABASE bimba_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Crear base de datos de DESARROLLO
CREATE DATABASE bimba_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# Crear usuario (si no existe)
CREATE USER 'bimba_user'@'%' IDENTIFIED BY 'password_seguro';
GRANT ALL PRIVILEGES ON bimba_prod.* TO 'bimba_user'@'%';
GRANT ALL PRIVILEGES ON bimba_dev.* TO 'bimba_user'@'%';
FLUSH PRIVILEGES;

EXIT;
```

### Paso 2: Configurar Variables de Entorno en el Servidor VM

En el servidor VM, editar el archivo de configuración del servicio:

**Si usas systemd (`/etc/systemd/system/bimba.service`):**
```ini
[Service]
Environment="DATABASE_PROD_URL=mysql://bimba_user:password@localhost:3306/bimba_prod"
Environment="DATABASE_DEV_URL=mysql://bimba_user:password@localhost:3306/bimba_dev"
Environment="DATABASE_MODE=prod"
```

**Si usas archivo `.env` en el servidor:**
```bash
# En /ruta/a/proyecto/.env
DATABASE_PROD_URL=mysql://bimba_user:password@localhost:3306/bimba_prod
DATABASE_DEV_URL=mysql://bimba_user:password@localhost:3306/bimba_dev
DATABASE_MODE=prod
```

### Paso 3: Configurar Acceso Remoto (Opcional)

Si los desarrolladores necesitan conectarse directamente desde sus computadoras:

```bash
# En el servidor VM, editar MySQL
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Cambiar:
bind-address = 0.0.0.0  # Permitir conexiones remotas

# Reiniciar MySQL
sudo systemctl restart mysql

# Configurar firewall (si es necesario)
sudo ufw allow 3306/tcp
```

**⚠️ IMPORTANTE:** Solo habilitar acceso remoto si es necesario y con seguridad adecuada (VPN, IPs permitidas, etc.)

## 💻 Configuración en Computadoras de Desarrollo

### Opción A: Conectarse al Servidor VM (Recomendado)

Cada desarrollador configura su `.env` local para apuntar al servidor:

```bash
# .env en computadora de desarrollo
# Conectar a bases de datos en el servidor VM

# Base de datos de PRODUCCIÓN (en servidor)
DATABASE_PROD_URL=mysql://bimba_user:password@[IP_SERVIDOR_VM]:3306/bimba_prod

# Base de datos de DESARROLLO (en servidor)
DATABASE_DEV_URL=mysql://bimba_user:password@[IP_SERVIDOR_VM]:3306/bimba_dev

# Modo inicial
DATABASE_MODE=dev  # o prod según prefiera
```

**Ejemplo:**
```bash
DATABASE_PROD_URL=mysql://bimba_user:password123@34.123.45.67:3306/bimba_prod
DATABASE_DEV_URL=mysql://bimba_user:password123@34.123.45.67:3306/bimba_dev
DATABASE_MODE=dev
```

### Opción B: Usar SSH Tunnel (Más Seguro)

Para mayor seguridad, usar túnel SSH:

```bash
# En la computadora de desarrollo, crear túnel SSH
ssh -L 3307:localhost:3306 usuario@[IP_SERVIDOR_VM]

# Luego en .env local:
DATABASE_PROD_URL=mysql://bimba_user:password@127.0.0.1:3307/bimba_prod
DATABASE_DEV_URL=mysql://bimba_user:password@127.0.0.1:3307/bimba_dev
```

## 🎮 Uso del Toggle desde Cualquier Computadora

1. **Cada desarrollador:**
   - Configura su `.env` local apuntando al servidor VM
   - Ejecuta la aplicación localmente
   - Accede a `/admin/panel_control`

2. **Cambiar modo:**
   - El toggle cambia la preferencia **en el servidor** (tabla `system_config`)
   - Todos los desarrolladores verán el mismo modo
   - ⚠️ **Requiere reiniciar la aplicación en el servidor** para que el cambio tome efecto en producción

3. **Desarrollo local:**
   - Cada desarrollador puede usar `DATABASE_MODE=dev` en su `.env` local
   - Esto solo afecta su computadora, no el servidor

## 🔄 Flujo de Trabajo Recomendado

### Desarrollo Local
```bash
# En .env de cada desarrollador
DATABASE_MODE=dev
DATABASE_DEV_URL=mysql://user:pass@[IP_SERVIDOR]:3306/bimba_dev
```

### Servidor de Producción
```bash
# En el servidor VM
DATABASE_MODE=prod  # Cambiar desde panel de control cuando sea necesario
DATABASE_PROD_URL=mysql://user:pass@localhost:3306/bimba_prod
DATABASE_DEV_URL=mysql://user:pass@localhost:3306/bimba_dev
```

## 📝 Script de Configuración Rápida

Crear `scripts/configurar_bd_servidor.sh` en el servidor:

```bash
#!/bin/bash
# Script para configurar bases de datos en el servidor VM

echo "🔧 Configurando bases de datos en servidor VM..."

# Obtener IP del servidor
SERVER_IP=$(hostname -I | awk '{print $1}')

# Crear archivo .env si no existe
ENV_FILE="/ruta/a/proyecto/.env"

cat >> "$ENV_FILE" << EOF

# Bases de datos en servidor VM
DATABASE_PROD_URL=mysql://bimba_user:password@localhost:3306/bimba_prod
DATABASE_DEV_URL=mysql://bimba_user:password@localhost:3306/bimba_dev
DATABASE_MODE=prod
EOF

echo "✅ Variables de entorno configuradas"
echo "📋 IP del servidor: $SERVER_IP"
echo ""
echo "💡 Para desarrolladores, usar en su .env local:"
echo "   DATABASE_PROD_URL=mysql://bimba_user:password@$SERVER_IP:3306/bimba_prod"
echo "   DATABASE_DEV_URL=mysql://bimba_user:password@$SERVER_IP:3306/bimba_dev"
```

## 🔒 Seguridad

### Recomendaciones

1. **Usar VPN** para acceso remoto a las bases de datos
2. **Limitar IPs** que pueden conectarse a MySQL
3. **Usar SSH Tunnel** en lugar de acceso directo
4. **Rotar passwords** regularmente
5. **No commitear** archivos `.env` con credenciales

### Configurar IPs Permitidas en MySQL

```sql
-- Solo permitir conexiones desde IPs específicas
CREATE USER 'bimba_user'@'192.168.1.%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON bimba_dev.* TO 'bimba_user'@'192.168.1.%';
GRANT ALL PRIVILEGES ON bimba_prod.* TO 'bimba_user'@'192.168.1.%';
```

## 🛠️ Comandos Útiles

### En el Servidor VM

```bash
# Ver bases de datos
mysql -u root -p -e "SHOW DATABASES LIKE 'bimba%';"

# Ver usuarios y permisos
mysql -u root -p -e "SELECT User, Host FROM mysql.user WHERE User='bimba_user';"

# Ver configuración actual
python3 -c "from app import create_app; from app.helpers.database_config_helper import get_current_database_info; app = create_app(); app.app_context().push(); import json; print(json.dumps(get_current_database_info(), indent=2))"
```

### En Computadoras de Desarrollo

```bash
# Probar conexión al servidor
mysql -h [IP_SERVIDOR] -u bimba_user -p -e "SHOW DATABASES;"

# Verificar configuración local
cat .env | grep DATABASE
```

## 📊 Resumen de Configuración

| Entorno | Base de Datos | Ubicación | Acceso |
|---------|--------------|-----------|--------|
| **Producción** | `bimba_prod` | Servidor VM | Solo servidor |
| **Desarrollo** | `bimba_dev` | Servidor VM | Servidor + Desarrolladores |
| **Local (opcional)** | SQLite | Computadora local | Solo local |

## ✅ Checklist de Configuración

- [ ] Bases de datos creadas en servidor VM
- [ ] Usuario MySQL creado con permisos
- [ ] Variables de entorno configuradas en servidor
- [ ] Variables de entorno configuradas en cada computadora de desarrollo
- [ ] Migración ejecutada (`migrate_system_config.py`)
- [ ] Acceso remoto configurado (si es necesario)
- [ ] Seguridad configurada (VPN, firewall, IPs permitidas)
- [ ] Toggle funcionando en panel de control



