# supplier_redis.py

import redis
import threading
import time
from utils import (
    list_to_string,
    string_to_list,
    print_update,
    PARTS_TO_SEND_AMOUNT_SUPPLIER,
    TIME_SLEEP,
    DAYS_MAX,
    REDIS_HOST,
    REDIS_PORT
)

class SupplierRedis:

    def __init__(self, redis_client):
        self.r = redis_client
        self.entity_name = 'supplier'

    def send_parts(self, parts_ordered):
        """
        Prepara e envia um lote de peças para o almoxarifado com base no pedido recebido.
        """
        # <<< NOTA: O número total de peças diferentes é 100 (de 0 a 99)
        parts_to_send = [0] * 100
        for idx, needs_part in enumerate(parts_ordered):
            # Se a posição na lista for 1, significa que aquela peça precisa ser enviada.
            if needs_part:
                parts_to_send[idx] = PARTS_TO_SEND_AMOUNT_SUPPLIER

        # <<< NOTA: A mensagem é simples: "comando/payload"
        # O almoxarifado (warehouse) vai ouvir por "receive_parts"
        payload = list_to_string(parts_to_send)
        msg = f"receive_parts/{payload}"
        
        print_update(f"Recebeu pedido. Enviando peças para o Almoxarifado.", self.entity_name)
        self.r.publish("channel:warehouse", msg)

    def listen(self):
        """
        Ouve continuamente o canal 'channel:supplier' por novas mensagens.
        """
        pubsub = self.r.pubsub()
        pubsub.subscribe("channel:supplier")
        print_update("Ouvindo o canal 'channel:supplier' por pedidos do almoxarifado...", self.entity_name)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                payload = message['data']
                parts = payload.split("/")
                
                # O comando esperado é "send_parts" vindo do almoxarifado
                if parts[0] == "send_parts":
                    ordered_list_str = parts[1]
                    ordered_list = string_to_list(ordered_list_str)
                    self.send_parts(ordered_list)

def main():
    """
    Função principal para iniciar o processo do fornecedor.
    """
    try:
        # <<< MELHORIA: A conexão com o Redis é feita aqui e passada para a classe.
        # Isso torna o código mais limpo e fácil de testar.
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        print_update("Conexão com Redis bem-sucedida.", 'supplier-main')
    except redis.exceptions.ConnectionError as e:
        print(f"ERRO CRÍTICO: Não foi possível conectar ao Redis. Verifique se ele está rodando. Detalhes: {e}")
        return

    sup = SupplierRedis(r)
    
    # Inicia o listener em uma thread separada para não bloquear o loop principal.
    listener_thread = threading.Thread(target=sup.listen, daemon=True)
    listener_thread.start()

    # Este processo não precisa de um loop de "dias", pois ele é reativo.
    # Ele apenas fica em execução, esperando por mensagens no listener.
    print_update("Processo iniciado. Aguardando reativamente por pedidos.", sup.entity_name)
    
    # Mantém o script principal vivo para que a thread do listener não morra.
    listener_thread.join()


if __name__ == "__main__":
    main()