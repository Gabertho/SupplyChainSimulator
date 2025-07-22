# warehouse_redis.py

import redis
import threading
import time
from utils import (
    list_to_string,
    string_to_list,
    print_update,
    PARTS_TO_SEND_AMOUNT_WAREHOUSE,
    TIME_SLEEP,
    DAYS_MAX,
    RED_ALERT_WAREHOUSE,
    YELLOW_ALERT_WAREHOUSE,
    REDIS_HOST,
    REDIS_PORT,
    NUM_PARTS
)

class WarehouseRedis:

    def __init__(self, redis_client):
        self.r = redis_client
        self.entity_name = 'warehouse'
        self.waiting_for_supplier_order = False

    def receive_parts(self, parts_received):
        print_update(f"Recebendo lote de peças do fornecedor.", self.entity_name)
        for i, amount in enumerate(parts_received):
            if amount > 0:
                self.r.incrby(f"warehouse:part:{i}", amount)
        self.waiting_for_supplier_order = False
        print_update("Estoque do almoxarifado reabastecido.", self.entity_name)

    def send_parts(self, line_id, factory_id, parts_ordered_flags):
        to_send = [0] * NUM_PARTS
        
        for i, needs_part in enumerate(parts_ordered_flags):
            if needs_part:
                stock = int(self.r.get(f"warehouse:part:{i}") or 0)
                if stock < PARTS_TO_SEND_AMOUNT_WAREHOUSE:
                    print_update(f"QUEBRA DE ESTOQUE! Não há peças '{i}' suficientes para a linha {factory_id}-{line_id}.", self.entity_name)
                    return 
                to_send[i] = PARTS_TO_SEND_AMOUNT_WAREHOUSE

        for i, amount_to_send in enumerate(to_send):
            if amount_to_send > 0:
                self.r.decrby(f"warehouse:part:{i}", amount_to_send)

        payload = list_to_string(to_send)
        msg = f"receive_parts/{line_id}/{factory_id}/{payload}"
        
        print_update(f"Enviando lote de peças para a linha {factory_id}-{line_id}.", self.entity_name)
        self.r.publish("channel:line", msg)

    def check_and_order_parts_from_supplier(self):
        if self.waiting_for_supplier_order:
            return

        parts_to_order = [0] * NUM_PARTS
        is_alert = False
        
        for i in range(NUM_PARTS):
            stock = int(self.r.get(f"warehouse:part:{i}") or 0)
            if stock < RED_ALERT_WAREHOUSE:
                parts_to_order[i] = 1
                is_alert = True
            elif stock < YELLOW_ALERT_WAREHOUSE:
                parts_to_order[i] = 1
                is_alert = True

        if is_alert:
            self.waiting_for_supplier_order = True
            payload = list_to_string(parts_to_order)
            msg = f"send_parts/{payload}"
            
            print_update("Nível de estoque baixo. Enviando pedido para o Fornecedor.", self.entity_name)
            self.r.publish("channel:supplier", msg)
        else:
            print_update("Nível de estoque: VERDE.", self.entity_name)

    def listen(self):
        """Ouve o canal 'channel:warehouse' e LOGA TUDO para depuração."""
        pubsub = self.r.pubsub()
        pubsub.subscribe("channel:warehouse")
        print_update("Ouvindo o canal 'channel:warehouse'...", self.entity_name)
        
        for message in pubsub.listen():
            # <<< PASSO DE DEBUG: Logar toda e qualquer mensagem que chegar >>>
            print_update(f"!!! MENSAGEM RECEBIDA: {message}", self.entity_name)
            
            if message['type'] != 'message':
                continue
            
            data = message['data']
            parts = data.split("/")
            
            # Mensagem do Fornecedor: "receive_parts/payload"
            if parts[0] == "receive_parts":
                print_update(">>> Mensagem identificada como do FORNECEDOR.", self.entity_name)
                payload = parts[1]
                rec = string_to_list(payload)
                self.receive_parts(rec)
            
            # Mensagem da Linha: "line_id/factory_id/send_parts/payload"
            elif len(parts) > 2 and parts[2] == "send_parts":
                print_update(">>> Mensagem identificada como da LINHA.", self.entity_name)
                line_id = parts[0]
                factory_id = parts[1]
                payload = parts[3]
                parts_to_order_flags = string_to_list(payload)
                self.send_parts(line_id, factory_id, parts_to_order_flags)
            else:
                # <<< PASSO DE DEBUG: Logar se uma mensagem não for reconhecida >>>
                print_update(f"XXX MENSAGEM NÃO RECONHECIDA: {data}", self.entity_name)

def main():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print_update("Conexão com Redis bem-sucedida.", 'warehouse-main')
    except redis.exceptions.ConnectionError as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao Redis. Detalhes: {e}")
        return

    wh = WarehouseRedis(r)
    
    listener_thread = threading.Thread(target=wh.listen, daemon=True)
    listener_thread.start()

    days = 0
    while days < DAYS_MAX:
        days += 1
        print_update(f"--- Dia {days} ---", wh.entity_name)
        wh.check_and_order_parts_from_supplier()
        time.sleep(TIME_SLEEP)
        
    print_update("Simulação terminada.", wh.entity_name)
    listener_thread.join()

if __name__ == "__main__":
    main()