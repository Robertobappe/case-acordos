# Operação e segurança (Parte 4)

## 1. Se a carga falhar no meio, como saber e como reprocessar?

**Como saber.** Cada carga tem um `correlation_id` e registra `carga_iniciada` e
`carga_finalizada`. Uma carga que começou e não terminou é o sinal. Em produção:
alarme para a ausência de `carga_finalizada` no período esperado, alarme para
mensagens na DLQ e *on-failure destination* na Lambda produtora. O fim da carga
informa o total de falhas e o processo sai com código diferente de zero.

**Como reprocessar.**

- Falhou antes de publicar tudo: executar o produtor de novo. O consumidor é
  idempotente (upsert), então repetir não duplica.
- Mensagens esgotaram as tentativas: estão preservadas na DLQ. Corrigida a causa,
  `scripts/reprocessar_dlq.py` devolve as mensagens à fila principal (só apaga da
  DLQ depois de reenviar). Mensagens fora do contrato voltam para a DLQ: reprocessar
  só resolve falhas transitórias.

**Observação verificada em teste.** Com o banco fora do ar durante as três
tentativas, as mensagens foram para a DLQ e a tabela `carga_erro` não registrou
nada, porque ela fica no mesmo banco indisponível. A DLQ é a rede de segurança; a
tabela de erros é um complemento.

## 2. Três métricas ou alertas

| Métrica | Alerta | Por quê |
|---|---|---|
| Mensagens visíveis na DLQ | Maior que 0 | Sinal direto de dado fora do fluxo normal, que exige uma pessoa |
| Idade da mensagem mais antiga na fila | Acima de um limite (ex.: 10 min) | Consumidor parado ou lento, antes de a DLQ encher |
| Taxa de erro 5xx e latência p95 da API | Taxa acima de 1% ou p95 acima do combinado | É o que o usuário final sente; a p95 mostra a cauda que a média esconde |

Critério: uma métrica de perda de dados, uma de atraso e uma de experiência do usuário.
Complemento: alarme de ausência de `carga_finalizada`.

## 3. Cuidados com os dados pessoais

| Camada | Cuidado | Situação |
|---|---|---|
| Logs | Nunca registrar corpo de mensagem nem valores; só ids, contagens e tipo de erro | Implementado e coberto por teste |
| `carga_erro` | Apenas metadados, sem o corpo | Implementado |
| Resposta da API | Devolver só o necessário, com autenticação; mascarar para perfis que não precisam do dado completo | Autenticação implementada; mascaramento é próximo passo |
| Banco | Subnet privada, criptografia em repouso (KMS) e em trânsito (TLS), menor privilégio no IAM | Produção (IaC) |
| Fila e DLQ | A DLQ guarda o corpo completo: criptografia (SSE), acesso restrito e retenção curta | Produção |
| Ambientes | Dados fictícios fora de produção | Implementado |
| Ciclo de vida | Retenção, eliminação e atendimento aos titulares | Próximo passo |

Princípio: minimização. Coletar, guardar e expor o mínimo necessário.

## Limitações conhecidas e próximos passos

- API Key única, sem limite de requisições; evoluir para JWT e *rate limiting* no API Gateway.
- A documentação `/docs` fica aberta; em produção, desligar ou proteger.
- Sem TLS no ambiente local; em produção o API Gateway ou o ALB termina o TLS.
- Remoções na origem não são propagadas (o upsert só insere e atualiza).
- Documentos de um acordo não são paginados; para volumes maiores, paginar.
- Esquema do banco aplicado por script na criação; evoluir para migrações (Alembic).
- Pipeline de CI e infraestrutura como código (Terraform) ainda não implementados.
