#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="stvaldivia"
ZONE="southamerica-west1-a"
VM="stvaldivia"
USER="stvaldiviazal"

TARGET="/var/www/stvaldivia/app/helpers/dashboard_metrics_service.py"

gcloud config set project "$PROJECT_ID" >/dev/null
gcloud config set compute/zone "$ZONE" >/dev/null

gcloud compute ssh "${USER}@${VM}" --command 'sudo bash -c "
set -euo pipefail

FILE=\"'$TARGET'\"
test -f \"\$FILE\" || { echo \"ERROR: No existe \$FILE\"; exit 1; }

echo \"== Backup ==\"
cp \"\$FILE\" \"\$FILE.bak.\$(date +%F-%H%M%S)\"

echo \"== Patch: agregar rollback en TODOS los bloques except Exception ==\"

python3 <<PYEOF
import re
import pathlib

p = pathlib.Path(\"'$TARGET'\")
s = p.read_text(encoding=\"utf-8\", errors=\"ignore\")

# Contar bloques except Exception
count = len(re.findall(r\"except\\s+Exception\\s+as\\s+\\w+:\", s))
print(f\"Encontrados {count} bloques except Exception\")

# Buscar todos los bloques except Exception que NO tienen rollback en las siguientes 3 líneas
lines = s.split(\"\\n\")
modified = False
i = 0
while i < len(lines):
    line = lines[i]
    # Si encontramos un except Exception
    if re.match(r\"\\s*except\\s+Exception\\s+as\\s+\\w+:\", line):
        # Verificar las siguientes 3 líneas para ver si ya tiene rollback
        has_rollback = False
        for j in range(i+1, min(i+4, len(lines))):
            if \"db.session.rollback()\" in lines[j]:
                has_rollback = True
                break
        
        if not has_rollback:
            # Insertar rollback después del except
            indent = len(line) - len(line.lstrip())
            rollback_line = \" \" * (indent + 4) + \"db.session.rollback()\"
            lines.insert(i+1, rollback_line)
            print(f\"  - Rollback agregado después de línea {i+1}: {line.strip()[:50]}...\")
            modified = True
            i += 1  # Saltar la línea que acabamos de insertar
    i += 1

if modified:
    s = \"\\n\".join(lines)
    p.write_text(s, encoding=\"utf-8\")
    print(\"PATCHED: rollback agregado en todos los bloques except Exception que lo necesitaban.\")
else:
    print(\"OK: Todos los bloques except Exception ya tienen rollback.\")
PYEOF

echo \"== Reiniciando servicio ==\"
systemctl restart stvaldivia
sleep 5
systemctl is-active --quiet stvaldivia && echo \"OK: stvaldivia activo\"

echo \"== Esperando 10 segundos y verificando logs ==\"
sleep 10
journalctl -u stvaldivia --since \"30 seconds ago\" --no-pager | grep -i \"InFailedSqlTransaction\" | head -5 || echo \"No se encontraron errores InFailedSqlTransaction recientes\"
"'
