import json
from collections import Counter

from app.config import settings
from app.messaging import criar_cliente_sqs


def main():
    sqs = criar_cliente_sqs()
    url = sqs.get_queue_url(QueueName=settings.sqs_dlq_name)["QueueUrl"]
    resumo, vistas = Counter(), set()

    while True:
        resposta = sqs.receive_message(
            QueueUrl=url, MaxNumberOfMessages=10, VisibilityTimeout=60, WaitTimeSeconds=1
        )
        mensagens = [m for m in resposta.get("Messages", []) if m["MessageId"] not in vistas]
        if not mensagens:
            break
        for m in mensagens:
            vistas.add(m["MessageId"])
            try:
                resumo[f"autor {json.loads(m['Body'])['id']}"] += 1
            except (ValueError, KeyError, TypeError):
                resumo["inválida (fora do contrato)"] += 1

    print(f"{len(vistas)} mensagens na DLQ")
    for chave, total in sorted(resumo.items()):
        print(f"  {chave}: {total}")


if __name__ == "__main__":
    main()
