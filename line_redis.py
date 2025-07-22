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
    NUM_PRODUCTS
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
            return

        parts_to_order_flags = [0] * NUM_PARTS
        status = "GREEN"
        
        for i in range(NUM_PARTS):
            stock = self._get_part_stock(i)
            if stock < RED_ALERT_LINE:
                status = "RED"
                parts_to_order_flags[i] = 1
            elif stock < YELLOW_ALERT_LINE and status != "RED":
                status = "YELLOW"
                parts_to_order_flags[i] = 1
        
        print_update(f"Status do buffer de peças: {status}", self.entity_name)

        if any(parts_to_order_flags):
            self.is_waiting_for_parts = True
            payload = list_to_string(parts_to_order_flags)
            msg = f"{self.line_id}/{self.factory_id}/send_parts/{payload}"
            
            # <<< PASSO DE DEBUG: Adicionamos este print para confirmar o envio >>>
            print_update(f"!!! ENVIANDO MENSAGEM para 'channel:warehouse': {msg}", self.entity_name)
            self.r.publish("channel:warehouse", msg)

    def execute_production_order(self, product_idx_str, qty_str):
        product_idx = int(product_idx_str)
        qty = int(qty_str)
        print_update(f"Recebida ordem de produção para {qty} unids do produto {product_idx + 1}.", self.entity_name)

        parts_for_this_product = self.products_necessary_parts[product_idx]
        
        for i in range(BASE_KIT_SIZE):
            if self._get_part_stock(i) < qty:
                print_update(f"QUEBRA DE LINHA! Faltam peças do KIT BASE (Peça {i}) para produzir {qty} unids.", self.entity_name)
                return
        for part_id in parts_for_this_product:
            if self._get_part_stock(part_id - 1) < qty:
                print_update(f"QUEBRA DE LINHA! Faltam peças do KIT VARIAÇÃO (Peça {part_id}) para produzir {qty} unids.", self.entity_name)
                return

        for i in range(BASE_KIT_SIZE):
            self._decrement_part_stock(i, qty)
        for part_id in parts_for_this_product:
            self._decrement_part_stock(part_id - 1, qty)

        msg = f"receive_products/{product_idx}/{self.line_id}/{self.factory_id}/{qty}"
        self.r.publish("channel:product_stock", msg)
        print_update(f"SUCESSO: Produziu {qty} unids do produto {product_idx + 1}. Notificando estoque.", self.entity_name)

    def listen(self):
        pubsub = self.r.pubsub()
        pubsub.subscribe("channel:line")
        print_update(f"Ouvindo o canal 'channel:line'...", self.entity_name)

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            data = message["data"]
            parts = data.split("/")
            command = parts[0]
            
            if command == "receive_parts":
                msg_line_id, msg_factory_id = parts[1], parts[2]
                if msg_line_id == self.line_id and msg_factory_id == self.factory_id:
                    payload = parts[3]
                    parts_to_receive = string_to_list(payload)
                    self.receive_parts_from_warehouse(parts_to_receive)
            
            elif command == "receive_order":
                msg_line_id, msg_factory_id = parts[1], parts[2]
                if msg_line_id == self.line_id and msg_factory_id == self.factory_id:
                    prod_idx, qty = parts[3], parts[4]
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

    days = 0
    while days < DAYS_MAX:
        days += 1
        print_update(f"--- Dia {days} ---", line.entity_name)
        line.check_and_order_parts()
        time.sleep(TIME_SLEEP)
        
    print_update("Simulação terminada.", line.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()