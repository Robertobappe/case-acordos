# Case: API de acordos

Consome uma API pública, grava os dados num banco relacional de forma **assíncrona** (via fila) e os expõe numa **API REST de consulta**.

Hierarquia: **Autor → Acordos → Documentos** (users → albums → photos da API pública).

## Como funciona

```
API pública ─► Produtor ─► Fila (SQS) ─► Consumidor ─► PostgreSQL ◄─ API de consulta
                              │
                              └─ após 3 falhas ─► DLQ
```

- **Produtor:** consulta a API pública (com timeout e retentativa com backoff) e publica uma mensagem por autor.
- **Consumidor:** valida a mensagem e grava no banco com upsert, numa transação. É idempotente.
- **API:** lê **somente do banco**, nunca da API pública.

Desenho da arquitetura AWS, justificativas e comparativos: [`docs/arquitetura.md`](docs/arquitetura.md).
Perguntas de operação e segurança: [`docs/operacao-e-seguranca.md`](docs/operacao-e-seguranca.md).

## Como executar

Requisitos: Docker com Compose.

```bash
cp .env.example .env          # ajuste os valores (API_KEY, DB_PASSWORD)
docker compose up -d --build  # banco, fila, API e consumidor
docker compose ps -a          # o serviço "init" termina com Exited (0): é o esperado
```

Disparar a carga (o consumidor processa sozinho):

```bash
docker compose run --rm producer
```

Consultar a API:

```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2-)
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/usuarios/1/acordos
```

- Documentação interativa (Swagger): http://localhost:8000/docs
- Health check: `GET /health` (liveness) e `GET /health/ready` (readiness, consulta o banco)

Zerar tudo e recomeçar: `docker compose down -v`.

## Endpoint

`GET /api/v1/usuarios/{id}/acordos` (cabeçalho `X-API-Key`)

| Status | Quando |
|---|---|
| 200 | Sucesso (inclui autor sem acordos) |
| 400 | `id` inválido |
| 401 | API Key ausente ou inválida |
| 404 | Autor não encontrado |
| 500 | Erro interno (resposta genérica, com `correlationId`) |

Todos os erros têm o mesmo formato e toda resposta traz o cabeçalho `X-Correlation-ID`.

## Testes

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v
```

Os testes não usam banco nem rede: o cliente HTTP, o serviço e as rotas são testados com dependências falsas.

## Banco de dados

- Criação das tabelas (chaves, índices): [`sql/01_schema.sql`](sql/01_schema.sql), aplicado automaticamente na criação do banco.
- Consultas relevantes: [`consultas/consultas.sql`](consultas/consultas.sql).

## Cenários de resiliência

```bash
python -m scripts.status_filas      # estado da fila e da DLQ
python -m scripts.inspecionar_dlq   # o que há na DLQ (só ids, sem expor dados pessoais)
python -m scripts.reprocessar_dlq   # devolve a DLQ à fila principal
```

Passo a passo da demonstração (retentativa, mensagem na DLQ e reprocessamento) em
[`docs/operacao-e-seguranca.md`](docs/operacao-e-seguranca.md). Os scripts rodam no
ambiente Python local, com o `docker compose` ativo.

## Estrutura

```
app/
  api/            controllers, dependências, erros centralizados e fábrica da aplicação
  clients/        cliente da API pública (retry e backoff)
  contracts.py    contrato das mensagens da fila
  mapping.py      de-para API pública → contrato
  producer.py     produtor
  consumer*.py    worker (fila) e serviço (regra de gravação)
  repository.py   gravação idempotente (upsert)
  query_repository.py, acordo_service.py   consulta da API
sql/              criação das tabelas
consultas/        consultas SQL e dados de teste
scripts/          utilitários de operação e demonstração
tests/            testes unitários
```

## Decisões principais

- **Idempotência** por chave primária vinda da origem e `INSERT ... ON CONFLICT DO UPDATE`.
- **Apaga da fila só depois do commit**; a DLQ é gerenciada pela fila (`maxReceiveCount = 3`).
- **Sem dados pessoais em logs**: só ids, contagens e tipo de erro.
- **ElasticMQ** no lugar do LocalStack: as versões recentes do LocalStack exigem token. O código usa `boto3` com `endpoint_url` configurável, então em produção só muda o endpoint.

## Uso de IA
Sim, foi usado para o desenvolvimento o claude code. A escolha foi além de acelerar o desenvolvimento como também para revisão de código, geração de testes e validação de testes.

## Próximos passos

CI com GitHub Actions, paginação dos documentos, JWT, mascaramento de dados pessoais, métricas, infraestrutura como código e migrações de banco.
