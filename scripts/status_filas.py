from app.config import settings
from app.messaging import criar_cliente_sqs, garantir_filas

METRICAS = [
    "ApproximateNumberOfMessages",            # disponíveis
    "ApproximateNumberOfMessagesNotVisible",  # em processamento (invisíveis)
]


def contar(sqs, url):
    atributos = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=METRICAS)["Attributes"]
    return int(atributos["ApproximateNumberOfMessages"]), int(atributos["ApproximateNumberOfMessagesNotVisible"])


def main():
    sqs = criar_cliente_sqs()
    fila_url, dlq_url = garantir_filas(sqs)
    for nome, url in ((settings.sqs_queue_name, fila_url), (settings.sqs_dlq_name, dlq_url)):
        disponiveis, em_processamento = contar(sqs, url)
        print(f"{nome:15} disponíveis={disponiveis:<4} em processamento={em_processamento}")


if __name__ == "__main__":
    main()
