#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"

TARGET="/var/www/stvaldivia/app/helpers/dashboard_metrics_service.py"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

gcloud compute ssh "${USER}@${VM}" --command "sudo bash -lc '
set -euo pipefail

FILE=\"$TARGET\"
test -f \"\$FILE\" || { echo \"ERROR: No existe \$FILE\"; exit 1; }

echo \"== Backup ==\"
cp \"\$FILE\" \"\$FILE.bak.\$(date +%F-%H%M%S)\"

echo \"== Patch: asegurar rollback ante Exception en consultas ==\"

python3 - <<PY
import re, pathlib
p = pathlib.Path(\"$TARGET\")
s = p.read_text(encoding=\"utf-8\", errors=\"ignore\")

# Si ya tiene rollback en except, no tocar.
if re.search(r\"except\\s+Exception\\s+as\\s+\\w+:\\s*\\n\\s*db\\.session\\.rollback\\(\\)\", s):
    print(\"OK: rollback ya presente. No se modifica.\")
    raise SystemExit(0)

# Inserta rollback en el primer bloque except Exception as e: (si existe)
m = re.search(r\"(except\\s+Exception\\s+as\\s+\\w+:\\s*\\n)\", s)
if not m:
    print(\"NO PATCH: no se encontró except Exception para insertar rollback automáticamente.\")
    raise SystemExit(2)

idx = m.end(1)
s2 = s[:idx] + \"    db.session.rollback()\\n\" + s[idx:]
p.write_text(s2, encoding=\"utf-8\")
print(\"PATCHED: rollback insertado en el primer except Exception.\")
PY

RC=${PIPESTATUS[0]}
if [ \"${RC:-0}\" -eq 2 ]; then
  echo \"ATENCION: No se pudo parchear automáticamente. Revisión manual requerida.\"
  exit 2
fi

echo \"== Reiniciando servicio ==\"
systemctl restart stvaldivia
sleep 2
systemctl is-active --quiet stvaldivia && echo \"OK: stvaldivia activo\"

echo \"== Logs recientes (buscando InFailedSqlTransaction) ==\"
journalctl -u stvaldivia -n 120 --no-pager | egrep -i \"InFailedSqlTransaction|transaction is aborted|ERROR\" || true
'"

