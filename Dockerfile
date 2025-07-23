# Usar uma imagem oficial do Python como base. A versão 'slim' é mais leve.
FROM python:3.11-slim

# Definir o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copiar o arquivo de dependências para o contêiner.
COPY requirements.txt .

# Instalar as dependências do projeto.
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código do projeto para o diretório de trabalho do contêiner.
COPY . .

# Comando padrão (pode ser sobrescrito pelo docker-compose).
CMD ["python"]