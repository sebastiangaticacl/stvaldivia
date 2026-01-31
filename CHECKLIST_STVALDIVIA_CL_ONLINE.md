# 📋 CHECKLIST: stvaldivia.cl EN LÍNEA

**Objetivo:** Dejar stvaldivia.cl funcionando correctamente apuntando a Cloud Run

---

## 🔍 ESTADO ACTUAL

### DNS Actual
- **stvaldivia.cl** → Apunta a IPs de Google (probablemente Load Balancer o Cloud DNS)
- **www.stvaldivia.cl** → Apunta a `ghs.googlehosted.com` (Google Sites)

### Infraestructura Disponible
1. ✅ **Cloud Run** - Configurado y listo (repo en GitHub)
2. ✅ **VM Google Cloud** (34.176.74.130) - Con Nginx configurado
3. ⚠️ **DNS** - No apunta directamente a ninguna infraestructura

---

## 🎯 OPCIONES PARA PONER EN LÍNEA

### OPCIÓN 1: Cloud Run + Load Balancer (Recomendado) ⭐
**Ventajas:**
- Escalable automáticamente
- SSL automático con Let's Encrypt
- Sin gestión de servidores
- Costo eficiente (pago por uso)

**Pasos:**
1. ✅ Repo configurado para Cloud Run
2. ⏳ Desplegar servicio en Cloud Run
3. ⏳ Configurar Load Balancer de Google Cloud
4. ⏳ Configurar DNS para apuntar al Load Balancer
5. ⏳ SSL automático vía Load Balancer

### OPCIÓN 2: VM + Nginx (Ya configurado)
**Ventajas:**
- Ya está configurado
- Control total del servidor

**Pasos:**
1. ✅ Nginx configurado en VM
2. ⏳ Cambiar DNS para apuntar a 34.176.74.130
3. ⏳ Configurar SSL con Let's Encrypt
4. ⏳ Verificar que Flask está corriendo

---

## 📝 CHECKLIST DETALLADA

### Para Cloud Run (Opción 1 - Recomendada)

#### 1. Desplegar en Cloud Run
- [ ] Ir a Cloud Run Console
- [ ] Crear nuevo servicio o usar existente
- [ ] Conectar con GitHub: `https://github.com/stvaldivia/stvaldivia.git`
- [ ] Branch: `main`
- [ ] Configurar build:
  - [ ] Dockerfile detectado automáticamente
  - [ ] Puerto: 8080 (automático)
  - [ ] Timeout: 300+ segundos

#### 2. Variables de Entorno en Cloud Run
- [ ] `FLASK_ENV=production`
- [ ] `FLASK_SECRET_KEY=<generar clave segura>`
- [ ] `DATABASE_URL=<postgresql://...>`
- [ ] `OPENAI_API_KEY=<si usas bot>` (opcional)
- [ ] `BIMBA_INTERNAL_API_KEY=<si usas API>` (opcional)

#### 3. Configurar Load Balancer
- [ ] Crear Load Balancer HTTP(S) en Google Cloud
- [ ] Backend: Cloud Run service
- [ ] Frontend: IP estática
- [ ] SSL: Certificado automático de Google

#### 4. Configurar DNS
- [ ] Cambiar registro A de `stvaldivia.cl` → IP del Load Balancer
- [ ] Cambiar registro A de `www.stvaldivia.cl` → IP del Load Balancer
- [ ] Esperar propagación DNS (5-60 minutos)

#### 5. Verificar
- [ ] `curl https://stvaldivia.cl/api/v1/public/evento/hoy`
- [ ] Verificar SSL (certificado válido)
- [ ] Verificar que todas las rutas funcionan

---

### Para VM + Nginx (Opción 2 - Alternativa)

#### 1. Verificar Flask en VM
- [ ] SSH a VM: `gcloud compute ssh sebastian@stvaldivia-vm --zone=southamerica-west1-a`
- [ ] Verificar servicio: `sudo systemctl status flask_app`
- [ ] Verificar logs: `sudo journalctl -u flask_app -n 50`
- [ ] Test local: `curl http://127.0.0.1:5001/api/v1/public/evento/hoy`

#### 2. Verificar Nginx
- [ ] Estado: `sudo systemctl status nginx`
- [ ] Test: `curl http://127.0.0.1` (debe responder desde Flask)
- [ ] Configuración: `/etc/nginx/sites-available/stvaldivia.cl`

#### 3. Configurar SSL
- [ ] Cambiar DNS para apuntar a `34.176.74.130`
- [ ] Esperar propagación DNS
- [ ] Ejecutar: `sudo certbot --nginx -d stvaldivia.cl -d www.stvaldivia.cl`
- [ ] Verificar: `curl https://stvaldivia.cl`

#### 4. Configurar Firewall
- [ ] Permitir HTTP (80): `gcloud compute firewall-rules create allow-http --allow tcp:80`
- [ ] Permitir HTTPS (443): `gcloud compute firewall-rules create allow-https --allow tcp:443`
- [ ] Verificar que puerto 5001 está cerrado al exterior

---

## 🔧 COMANDOS ÚTILES

### Verificar DNS
```bash
dig stvaldivia.cl +short
dig www.stvaldivia.cl +short
nslookup stvaldivia.cl
```

### Verificar Cloud Run
```bash
gcloud run services list
gcloud run services describe <service-name> --region=<region>
```

### Verificar Load Balancer
```bash
gcloud compute forwarding-rules list
gcloud compute addresses list
```

### Verificar VM
```bash
gcloud compute ssh sebastian@stvaldivia-vm --zone=southamerica-west1-a
sudo systemctl status flask_app
sudo systemctl status nginx
```

---

## ⚠️ PROBLEMAS COMUNES

### DNS no resuelve
- Verificar registros en tu proveedor de DNS
- Esperar propagación (puede tardar hasta 24 horas)
- Usar `dig` o `nslookup` para verificar

### SSL no funciona
- Verificar que DNS apunta correctamente
- Verificar que puertos 80/443 están abiertos
- Re-ejecutar certbot si es necesario

### Cloud Run no responde
- Verificar variables de entorno
- Verificar logs en Cloud Run Console
- Verificar que DATABASE_URL es correcto

### Error 502 Bad Gateway
- Verificar que Flask está corriendo (VM)
- Verificar configuración de Nginx
- Verificar logs de Nginx: `sudo tail -f /var/log/nginx/error.log`

---

## 🎯 RECOMENDACIÓN FINAL

**Usar Cloud Run + Load Balancer** porque:
1. ✅ Ya está configurado en el código
2. ✅ Escalable automáticamente
3. ✅ SSL automático
4. ✅ Menos mantenimiento
5. ✅ Costo eficiente

**Pasos inmediatos:**
1. Desplegar en Cloud Run (configurar variables de entorno)
2. Crear Load Balancer apuntando a Cloud Run
3. Cambiar DNS para apuntar al Load Balancer
4. Verificar que funciona

---

**Estado actual:** ⏳ **PENDIENTE CONFIGURACIÓN DNS Y DEPLOY**

