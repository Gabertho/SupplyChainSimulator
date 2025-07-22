# kanban_visualizer.py

import streamlit as st
import redis
from utils import (
    REDIS_HOST,
    REDIS_PORT,
    RED_ALERT_LINE,
    YELLOW_ALERT_LINE,
    RED_ALERT_WAREHOUSE,
    YELLOW_ALERT_WAREHOUSE,
    RED_ALERT_PRODUCT_STOCK,
    NUM_PARTS,
    NUM_PRODUCTS
)

# --- Configurações da Página do Streamlit ---
st.set_page_config(
    page_title="Dashboard de Produção",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Funções Auxiliares ---

def connect_to_redis():
    """Tenta conectar ao Redis e retorna o cliente ou None se falhar."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        return r
    except redis.exceptions.ConnectionError:
        st.error(f"**Erro de Conexão:** Não foi possível conectar ao servidor Redis em `{REDIS_HOST}:{REDIS_PORT}`. Verifique se o Redis está rodando e se os outros scripts estão ativos.", icon="🚨")
        return None

def get_kanban_color_and_symbol(value, red_limit, yellow_limit):
    """Retorna um símbolo e cor com base nos limites do Kanban."""
    if value < red_limit:
        return "🟥", "red"
    if value < yellow_limit:
        return "🟨", "orange"
    return "🟩", "green"

def display_stock_grid(title, data_dict, red_limit, yellow_limit, items_per_row=10):
    """Exibe um grid de métricas de estoque com cores Kanban."""
    st.subheader(title)
    
    # Organiza os itens em colunas para uma visualização em grid
    cols = st.columns(items_per_row)
    
    # Itera sobre o dicionário de itens (ex: {id_da_peca: quantidade})
    for i, (item_id, qty) in enumerate(data_dict.items()):
        symbol, color = get_kanban_color_and_symbol(qty, red_limit, yellow_limit)
        
        # Coloca cada métrica em uma coluna do grid
        with cols[i % items_per_row]:
            # Usa st.metric para um visual mais limpo
            st.metric(
                label=f"{symbol} {item_id}",
                value=qty
            )

# --- Lógica Principal da Interface ---

st.title("📊 Dashboard Kanban de Produção em Tempo Real")
st.markdown("Este painel atualiza automaticamente a cada 2 segundos.")

# Conecta ao Redis. Se falhar, exibe o erro e para a execução.
r = connect_to_redis()

if r:
    # Auto-reload a cada 2 segundos se a conexão for bem-sucedida
    st.markdown('<meta http-equiv="refresh" content="2">', unsafe_allow_html=True)

    # --- Estoque do Almoxarifado Central ---
    st.markdown("---")
    warehouse_keys = [f"warehouse:part:{i}" for i in range(NUM_PARTS)]
    warehouse_values = r.mget(warehouse_keys)
    warehouse_stock = {f"Peça {i+1}": int(v or 0) for i, v in enumerate(warehouse_values)}
    display_stock_grid("Estoque do Almoxarifado Central", warehouse_stock, RED_ALERT_WAREHOUSE, YELLOW_ALERT_WAREHOUSE, items_per_row=10)

    # --- Estoque de Produtos Acabados ---
    st.markdown("---")
    product_keys = [f"product:{i}" for i in range(NUM_PRODUCTS)]
    product_values = r.mget(product_keys)
    product_stock = {f"Produto {i+1}": int(v or 0) for i, v in enumerate(product_values)}
    display_stock_grid("Estoque de Produtos Acabados", product_stock, RED_ALERT_PRODUCT_STOCK, RED_ALERT_PRODUCT_STOCK * 2, items_per_row=5)

    # --- Estoque das Linhas de Produção ---
    st.markdown("---")
    st.subheader("Estoque de Peças nas Linhas de Produção")
    
    # Abas para cada fábrica para melhor organização
    f1_tab, f2_tab = st.tabs(["Fábrica 1 (Empurrada)", "Fábrica 2 (Puxada)"])

    with f1_tab:
        for line_id in range(1, 6): # Linhas 1 a 5
            line_keys = [f"line:1:{line_id}:part:{i}" for i in range(NUM_PARTS)]
            line_values = r.mget(line_keys)
            line_stock = {f"Peça {i+1}": int(v or 0) for i, v in enumerate(line_values)}
            display_stock_grid(f"Fábrica 1 • Linha {line_id}", line_stock, RED_ALERT_LINE, YELLOW_ALERT_LINE, items_per_row=10)
            
    with f2_tab:
        for line_id in range(1, 9): # Linhas 1 a 8
            line_keys = [f"line:2:{line_id}:part:{i}" for i in range(NUM_PARTS)]
            line_values = r.mget(line_keys)
            line_stock = {f"Peça {i+1}": int(v or 0) for i, v in enumerate(line_values)}
            display_stock_grid(f"Fábrica 2 • Linha {line_id}", line_stock, RED_ALERT_LINE, YELLOW_ALERT_LINE, items_per_row=10)