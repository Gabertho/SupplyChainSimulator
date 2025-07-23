# factory_redis.py (Versão Final com Lógica de Atribuição Corrigida)

import redis
import threading
import sys
import time
from utils import (
    string_to_list,
    print_update,
    BATCH_SIZE,
    TIME_SLEEP,
    DAYS_MAX,
    RED_ALERT_PRODUCT_STOCK,
    NUM_PRODUCTS,
    REDIS_HOST,
    REDIS_PORT
)

class FactoryRedis:

    def __init__(self, fabric_type, factory_id, lines_number, redis_client):
        self.r = redis_client
        self.fabric_type = fabric_type
        self.factory_id = str(factory_id)
        self.lines_number = lines_number
        self.entity_name = f'factory-{self.factory_id}-{self.fabric_type}'
        self.last_stock_status = 'green'
        # <<< MUDANÇA: Armazena o buffer de estoque mais recente
        self.last_stock_buffer = [0] * NUM_PRODUCTS

    def update_finished_goods_stock(self, stock_buffer):
        print_update(f"Recebeu atualização do estoque de produtos: {stock_buffer}", self.entity_name)
        self.last_stock_buffer = stock_buffer # Armazena o buffer para uso posterior
        
        total_stock = sum(stock_buffer)
        if total_stock <= RED_ALERT_PRODUCT_STOCK * self.lines_number:
            self.last_stock_status = 'red'
        elif total_stock <= RED_ALERT_PRODUCT_STOCK * self.lines_number * 2:
            self.last_stock_status = 'yellow'
        else:
            self.last_stock_status = 'green'
        print_update(f"Status do estoque de produtos definido como: {self.last_stock_status.upper()}", self.entity_name)

    def order_daily_batch(self):
        lot_size = BATCH_SIZE
        if self.fabric_type == 'puxada':
            if self.last_stock_status == 'green':
                lot_size = BATCH_SIZE // 2
            elif self.last_stock_status == 'red':
                lot_size = BATCH_SIZE * 2
        
        print_update(f"Iniciando ordens de produção do dia com tamanho de lote = {lot_size}", self.entity_name)

        # <<< LÓGICA DE ATRIBUIÇÃO CORRIGIDA E SIMPLIFICADA >>>
        
        # Cria uma lista de produtos ordenados do menor para o maior estoque.
        # Ex: [(1, 546), (2, 685), (3, 743), (0, 767), (4, 890)]
        # Onde o primeiro elemento é o índice do produto e o segundo é o estoque.
        sorted_products_by_stock = sorted(enumerate(self.last_stock_buffer), key=lambda x: x[1])
        
        for line_idx in range(self.lines_number):
            if self.fabric_type == 'empurrada':
                # Fábrica empurrada: cada linha tem seu produto fixo. Linha 1 -> P1, Linha 2 -> P2...
                product_to_produce_idx = line_idx % NUM_PRODUCTS
            else: # Fábrica puxada
                # Fábrica puxada: distribui a produção com base na necessidade (menor estoque).
                # A linha 1 produz o de menor estoque, a linha 2 o segundo menor, etc.
                # O operador de módulo (%) garante que a gente recomece a lista se tiver mais linhas que produtos.
                product_to_produce_idx = sorted_products_by_stock[line_idx % len(sorted_products_by_stock)][0]
            
            self.order_to_line(line_idx, lot_size, product_to_produce_idx)
    
    def order_to_line(self, line_index, size, product_index):
        line_id_for_msg = line_index + 1
        target_channel = f"channel:line:{self.factory_id}:{line_id_for_msg}"
        msg = f"receive_order/{product_index}/{size}"
        
        print_update(f"Enviando Ordem para o canal {target_channel} -> Produto: {product_index + 1}, Qtd: {size}", self.entity_name)
        self.r.publish(target_channel, msg)

    def listen(self):
        pubsub = self.r.pubsub()
        pubsub.subscribe("channel:factory")
        print_update("Ouvindo o canal 'channel:factory' por atualizações de estoque...", self.entity_name)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                parts = message['data'].split("/")
                if parts[0] == "update_factory":
                    buffer = string_to_list(parts[1])
                    self.update_finished_goods_stock(buffer)

def main():
    if len(sys.argv) != 4:
        print("Uso: python3 factory_redis.py [empurrada|puxada] [factory_id] [lines_number]")
        sys.exit(1)

    fabric_type, factory_id, lines_n = sys.argv[1], sys.argv[2], int(sys.argv[3])
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"ERRO CRÍTICO (Fábrica {factory_id}): Não foi possível conectar ao Redis. Detalhes: {e}")
        return

    fac = FactoryRedis(fabric_type, factory_id, lines_n, r)
    
    listener_thread = threading.Thread(target=fac.listen, daemon=True)
    listener_thread.start()

    days = 0
    while days < DAYS_MAX:
        days += 1
        print_update(f"--- Dia {days} ---", fac.entity_name)
        fac.order_daily_batch()
        time.sleep(TIME_SLEEP)
        
    print_update("Simulação terminada.", fac.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()