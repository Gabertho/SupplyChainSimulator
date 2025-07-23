# Trabalho 2 – Sistemas Distribuídos

**Universidade Federal de São Carlos (UFSCar)**  
**Disciplina:** Sistemas Distribuídos  
**Professor:** Dr. Fredy João Valente  
**Aluno:** Gabriel Andreazi Bertho – RA: 790780  

---

## Visão Geral do Projeto

Este projeto simula um sistema de manufatura distribuído com controle de estoque em tempo real, utilizando a arquitetura de containers Docker e comunicação via Redis.

A empresa simulada possui:
- **2 fábricas**:
  - **Fábrica 1**: 5 linhas de produção (fabricação empurrada)
  - **Fábrica 2**: 8 linhas de produção (fabricação puxada)
- **1 almoxarifado central**
- **1 fornecedor**
- **1 depósito de produtos acabados**

São fabricados **5 produtos (Pv1 a Pv5)**, todos compostos por:
- Um **kit base fixo com 43 peças**
- Um **kit de variação específico por versão (20 a 33 peças extras)**
- Total de **100 peças únicas disponíveis**

---

## Entidades e Responsabilidades

###  Fábricas (`factory_redis.py`)
- Tipo **empurrada**: cada linha produz um produto fixo com lote de 60 unid.
- Tipo **puxada**: cada linha produz o produto com menor estoque.
- Recebem atualizações do nível de estoque via canal Redis e disparam ordens de produção via **Redis Pub/Sub**.

### Linhas de Produção (`line_redis.py`)
- Recebem ordens da fábrica para fabricar um determinado produto.
- Consomem peças do estoque local conforme necessidade do produto.
- Quando o nível de peças está baixo, disparam pedidos ao almoxarifado.
- Após produção, notificam o depósito central com as unidades prontas.

###  Almoxarifado (`warehouse_redis.py`)
- Controla estoque de todas as 100 peças.
- Atende pedidos de reabastecimento das linhas.
- Quando níveis críticos são detectados (Kanban vermelho/amarelo), envia pedidos ao fornecedor.

### Depósito de Produtos Acabados (`product_stock_redis.py`)
- Armazena unidades produzidas.
- Simula a **demanda de mercado** aleatoriamente dia a dia.
- Após consumo via pedidos, informa as fábricas para replanejamento.

###  Fornecedor (`supplier_redis.py`)
- Reativo: apenas responde aos pedidos do almoxarifado.
- Envia lotes de peças conforme necessidade.

### Dashboard Kanban (`kanban_visualizer.py`)
- Interface gráfica em tempo real com **Streamlit**.
- Mostra em cores os estoques (verde, amarelo, vermelho) do:
  - Almoxarifado
  - Produtos acabados
  - Estoques de cada linha

---

##  Arquitetura e Comunicação

- **Containers Docker**: cada entidade roda isoladamente.
- **Redis**: utilizado como **único backend** tanto para:
  - Armazenamento em memória de estoques e buffers
  - Comunicação assíncrona entre entidades com **Pub/Sub**
- **Justificativa**: Redis foi escolhido por simplicidade, leveza, suporte a múltiplas estruturas de dados e canais Pub/Sub integrados, dispensando o uso de outros brokers (como MQTT ou RabbitMQ).

---

## Como Executar o Projeto

### 1. Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.10+ com `pip`
- Redis rodando localmente (porta 6379)
- Dependências Python:
```bash
pip install redis streamlit
```

### 2. Inicializar os dados do Redis

```bash
python3 init_redis.py
```

### 3. Rodar os serviços com Docker

Você pode usar o `docker-compose.yml` para orquestrar todos os containers:

```bash
docker compose up --build
```

Se preferir, pode executar os scripts manualmente em terminais separados, por exemplo:

```bash
# Em terminais diferentes:

python3 supplier_redis.py
python3 warehouse_redis.py
python3 product_stock_redis.py
python3 factory_redis.py empurrada 1 5
python3 factory_redis.py puxada 2 8

# Linhas da Fábrica 1 (empurrada)
python3 line_redis.py 1 1
...
python3 line_redis.py 5 1

# Linhas da Fábrica 2 (puxada)
python3 line_redis.py 1 2
...
python3 line_redis.py 8 2
```

### 4. Rodar o Dashboard

```bash
streamlit run kanban_visualizer.py
```

Abra no navegador: [http://localhost:8501](http://localhost:8501)

---

##  Estrutura do Projeto

```
.
├── Dockerfile
├── docker-compose.yml
├── init_redis.py
├── kanban_visualizer.py
├── factory_redis.py
├── line_redis.py
├── product_stock_redis.py
├── supplier_redis.py
├── warehouse_redis.py
├── random_parts.py
├── products_and_parts.txt
└── utils.py
```

---

## Observações

- A geração dos produtos e partes está em `random_parts.py` e gera o arquivo `products_and_parts.txt`.
- Todas as operações de consumo e reabastecimento usam lógica de buffer de estoque com `check_in` e `check_out`.
- O sistema segue uma lógica cíclica simulando **dias**, onde produção e consumo são simulados automaticamente a cada ciclo.
- Os limites Kanban são definidos em constantes dentro do `utils.py`.

---

## Conclusão