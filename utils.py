# utils.py

import os

# Configurações de conexão Redis
REDIS_HOST = 'redis' # <<< O nome do serviço do Redis no docker-compose
REDIS_PORT = 6379

# Intervalo de tempo entre "dias" na simulação (em segundos)
TIME_SLEEP = 5

# --- Constantes da Simulação ---

# <<< CORREÇÃO: Renomeado de PRODUCTS_N para NUM_PRODUCTS e adicionado NUM_PARTS
NUM_PRODUCTS = 5     # O número total de versões do produto
NUM_PARTS = 100      # O número total de peças diferentes usadas

BATCH_SIZE = 48
DAYS_MAX = 20

# --- Parâmetros de Estoque e Kanban ---

# Alertas para o estoque de PEÇAS na LINHA DE PRODUÇÃO
YELLOW_ALERT_LINE = BATCH_SIZE * 6
RED_ALERT_LINE = BATCH_SIZE * 3

# Alertas para o estoque de PEÇAS no ALMOXARIFADO CENTRAL
YELLOW_ALERT_WAREHOUSE = BATCH_SIZE * 780
RED_ALERT_WAREHOUSE = BATCH_SIZE * 390

# Alerta para o estoque de PRODUTOS ACABADOS
RED_ALERT_PRODUCT_STOCK = 500

# --- Parâmetros de Reabastecimento e Pedidos ---

# Quantidade de peças que o Fornecedor envia em um lote
PARTS_TO_SEND_AMOUNT_SUPPLIER = BATCH_SIZE * 1950

# Quantidade de peças que o Almoxarifado envia para uma linha em um lote
PARTS_TO_SEND_AMOUNT_WAREHOUSE = BATCH_SIZE * 30

# Limites para os pedidos aleatórios de clientes
MIN_ORDERED_AMOUNT = 50
MAX_ORDERED_AMOUNT = 250


def list_to_string(lst):
    """Converte uma lista de números em uma string separada por ponto e vírgula."""
    return ';'.join(str(item) for item in lst)

def string_to_list(string):
    """Converte uma string separada por ponto e vírgula de volta para uma lista de inteiros."""
    return [int(item) for item in string.split(';') if item]

def print_update(msg, entity_name):
    """Imprime uma mensagem formatada no console e a salva em um arquivo de log."""
    final_msg = (
        "\n"
        "===============================================================================\n"
        f"[{entity_name.upper()}] {msg}\n"
        "===============================================================================\n"
    )
    print(final_msg)
    
    os.makedirs('output', exist_ok=True)
    with open(f'output/{entity_name}.txt', 'a', encoding='utf-8') as file:
        file.write(final_msg)