# Deploy a producción

**Ya no usamos Google Cloud (gcloud / Cloud Run).** El deploy es por **SSH** a la VM.

## Deploy completo (recomendado)

```bash
./deploy_completo.sh
```

- Requiere clave SSH en `~/.ssh/id_ed25519` (o `~/.ssh/id_rsa`) con acceso a la VM.
- Sube el código con rsync, instala dependencias y reinicia gunicorn.

## Actualizar solo código (git pull en la VM)

Si en la VM ya tienes el repo clonado:

```bash
./actualizar_produccion.sh [VM_IP] [USUARIO]
# Por defecto: 34.176.144.166 stvaldiviazal
```

## Sincronizar datos y luego deploy

```bash
./sync_and_deploy.sh
```

Pide que sincronices desde el panel local y luego ejecuta `deploy_completo.sh`.

---

La documentación antigua sobre Cloud Run y gcloud se mantiene en `docs/historial/` y en archivos como `ACTUALIZAR_CLOUD_RUN.md` solo como referencia histórica.
