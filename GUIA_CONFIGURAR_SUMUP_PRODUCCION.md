# 🔧 Guía: Configurar SumUp en Producción

## 📍 Ubicación de Configuración

Las variables de entorno en producción se configuran en el **servicio systemd**.

**Archivo:** `/etc/systemd/system/stvaldivia.service`

---

## 🎯 Opción 1: Usar Script Automático (Recomendado)

```bash
./configurar_sumup_produccion.sh
```

Este script:
- ✅ Crea backup del servicio
- ✅ Agrega variables de entorno SumUp
- ✅ Recarga systemd
- ✅ Reinicia el servicio

---

## 🎯 Opción 2: Configuración Manual

### Paso 1: Editar el Servicio Systemd

```bash
ssh stvaldivia
sudo nano /etc/systemd/system/stvaldivia.service
```

### Paso 2: Agregar Variables en la Sección [Service]

Buscar la sección `[Service]` y agregar estas líneas después de las líneas `Environment` existentes:

```ini
[Service]
Type=notify
User=deploy
Group=deploy
WorkingDirectory=/var/www/stvaldivia
Environment="PATH=/var/www/stvaldivia/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/var/www/stvaldivia"
Environment="SUMUP_API_KEY=sup_sk_Tzj0qRj01rcmdYN8YpK2bLIkdRWahvWQI"
Environment="PUBLIC_BASE_URL=https://stvaldivia.cl"
# Environment="SUMUP_MERCHANT_CODE=TU_MERCHANT_CODE"  # Opcional
ExecStart=/var/www/stvaldivia/venv/bin/gunicorn ...
```

### Paso 3: Recargar y Reiniciar

```bash
sudo systemctl daemon-reload
sudo systemctl restart stvaldivia.service
sudo systemctl status stvaldivia.service
```

---

## 🎯 Opción 3: Agregar Variables desde Terminal

```bash
ssh -i ~/.ssh/id_ed25519_gcp stvaldiviazal@34.176.144.166 "sudo bash << 'END'
# Crear backup
cp /etc/systemd/system/stvaldivia.service /etc/systemd/system/stvaldivia.service.backup.\$(date +%Y%m%d_%H%M%S)

# Agregar variables (usando sed o python)
# Método con sed:
sed -i '/Environment=\"PYTHONPATH=/a Environment=\"SUMUP_API_KEY=sup_sk_Tzj0qRj01rcmdYN8YpK2bLIkdRWahvWQI\"' /etc/systemd/system/stvaldivia.service
sed -i '/Environment=\"SUMUP_API_KEY=/a Environment=\"PUBLIC_BASE_URL=https://stvaldivia.cl\"' /etc/systemd/system/stvaldivia.service

# Recargar y reiniciar
systemctl daemon-reload
systemctl restart stvaldivia.service
END
"
```

---

## ✅ Verificación

### Ver Variables Configuradas

```bash
ssh stvaldivia 'sudo systemctl show stvaldivia.service --property=Environment'
```

Debes ver:
- `SUMUP_API_KEY=sup_sk_...`
- `PUBLIC_BASE_URL=https://stvaldivia.cl`

### Ver Logs del Servicio

```bash
ssh stvaldivia 'sudo journalctl -u stvaldivia.service -n 50 --no-pager'
```

### Verificar que la App Carga las Variables

```bash
ssh stvaldivia 'cd /var/www/stvaldivia && sudo -u deploy python3 -c "from app import create_app; app = create_app(); print(\"SUMUP_API_KEY:\", \"✅\" if app.config.get(\"SUMUP_API_KEY\") else \"❌\")"'
```

---

## 🔍 Ubicación del Archivo del Servicio

```
/etc/systemd/system/stvaldivia.service
```

**Permisos necesarios:** sudo/root

**Usuario del servicio:** `deploy`

---

## 📝 Variables a Configurar

### Obligatorias

```bash
SUMUP_API_KEY=sup_sk_Tzj0qRj01rcmdYN8YpK2bLIkdRWahvWQI
PUBLIC_BASE_URL=https://stvaldivia.cl
```

### Opcionales

```bash
SUMUP_MERCHANT_CODE=TU_MERCHANT_CODE  # Si tienes merchant code específico
```

---

## 🔄 Después de Configurar

1. **Recargar systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

2. **Reiniciar servicio:**
   ```bash
   sudo systemctl restart stvaldivia.service
   ```

3. **Verificar estado:**
   ```bash
   sudo systemctl status stvaldivia.service
   ```

---

## ⚠️ Notas Importantes

1. **Backup:** El script crea backup automático, pero siempre es bueno hacer uno manual:
   ```bash
   sudo cp /etc/systemd/system/stvaldivia.service /etc/systemd/system/stvaldivia.service.backup
   ```

2. **Sintaxis:** Las variables deben estar entre comillas:
   ```ini
   Environment="VARIABLE=valor"
   ```

3. **Reinicio necesario:** Después de cambiar variables, siempre reiniciar el servicio

4. **Logs:** Si algo falla, revisar logs:
   ```bash
   sudo journalctl -u stvaldivia.service -f
   ```

---

## 📚 Referencias

- **Archivo del servicio:** `/etc/systemd/system/stvaldivia.service`
- **Usuario del servicio:** `deploy`
- **Directorio del proyecto:** `/var/www/stvaldivia`
- **Script de configuración:** `configurar_sumup_produccion.sh`

---

**Última actualización:** 2025-01-15

