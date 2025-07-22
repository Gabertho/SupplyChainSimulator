# product_stock_redis.py

import redis
import threading
import time
import random
from utils import (
    list_to_string,
    print_update,
    TIME_SLEEP,
    DAYS_MAX,
    RED_ALERT_PRODUCT_STOCK,
    MIN_ORDERED_AMOUNT,
    MAX_ORDERED_AMOUNT,
    NUM_PRODUCTS,
    REDIS_HOST,
    REDIS_PORT
)

class ProductStockRedis:

    def __init__(self, redis_client):
        self.r = redis_client
        self.entity_name = 'product-stock'

    def receive_products(self, product_index_str, line_id, factory_id, qty_str):
        """Recebe um lote de produtos acabados de uma linha de produção e o adiciona ao estoque."""
        product_index = int(product_index_str)
        qty = int(qty_str)
        
        key = f"product:{product_index}"
        self.r.incrby(key, qty)
        
        print_update(f"Recebeu {qty} unids do produto {product_index + 1} da linha {factory_id}-{line_id}.", self.entity_name)

    def simulate_daily_customer_orders(self):
        """
        Simula a demanda do mercado gerando pedidos aleatórios para cada produto
        e os decrementando do estoque. Em seguida, publica o novo status para as fábricas.
        """
        print_update("Simulando pedidos de clientes para o dia...", self.entity_name)
        
        sent_orders = [0] * NUM_PRODUCTS
        for i in range(NUM_PRODUCTS):
            # Gera uma quantidade de pedido aleatória
            order_amount = random.randint(MIN_ORDERED_AMOUNT, MAX_ORDERED_AMOUNT)
            key = f"product:{i}"
            
            # Pega o estoque atual do Redis
            current_stock = int(self.r.get(key) or 0)
            
            # Verifica se há estoque suficiente para atender ao pedido
            if current_stock < order_amount:
                print_update(f"FALHA DE VENDA: Pedido de {order_amount} unids para o produto {i + 1} falhou. Estoque: {current_stock}", self.entity_name)
            else:
                self.r.decrby(key, order_amount)
                sent_orders[i] = order_amount
                print_update(f"VENDA: Pedido de {order_amount} unids para o produto {i + 1} atendido com sucesso.", self.entity_name)

        # Após simular todas as vendas, informa às fábricas o novo status do estoque.
        self.publish_stock_status_to_factories()
        
    def publish_stock_status_to_factories(self):
        """Lê o estado atual do estoque de todos os produtos e publica para as fábricas."""
        # Monta uma lista com o estoque atual de cada produto.
        current_stock_buffer = [int(self.r.get(f"product:{i}") or 0) for i in range(NUM_PRODUCTS)]
        
        # Formata a mensagem e publica no canal da fábrica.
        payload = list_to_string(current_stock_buffer)
        msg = f"update_factory/{payload}"
        
        self.r.publish("channel:factory", msg)
        print_update(f"Enviando atualização de estoque para fábricas: {current_stock_buffer}", self.entity_name)


    def listen(self):
        """Ouve o canal 'channel:product_stock' por notificações de novas produções."""
        pubsub = self.r.pubsub()
        pubsub.subscribe("channel:product_stock")
        print_update("Ouvindo o canal 'channel:product_stock' por novos produtos...", self.entity_name)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                parts = message['data'].split("/")
                # Formato esperado: "receive_products/{product_idx}/{line_id}/{factory_id}/{qty}"
                if parts[0] == "receive_products":
                    self.receive_products(parts[1], parts[2], parts[3], parts[4])

def main():
    """Função principal para iniciar o processo de estoque de produtos."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print_update("Conexão com Redis bem-sucedida.", 'product-stock-main')
    except redis.exceptions.ConnectionError as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao Redis. Detalhes: {e}")
        return

    ps = ProductStockRedis(r)
    
    listener_thread = threading.Thread(target=ps.listen, daemon=True)
    listener_thread.start()

    # Loop principal que simula a passagem dos "dias".
    days = 0
    while days < DAYS_MAX:
        days += 1
        print_update(f"--- Dia {days} ---", ps.entity_name)
        
        # A cada "dia", o sistema simula as vendas e atualiza as fábricas.
        ps.simulate_daily_customer_orders()
        
        time.sleep(TIME_SLEEP)

    print_update("Simulação terminada.", ps.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()