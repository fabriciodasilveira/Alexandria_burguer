# Dockerfile para o Backend (Python/FastAPI)
FROM python:3.11-slim

WORKDIR /app

# Instalação de dependências
COPY requirements.txt .
# Adiciona o cliente PostgreSQL para o script de espera
RUN apt-get update && apt-get install -y postgresql-client && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Copia o código da aplicação e o script de espera
COPY . .

# Torna o script executável
RUN chmod +x /app/wait-for-db.sh

# Usa o script como ENTRYPOINT para garantir que o DB esteja pronto antes de iniciar o uvicorn
ENTRYPOINT ["/app/wait-for-db.sh", "database"]

# Comando para rodar a aplicação
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
