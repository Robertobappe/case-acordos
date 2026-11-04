#!/usr/bin/env bash
ok()    { echo "[OK]     $1"; }
falha() { echo "[FALHA]  $1"; }

[ -n "$VIRTUAL_ENV" ] && ok "venv ativo" || falha "source .venv/bin/activate"
python -c "import fastapi, sqlalchemy, boto3, httpx, pydantic_settings, psycopg2" 2>/dev/null && ok "dependências" || falha "pip install -r requirements.txt"
[ -z "$(env | grep '^AWS_ENDPOINT_URL=')" ] && ok "sem AWS_ENDPOINT_URL sobrescrevendo o .env" || falha "unset AWS_ENDPOINT_URL"
docker ps > /dev/null 2>&1 && ok "docker sem sudo" || falha "docker inacessível"
[ "$(docker inspect -f '{{.State.Health.Status}}' acordos-postgres 2>/dev/null)" = "healthy" ] && ok "postgres healthy" || falha "docker compose up -d"
[ -n "$(docker ps --filter name=acordos-sqs --filter status=running -q)" ] && ok "sqs rodando" || falha "docker compose up -d"
python -m scripts.check_setup
