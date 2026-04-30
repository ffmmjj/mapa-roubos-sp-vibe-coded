# Mapa de Crimes - Roubo de Celulares (São Paulo)

Dashboard interativo para visualização de dados de roubo de celulares no estado de São Paulo, com filtros por ano, cidade, bairro, período e seleção de área no mapa.

## 📊 Dados

- **Período**: 2023 a 2025
- **Total de roubos**: 507.159
- **Com coordenadas**: 498.001 (98,2%)
- **Municípios**: Vários do estado de São Paulo

## ✨ Funcionalidades

- 📍 Mapa interativo com clustering e heatmap
- 📊 Estatísticas gerais e por área selecionada
- 🔍 Filtros: ano, cidade, bairro, período do dia, data
- ✋ Seleção retangular de áreas com estatísticas
- 📈 Gráficos por período, mês, tipo local, marcas

## 🚀 Início Rápido

### Opção 1: Docker (Recomendado)

```bash
# Clonar o repositório
git clone <seu-repositorio>
cd mapa-crimes

# Executar com docker-compose (o banco já está incluído na imagem)
docker-compose up -d

# Acessar: http://localhost:8000
```

**Comandos úteis:**
```bash
# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Reconstruir imagem (apenas se alterar código)
docker-compose up -d --build

# Entrar no container
docker-compose exec web bash
```

### Opção 2: Instalação Manual

#### Pré-requisitos
- Python 3.10+
- pip

#### Passos

1. Clone o repositório
2. Execute o setup:
   ```bash
   ./setup.sh
   ```
   Ou manualmente:
   ```bash
   cd backend
   pip install -r requirements.txt
   gunzip crimes.db.gz
   ```

3. Inicie o servidor:
   ```bash
   ./start.sh
   ```
   Ou manualmente:
   ```bash
   cd backend
   python3 main.py
   ```

4. Acesse: http://localhost:8000

## 📁 Estrutura do Projeto

```
mapa-crimes/
├── backend/
│   ├── main.py                 # API FastAPI
│   ├── import_full.py          # Importação inicial de dados
│   ├── import_additional.py    # Adicionar novos anos
│   ├── cross_reference_coords.py  # Geocoding por cross-reference
│   ├── geocode_mapbox.py       # Geocoding com Mapbox API
│   ├── geocode_all.sh          # Script completo de geocoding
│   ├── requirements.txt        # Dependências
│   └── crimes.db.gz            # Banco de dados comprimido (45MB)
├── frontend/
│   └── index.html              # Interface do usuário
├── Dockerfile                  # Imagem Docker
├── docker-compose.yml          # Compose Docker
├── setup.sh                    # Script de setup
├── start.sh                    # Script de inicialização
└── README.md                   # Este arquivo
```

## 🔌 API Endpoints

| Endpoint | Descrição |
|----------|-----------|
| `GET /` | Interface do usuário |
| `GET /api/crimes` | Obter pontos de crime |
| `GET /api/crimes/count` | Contar crimes com filtros |
| `GET /api/crimes/heatmap` | Dados para heatmap |
| `GET /api/stats` | Estatísticas gerais |
| `GET /api/stats/area` | Estatísticas de área selecionada |

## 🔍 Parâmetros de Filtro

- `bounds`: Coordenadas do mapa (sw_lat,sw_lon,ne_lat,ne_lon)
- `cidade`: Filtro por cidade
- `bairro`: Filtro por bairro
- `periodo`: Período do dia (Manhã, Tarde, Noite, Madrugada)
- `ano`: Ano de ocorrência (2023, 2024, 2025)
- `data_inicio`: Data inicial (YYYY-MM-DD)
- `data_fim`: Data final (YYYY-MM-DD)

## ➕ Adicionar Novos Dados

### Via Docker

```bash
# Coloque o arquivo .xlsx na raiz do projeto
docker-compose run --rm importer python3 import_additional.py /data/CelularesSubtraidos_XXXX.xlsx
```

### Via Instalação Manual

1. Coloque o arquivo `.xlsx` na raiz do projeto
2. Execute:
   ```bash
   cd backend
   python3 import_additional.py ../CelularesSubtraidos_XXXX.xlsx
   ```
3. Execute o geocoding:
   ```bash
   python3 cross_reference_coords.py
   export MAPBOX_ACCESS_TOKEN="seu_token"
   python3 geocode_mapbox.py
   ```
4. Comprima o banco:
   ```bash
   gzip crimes.db
   ```

## 🗺️ Geocoding

O projeto usa um sistema de duas etapas para geocodificar registros sem coordenadas:

1. **Cross-reference**: Busca endereços similares no próprio banco (gratuito)
2. **Mapbox API**: Para os registros restantes (requer token gratuito)

### Usando o Mapbox

```bash
export MAPBOX_ACCESS_TOKEN="seu_token_aqui"
python3 geocode_mapbox.py
```

Para obter um token gratuito: https://www.mapbox.com/

## 🐛 Troubleshooting

### Docker

**Porta 8000 já em uso:**
```bash
# Altere a porta no docker-compose.yml
ports:
  - "8001:8000"
```

**Erro ao descomprimir crimes.db:**
```bash
# Descomprimir manualmente
gunzip backend/crimes.db.gz
```

### Instalação Manual

**Erro de dependências:**
```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Erro ao iniciar servidor:**
```bash
# Verificar se crimes.db existe
ls -la backend/crimes.db

# Se não existir, descomprimir:
gunzip backend/crimes.db.gz
```

## 📄 Fonte dos Dados

Dados públicos do governo do estado de São Paulo sobre roubo de celulares.

## 📝 Licença

Este projeto é para fins educacionais e de análise de dados públicos.

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## 📞 Suporte

Se encontrar problemas, abra uma issue no repositório.
