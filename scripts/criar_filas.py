from app.messaging import criar_cliente_sqs, garantir_filas


def main():
    sqs = criar_cliente_sqs()
    fila_url, dlq_url = garantir_filas(sqs)
    atributos = sqs.get_queue_attributes(
        QueueUrl=fila_url, AttributeNames=["All"]
    )["Attributes"]

    print("fila principal :", fila_url)
    print("dlq            :", dlq_url)
    print("visibility     :", atributos.get("VisibilityTimeout"), "s")
    print("redrive policy :", atributos.get("RedrivePolicy"))


if __name__ == "__main__":
    main()
