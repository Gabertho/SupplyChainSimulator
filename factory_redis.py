# factory_redis.py

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
        
        # <<< CORREÇÃO: Inicializa o status para evitar erro na primeira execução.
        self.last_stock_status = 'green'
        
        # Lista que guarda os produtos mais necessários (usado pela fábrica 'puxada').
        self.products_most_needed = []

    def update_finished_goods_stock(self, stock_buffer):
        """Atualiza o status do estoque com base nos dados recebidos do depósito de produtos."""
        print_update(f"Recebeu atualização do estoque de produtos: {stock_buffer}", self.entity_name)
        
        total_stock = sum(stock_buffer)
        # Define o status geral do estoque (Kanban de produtos acabados)
        if total_stock <= RED_ALERT_PRODUCT_STOCK * self.lines_number:
            self.last_stock_status = 'red'
        elif total_stock <= RED_ALERT_PRODUCT_STOCK * self.lines_number * 2:
            self.last_stock_status = 'yellow'
        else:
            self.last_stock_status = 'green'
        print_update(f"Status do estoque de produtos definido como: {self.last_stock_status.upper()}", self.entity_name)

        # Determina os produtos mais necessários para as linhas de produção excedentes
        # (relevante para a Fábrica 2, que tem mais linhas do que produtos base)
        if self.lines_number > NUM_PRODUCTS:
            # Cria uma lista de tuplas (índice, valor) para facilitar a ordenação
            indexed_stock = list(enumerate(stock_buffer))
            # Ordena a lista com base no valor do estoque (do menor para o maior)
            indexed_stock.sort(key=lambda x: x[1])
            # Pega os índices dos produtos com menor estoque
            self.products_most_needed = [item[0] for item in indexed_stock]
            print_update(f"Ordem de prioridade de produção (do mais necessário para o menos): {self.products_most_needed}", self.entity_name)

    def order_daily_batch(self):
        """Calcula o tamanho do lote para o dia e envia as ordens de produção para as linhas."""
        # Se for fabricação 'empurrada', o lote é sempre o mesmo (60, no seu caso).
        if self.fabric_type == 'empurrada':
            lot_size = BATCH_SIZE
        # Se for 'puxada', o lote varia com a demanda (status do estoque).
        else:
            if self.last_stock_status == 'green':
                lot_size = BATCH_SIZE // 2  # Produz menos se o estoque está alto
            elif self.last_stock_status == 'yellow':
                lot_size = BATCH_SIZE      # Produção normal
            else: # 'red'
                lot_size = BATCH_SIZE * 2  # Produz o dobro se o estoque está baixo
        
        print_update(f"Iniciando ordens de produção do dia com tamanho de lote = {lot_size}", self.entity_name)

        # Envia ordens para todas as suas linhas
        for line_idx in range(self.lines_number):
            # As primeiras linhas (0 a 4) produzem os produtos base (P1 a P5)
            if line_idx < NUM_PRODUCTS:
                product_to_produce = line_idx
            # As linhas excedentes produzem os produtos mais necessários no momento
            else:
                if self.products_most_needed:
                    # Pega o produto mais necessário da lista de prioridades
                    product_to_produce = self.products_most_needed[line_idx - NUM_PRODUCTS]
                else:
                    # Caso fallback, se a lista estiver vazia, apenas produz P1
                    product_to_produce = 0
            
            self.order_to_line(line_idx, lot_size, product_to_produce)
    
    def order_to_line(self, line_index, size, product_index):
        """Formata e publica a mensagem de ordem de produção para uma linha específica."""
        # <<< NOTA: O ID da linha no sistema vai de 1 em diante, mas nosso loop é 0-indexed.
        # A linha que recebe a mensagem usa o ID que foi passado na sua inicialização.
        line_id_for_msg = line_index + 1
        
        # Formato que a linha espera: "comando/id_linha/id_fabrica/id_produto/quantidade"
        msg = f"receive_order/{line_id_for_msg}/{self.factory_id}/{product_index}/{size}"
        
        print_update(f"Enviando Ordem -> Linha: {line_id_for_msg}, Produto: {product_index + 1}, Qtd: {size}", self.entity_name)
        self.r.publish("channel:line", msg)

    def listen(self):
        """Ouve o canal 'channel:factory' por atualizações do estoque de produtos."""
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
        # <<< CORREÇÃO: O batch_size foi removido dos argumentos, pois é definido no utils.py
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

    # Loop diário para enviar ordens de produção
    days = 0
    while days < DAYS_MAX:
        days += 1
        print_update(f"--- Dia {days} ---", fac.entity_name)
        # A fábrica só envia ordens depois de receber a primeira atualização de estoque
        if fac.last_stock_status:
             fac.order_daily_batch()
        else:
             print_update("Aguardando primeira atualização de estoque para iniciar produção.", fac.entity_name)
        
        time.sleep(TIME_SLEEP)
        
    print_update("Simulação terminada.", fac.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()