#!/bin/bash

# Script para iniciar o sistema completo de simulação de produção.

echo "================================================="
echo "🚀 INICIANDO SIMULAÇÃO DE PRODUÇÃO 🚀"
echo "================================================="

# PASSO 1: Preparar o ambiente
# Garante que o arquivo de peças de variação exista antes de tudo.
echo "[PREPARAÇÃO] Gerando o arquivo 'products_and_parts.txt'..."
python3 random_parts.py

# PASSO 2: Inicializar o banco de dados
# Este script precisa rodar e terminar ANTES de todos os outros.
echo "[INIT] Limpando e populando o banco de dados Redis..."
python3 init_redis.py
echo "-------------------------------------------------"

# PASSO 3: Iniciar os processos de back-end em segundo plano
# O '&' no final de cada comando faz com que ele rode em background.

echo "[START] Iniciando Fornecedor (Supplier)..."
python3 supplier_redis.py &

echo "[START] Iniciando Almoxarifado (Warehouse)..."
python3 warehouse_redis.py &

echo "[START] Iniciando Estoque de Produtos Acabados..."
python3 product_stock_redis.py &

echo "[START] Iniciando Fábrica 1 (Empurrada)..."
python3 factory_redis.py empurrada 1 5 &

echo "[START] Iniciando Fábrica 2 (Puxada)..."
python3 factory_redis.py puxada 2 8 &

# Inicia as 5 linhas da Fábrica 1
echo "[START] Iniciando 5 linhas da Fábrica 1..."
for i in {1..5}
do
   python3 line_redis.py $i 1 &
done

# Inicia as 8 linhas da Fábrica 2
echo "[START] Iniciando 8 linhas da Fábrica 2..."
for i in {1..8}
do
   python3 line_redis.py $i 2 &
done

echo "-------------------------------------------------"
echo "✅ Todos os processos de back-end foram iniciados."
echo "⏳ Aguarde um instante para a inicialização completa..."
sleep 3

# PASSO 4: Iniciar a interface visual (Dashboard)
# Este é o único processo que roda em primeiro plano.
echo "[UI] Iniciando o Dashboard do Streamlit..."
echo "Pressione Ctrl+C neste terminal para encerrar o dashboard."
echo "Use o script './stop_simulation.sh' para parar TODOS os processos."

streamlit run kanban_visualizer.py