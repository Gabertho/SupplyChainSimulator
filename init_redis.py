# init_redis.py

import redis
from utils import BATCH_SIZE, NUM_PRODUCTS, REDIS_HOST, REDIS_PORT

def initialize_simulation():
    """
    Limpa o banco de dados Redis e o popula com um estado inicial saudável.
    Isso evita que a simulação comece com estoques zerados e trave imediatamente.
    """
    try:
        # Conecta ao servidor Redis local
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        # Verifica a conexão
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print("ERRO: Não foi possível conectar ao Redis.")
        print(f"Por favor, certifique-se de que o servidor Redis está rodando no host '{REDIS_HOST}' e porta '{REDIS_PORT}'.")
        print(f"Detalhes do erro: {e}")
        return

    print(">>> Conexão com Redis bem-sucedida.")
    
    print(">>> Limpando o banco de dados de simulações anteriores (FLUSHDB)...")
    r.flushdb()

    # 1. Inicializar estoque de produtos acabados
    # Começa com um estoque saudável para que os primeiros pedidos dos clientes possam ser atendidos.
    print(f">>> Inicializando estoque de {NUM_PRODUCTS} produtos acabados...")
    initial_product_stock = 1000
    for i in range(NUM_PRODUCTS):
        key = f"product:{i}"
        r.set(key, initial_product_stock)
        print(f"    - Chave '{key}' criada com valor {initial_product_stock}")

    # 2. Inicializar estoque do almoxarifado (warehouse)
    # O almoxarifado precisa de um estoque robusto para poder abastecer as 13 linhas de produção.
    print(">>> Inicializando estoque de peças no Almoxarifado...")
    initial_warehouse_stock = BATCH_SIZE * 1000  # Um valor alto para garantir o início
    for i in range(100): # Total de 100 peças diferentes
        key = f"warehouse:part:{i}"
        r.set(key, initial_warehouse_stock)
    print(f"    - 100 chaves 'warehouse:part:x' criadas com valor {initial_warehouse_stock}")
    
    # NOTA: As linhas de produção podem começar com estoque zero. A lógica delas
    # fará com que peçam peças ao almoxarifado assim que iniciarem.
    
    print("\n>>> Inicialização do Redis completa! A simulação está pronta para começar.")


if __name__ == "__main__":
    initialize_simulation()