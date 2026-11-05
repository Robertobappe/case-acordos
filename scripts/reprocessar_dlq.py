from app.config import settings
from app.logging_config import configurar_logging, get_logger
from app.messaging import criar_cliente_sqs

log = get_logger(__name__)


def main():
    configurar_logging()
    sqs = criar_cliente_sqs()
    fila = sqs.get_queue_url(QueueName=settings.sqs_queue_name)["QueueUrl"]
    dlq = sqs.get_queue_url(QueueName=settings.sqs_dlq_name)["QueueUrl"]
    movidas = 0

    while True:
        resposta = sqs.receive_message(
            QueueUrl=dlq,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=1,
            VisibilityTimeout=60,
            MessageAttributeNames=["All"],
        )
        mensagens = resposta.get("Messages", [])
        if not mensagens:
            break
        for m in mensagens:
            atributos = {
                nome: {"DataType": valor["DataType"], "StringValue": valor["StringValue"]}
                for nome, valor in m.get("MessageAttributes", {}).items()
            }
            sqs.send_message(QueueUrl=fila, MessageBody=m["Body"], MessageAttributes=atributos)
            # Só apaga da DLQ depois que o envio deu certo.
            sqs.delete_message(QueueUrl=dlq, ReceiptHandle=m["ReceiptHandle"])
            movidas += 1

    log.info("dlq_reprocessada", extra={"movidas": movidas})


if __name__ == "__main__":
    main()
