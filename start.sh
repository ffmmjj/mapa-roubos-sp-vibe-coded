#!/bin/bash

echo "🚀 Iniciando Mapa de Crimes..."

# Verificar se crimes.db existe, senão descomprimir
cd backend
if [ ! -f "crimes.db" ] && [ -f "crimes.db.gz" ]; then
    echo "📦 Descomprimindo crimes.db..."
    gunzip crimes.db.gz
fi

# Iniciar servidor
echo "📍 Iniciando servidor em http://localhost:8000"
python3 main.py
