#!/bin/bash
# Wrapper script to run both geocoding approaches
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "===================================================="
echo "  GEOCODING DE R O U B O S  -  Duas Etapas"
echo "===================================================="
echo ""

# Step 1: Cross-reference
echo "📋 ETAPA 1: Cross-Reference"
echo "   Inferir coordenadas de endereços similares"
echo ""
python3 cross_reference_coords.py
echo ""

# Step 2: Mapbox geocoding (if MAPBOX token is set)
if [ -n "$MAPBOX_ACCESS_TOKEN" ]; then
    echo "🌍 ETAPA 2: Mapbox Geocoding"
    echo "   Geocoding dos registros restantes"
    echo ""
    python3 geocode_mapbox.py
else
    echo "⚠️  ETAPA 2: Mapbox Geocoding (SKIP)"
    echo "   MAPBOX_ACCESS_TOKEN não configurada"
    echo ""
    echo "   Para ativar, execute:"
    echo "   export MAPBOX_ACCESS_TOKEN='seu_token_aqui'"
    echo ""
fi

# Final stats
echo "===================================================="
echo "  RESULTADO FINAL"
echo "===================================================="
python3 -c "
import sqlite3
conn = sqlite3.connect('crimes.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM crimes WHERE latitude IS NOT NULL AND latitude != 0')
with_coords = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM crimes')
total = c.fetchone()[0]
c.execute('SELECT coords_source, COUNT(*) as cnt FROM crimes WHERE coords_source IS NOT NULL GROUP BY coords_source ORDER BY cnt DESC')
sources = c.fetchall()
print(f'\nTotal com coords:      {with_coords:,}/{total:,} ({with_coords/total*100:.1f}%)')
print(f'\nFonte das coordenadas:')
for source, cnt in sources:
    pct = cnt/with_coords*100
    print(f'  {source:30s} {cnt:>8,} ({pct:.1f}%)')
print('')
"

echo "✅ Geocoding concluído!"
echo ""
echo "Para atualizar o backend, reinicie o servidor:"
echo "  ./start.sh"
