import json

import boto3

from app.config import settings
from app.contracts import TAMANHO_MAX_BYTES, MensagemGrandeDemais


def criar_cliente_sqs():
    """Com endpoint_url usa o ElasticMQ local; com None, o SQS real da AWS."""
    return boto3.client(
        "sqs",
        endpoint_url=settings.aws_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def garantir_filas(sqs) -> tuple[str, str]:
    """Cria (se não existirem) a DLQ e a fila principal ligada a ela.

    A DLQ vem primeiro, porque a fila principal precisa do ARN dela.
    Devolve (url_da_fila, url_da_dlq).
    """
    dlq_url = sqs.create_queue(QueueName=settings.sqs_dlq_name)["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(
        QueueUrl=dlq_url, AttributeNames=["QueueArn"]
    )["Attributes"]["QueueArn"]

    politica_redrive = {
        "deadLetterTargetArn": dlq_arn,
        "maxReceiveCount": str(settings.sqs_max_receive_count),
    }
    fila_url = sqs.create_queue(
        QueueName=settings.sqs_queue_name,
        Attributes={
            "VisibilityTimeout": str(settings.sqs_visibility_timeout),
            "RedrivePolicy": json.dumps(politica_redrive),
        },
    )["QueueUrl"]
    return fila_url, dlq_url


def publicar(sqs, fila_url: str, corpo: str, correlation_id: str) -> int:
    """Publica uma mensagem e devolve o tamanho em bytes."""
    tamanho = len(corpo.encode("utf-8"))
    if tamanho > TAMANHO_MAX_BYTES:
        raise MensagemGrandeDemais(
            f"Mensagem com {tamanho} bytes excede o limite de {TAMANHO_MAX_BYTES}"
        )
    sqs.send_message(
        QueueUrl=fila_url,
        MessageBody=corpo,
        MessageAttributes={
            "correlation_id": {"DataType": "String", "StringValue": correlation_id}
        },
    )
    return tamanho
