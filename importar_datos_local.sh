#!/bin/bash
# Script para importar datos de SQLite local a PostgreSQL en producción

set -e

echo "🔄 IMPORTANDO DATOS LOCALES A PRODUCCIÓN"
echo "=========================================="

LOCAL_DB="instance/bimba.db"
VM_USER="stvaldiviazal"
VM_IP="34.176.144.166"
SSH_KEY="$HOME/.ssh/id_ed25519_gcp"

if [ ! -f "$LOCAL_DB" ]; then
    echo "❌ Base de datos local no encontrada: $LOCAL_DB"
    exit 1
fi

echo "📊 Analizando base de datos local..."
TABLES=$(sqlite3 "$LOCAL_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")

echo ""
echo "📋 Tablas encontradas:"
for table in $TABLES; do
    count=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null || echo "0")
    echo "  - $table: $count registros"
done

echo ""
echo "🚀 Iniciando importación..."
echo ""

# Crear script SQL temporal para PostgreSQL
TEMP_SQL=$(mktemp)
echo "-- Importación de datos desde SQLite local" > "$TEMP_SQL"

# Función para exportar tabla de SQLite a formato SQL para PostgreSQL
export_table() {
    local table=$1
    local count=$(sqlite3 "$LOCAL_DB" "SELECT COUNT(*) FROM \"$table\";" 2>/dev/null || echo "0")
    
    if [ "$count" -eq 0 ]; then
        echo "  ⏭️  $table: Sin datos (omitida)"
        return
    fi
    
    echo "  📥 Exportando $table ($count registros)..."
    
    # Exportar datos en formato CSV
    TEMP_CSV=$(mktemp)
    sqlite3 -header -csv "$LOCAL_DB" "SELECT * FROM \"$table\";" > "$TEMP_CSV" 2>/dev/null || {
        echo "  ⚠️  Error exportando $table"
        rm -f "$TEMP_CSV"
        return
    }
    
    # Verificar que el CSV tiene datos (más de 1 línea = header + datos)
    if [ $(wc -l < "$TEMP_CSV") -le 1 ]; then
        echo "  ⏭️  $table: CSV vacío (omitida)"
        rm -f "$TEMP_CSV"
        return
    fi
    
    # Subir CSV a la VM
    scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$TEMP_CSV" "$VM_USER@$VM_IP:/tmp/${table}_import.csv" >/dev/null 2>&1
    
    # Crear script de importación en PostgreSQL
    cat >> "$TEMP_SQL" << EOF

-- Importar $table
\\echo 'Importando $table...'
\\copy "$table" FROM '/tmp/${table}_import.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',', NULL '');
EOF
    
    rm -f "$TEMP_CSV"
    echo "  ✅ $table exportada"
}

# Exportar cada tabla
for table in $TABLES; do
    export_table "$table"
done

# Subir script SQL a la VM
echo ""
echo "📤 Subiendo script de importación..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "$TEMP_SQL" "$VM_USER@$VM_IP:/tmp/import_data.sql" >/dev/null 2>&1

# Ejecutar importación en la VM
echo ""
echo "🔄 Ejecutando importación en PostgreSQL..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo -u postgres psql -d bimba -f /tmp/import_data.sql 2>&1" | grep -v "could not change directory" || true

# Limpiar archivos temporales
rm -f "$TEMP_SQL"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "rm -f /tmp/*_import.csv /tmp/import_data.sql" 2>/dev/null || true

echo ""
echo "✅ Importación completada"
echo ""
echo "📊 Verificando datos importados..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_IP" "sudo -u postgres psql -d bimba << 'SQL'
SELECT 
    schemaname,
    tablename,
    n_tup_ins as registros
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_tup_ins DESC
LIMIT 20;
SQL
" 2>&1 | grep -v "could not change directory" | head -25





