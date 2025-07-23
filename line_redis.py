# line_redis.py

import redis
import threading
import time
import sys
from utils import (
    string_to_list,
    list_to_string,
    print_update,
    TIME_SLEEP,
    DAYS_MAX,
    RED_ALERT_LINE,
    YELLOW_ALERT_LINE,
    REDIS_HOST,
    REDIS_PORT,
    NUM_PARTS,
)

BASE_KIT_SIZE = 43

class LineRedis:
    def __init__(self, line_id, factory_id, redis_client):
        self.r = redis_client
        self.line_id = str(line_id)
        self.factory_id = str(factory_id)
        self.entity_name = f'line-{self.factory_id}-{self.line_id}'
        self.is_waiting_for_parts = False
        self.products_necessary_parts = self._read_products_necessary_parts()

    def _read_products_necessary_parts(self):
        try:
            with open("products_and_parts.txt", "r") as f:
                return [string_to_list(line.strip()) for line in f.readlines()]
        except FileNotFoundError:
            print_update(f"ERRO CRÍTICO: Arquivo 'products_and_parts.txt' não encontrado!", self.entity_name)
            sys.exit(1)

    def _get_part_stock(self, part_id):
        key = f"line:{self.factory_id}:{self.line_id}:part:{part_id}"
        return int(self.r.get(key) or 0)

    def _increment_part_stock(self, part_id, qty):
        key = f"line:{self.factory_id}:{self.line_id}:part:{part_id}"
        self.r.incrby(key, qty)

    def _decrement_part_stock(self, part_id, qty):
        key = f"line:{self.factory_id}:{self.line_id}:part:{part_id}"
        self.r.decrby(key, qty)
    
    def receive_parts_from_warehouse(self, parts_received):
        print_update("Recebendo lote de peças do Almoxarifado.", self.entity_name)
        for i, amount in enumerate(parts_received):
            if amount > 0:
                self._increment_part_stock(i, amount)
        self.is_waiting_for_parts = False
        print_update("Estoque da linha reabastecido.", self.entity_name)

    def check_and_order_parts(self):
        if self.is_waiting_for_parts:
            print_update("Aguardando peças do Almoxarifado.", self.entity_name)
            return

        all_stocks = [self._get_part_stock(i) for i in range(NUM_PARTS)]
        min_stock = min(all_stocks)

        if min_stock < YELLOW_ALERT_LINE:
            print_update(f"Estoque baixo detectado (peça com menor estoque: {min_stock}). Pedindo reposição.", self.entity_name)
            
            self.is_waiting_for_parts = True
            parts_to_order_flags = [1] * NUM_PARTS
            payload = list_to_string(parts_to_order_flags)
            msg = f"{self.line_id}/{self.factory_id}/send_parts/{payload}"
            self.r.publish("channel:warehouse", msg)
        else:
            print_update(f"Status do buffer de peças: VERDE (mínimo: {min_stock}).", self.entity_name)

    def execute_production_order(self, product_idx_str, qty_str):
        product_idx = int(product_idx_str)
        qty = int(qty_str)
        print_update(f"Recebida ordem para produzir {qty} unids do produto {product_idx + 1}.", self.entity_name)

        parts_for_this_product = self.products_necessary_parts[product_idx]
        
        pipe = self.r.pipeline()
        for i in range(BASE_KIT_SIZE):
            pipe.get(f"line:{self.factory_id}:{self.line_id}:part:{i}")
        for part_id in parts_for_this_product:
            pipe.get(f"line:{self.factory_id}:{self.line_id}:part:{part_id - 1}")
        
        stocks = pipe.execute()
        
        for stock in stocks:
            if int(stock or 0) < qty:
                print_update(f"QUEBRA DE LINHA! Estoque insuficiente para lote de {qty}.", self.entity_name)
                return

        pipe = self.r.pipeline()
        for i in range(BASE_KIT_SIZE):
            pipe.decrby(f"line:{self.factory_id}:{self.line_id}:part:{i}", qty)
        for part_id in parts_for_this_product:
            pipe.decrby(f"line:{self.factory_id}:{self.line_id}:part:{part_id - 1}", qty)
        pipe.execute()

        msg = f"receive_products/{product_idx}/{self.line_id}/{self.factory_id}/{qty}"
        self.r.publish("channel:product_stock", msg)
        print_update(f"SUCESSO: Produziu {qty} unids do produto {product_idx + 1}.", self.entity_name)

    def listen(self):
        my_channel = f"channel:line:{self.factory_id}:{self.line_id}"
        pubsub = self.r.pubsub()
        pubsub.subscribe(my_channel)
        print_update(f"Ouvindo o canal exclusivo '{my_channel}'...", self.entity_name)

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = message["data"]
            parts = data.split("/")
            command = parts[0]
            
            if command == "receive_parts":
                payload = parts[1]
                parts_to_receive = string_to_list(payload)
                self.receive_parts_from_warehouse(parts_to_receive)
            
            elif command == "receive_order":
                prod_idx, qty = parts[1], parts[2]
                self.execute_production_order(prod_idx, qty)

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 line_redis.py [line_id] [factory_id]")
        sys.exit(1)

    line_id, factory_id = sys.argv[1], sys.argv[2]
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
    except redis.exceptions.ConnectionError as e:
        print(f"ERRO CRÍTICO (Linha {factory_id}-{line_id}): Não foi possível conectar ao Redis. Detalhes: {e}")
        return

    line = LineRedis(line_id, factory_id, r)
    
    listener_thread = threading.Thread(target=line.listen, daemon=True)
    listener_thread.start()
    
    # <<< CORREÇÃO CRÍTICA: Esperar pelo sinal do almoxarifado antes de começar >>>
    print_update("Aguardando sinal de prontidão do almoxarifado...", line.entity_name)
    pubsub = r.pubsub()
    pubsub.subscribe("control:warehouse_ready")
    for message in pubsub.listen():
        if message['type'] == 'message' and message['data'] == "READY":
            print_update("Sinal recebido! Iniciando ciclo de operações.", line.entity_name)
            break 
    pubsub.unsubscribe()
    # <<< FIM DA CORREÇÃO >>>

    days = 0
    while days < DAYS_MAX:
        days += 1
        line.check_and_order_parts()
        time.sleep(TIME_SLEEP)
        
    print_update("Simulação terminada.", line.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()