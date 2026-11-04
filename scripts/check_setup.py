import boto3
from sqlalchemy import create_engine, text

from app.config import settings


def check_postgres():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        resultado = conn.execute(text("SELECT 1")).scalar()
    print(f"[OK] Postgres respondeu: {resultado}")


def check_sqs():
    sqs = boto3.client(
        "sqs",
        endpoint_url=settings.aws_endpoint_url,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    sqs.create_queue(QueueName=settings.sqs_queue_name)
    filas = sqs.list_queues().get("QueueUrls", [])
    print(f"[OK] SQS respondeu. Filas: {filas}")


if __name__ == "__main__":
    check_postgres()
    check_sqs()
