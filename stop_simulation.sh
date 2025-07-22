#!/bin/bash

# Script para parar todos os processos relacionados à simulação.

echo "================================================="
echo "🛑 ENCERRANDO SIMULAÇÃO DE PRODUÇÃO 🛑"
echo "================================================="

# O comando 'pkill' encontra processos pelo nome ou parte do comando.
# A flag '-f' faz com que ele procure em toda a linha de comando.
# Isso é mais robusto do que matar por 'python', pois pode haver outros
# scripts python não relacionados rodando na sua máquina.

echo "Parando o processo do Streamlit (kanban_visualizer)..."
pkill -f "streamlit run kanban_visualizer.py"

echo "Parando todos os processos da simulação (*_redis.py)..."
pkill -f "_redis.py"

sleep 1
echo "✅ Todos os processos da simulação foram encerrados."
echo "================================================="