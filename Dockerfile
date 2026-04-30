FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY backend/requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar arquivos do backend
COPY backend/main.py .
COPY backend/import_full.py .
COPY backend/import_additional.py .
COPY backend/import_data.py .
COPY backend/geocode_mapbox.py .
COPY backend/geocode_all.sh .
COPY backend/cross_reference_coords.py .

# Descomprimir o banco de dados
COPY backend/crimes.db.gz .
RUN gunzip crimes.db.gz

# Copiar frontend
COPY frontend/ /app/frontend/

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["python3", "main.py", "--host", "0.0.0.0"]
