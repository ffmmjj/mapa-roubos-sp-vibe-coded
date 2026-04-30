#!/bin/bash

echo "🔧 Setup do Mapa de Crimes"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor instale Python 3.10+"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Instalar dependências
echo ""
echo "📦 Instalando dependências..."
cd backend
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Erro ao instalar dependências"
    exit 1
fi

# Descomprimir banco de dados
echo ""
echo "📦 Descomprimindo banco de dados..."
if [ -f "crimes.db.gz" ]; then
    gunzip crimes.db.gz
    echo "✅ Banco de dados descomprimido"
else
    echo "⚠️  crimes.db.gz não encontrado. Verifique se está no diretório backend/"
fi

echo ""
echo "✅ Setup concluído!"
echo ""
echo "Para iniciar o servidor, execute:"
echo "  ./start.sh"
echo ""
echo "Ou manualmente:"
echo "  cd backend && python3 main.py"
