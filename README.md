# Case: API de acordos

Consumo de API pública, persistência assíncrona via mensageria e API REST de consulta.

## Stack

Python 3.13, FastAPI, SQLAlchemy, PostgreSQL, SQS (ElasticMQ local), Docker Compose.

## Como rodar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # ajuste os valores
docker compose up -d
python -m scripts.check_setup
```

## Status

Em desenvolvimento.
