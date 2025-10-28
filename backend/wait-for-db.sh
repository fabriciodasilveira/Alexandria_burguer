#!/bin/bash
# wait-for-db.sh

set -e

host="$1"
shift
cmd="$@"

echo "Waiting for PostgreSQL to start..."

# Loop para verificar a conexão com o PostgreSQL e a existência das tabelas
# O comando \q tenta conectar e sair imediatamente.
until PGPASSWORD="password" psql -h "$host" -U "user" -d "restaurante_13mesas" -c '\dt tables'; do
  >&2 echo "Postgres is unavailable or tables not created - sleeping"
  sleep 1
done

>&2 echo "Postgres is up and tables are created - executing command"
exec $cmd
