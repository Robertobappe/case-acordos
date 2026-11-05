import argparse
import signal
import sys
import time

from app.consumer_service import ConsumidorService, MensagemInvalida
from app.logging_config import configurar_logging, correlation_id_ctx, get_logger
from app.models import CargaErro

log = get_logger(__name__)


def _resumo(erro: Exception) -> str:
    """Primeira linha do erro. Os detalhes (SQL e valores) podem conter dado pessoal."""
    linhas = str(erro).splitlines()
    return (linhas[0] if linhas else type(erro).__name__)[:200]


class Worker:
    def __init__(
        self,
        sqs,
        fila_url,
        servico,
        registrar_erro,
        max_receive_count=3,
        visibility_timeout=30,
        espera_s=5,
    ):
        self._sqs = sqs
        self._fila_url = fila_url
        self._servico = servico
        self._registrar_erro = registrar_erro
        self._max_receive_count = max_receive_count
        self._visibility_timeout = visibility_timeout
        self._espera_s = espera_s
        self._parar = False
        self.processadas = 0
        self.falhas = 0  # tentativas que falharam (a mesma mensagem pode contar mais de uma vez)

    def parar(self) -> None:
        self._parar = True

    def executar(self, ate_esvaziar: bool = False) -> None:
        log.info("consumo_iniciado", extra={"ate_esvaziar": ate_esvaziar})
        while not self._parar:
            recebidas = self.processar_lote()
            if ate_esvaziar and recebidas == 0 and self._fila_vazia():
                break
        log.info("consumo_finalizado", extra={"processadas": self.processadas, "falhas": self.falhas})

    def processar_lote(self) -> int:
        resposta = self._sqs.receive_message(
            QueueUrl=self._fila_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self._espera_s,  # long polling
            VisibilityTimeout=self._visibility_timeout,
            MessageAttributeNames=["All"],
            AttributeNames=["All"],
        )
        mensagens = resposta.get("Messages", [])
        for mensagem in mensagens:
            self._tratar(mensagem)
        return len(mensagens)

    def _tratar(self, mensagem: dict) -> None:
        tentativa = int(mensagem.get("Attributes", {}).get("ApproximateReceiveCount", 1))
        correlation_id = (
            mensagem.get("MessageAttributes", {}).get("correlation_id", {}).get("StringValue")
        )
        token = correlation_id_ctx.set(correlation_id)
        inicio = time.monotonic()
        try:
            resultado = self._servico.processar(mensagem["Body"])
        except Exception as erro:
            self._falhou(mensagem, tentativa, correlation_id, erro)
        else:
            self._confirmar(mensagem, resultado, inicio)
        finally:
            correlation_id_ctx.reset(token)

    def _confirmar(self, mensagem: dict, resultado, inicio: float) -> None:
        # O commit já foi feito dentro do serviço: só agora é seguro apagar.
        try:
            self._sqs.delete_message(
                QueueUrl=self._fila_url, ReceiptHandle=mensagem["ReceiptHandle"]
            )
        except Exception as erro:
            # Dado já gravado. A mensagem vai reaparecer e o upsert absorve a repetição.
            log.warning(
                "falha_ao_apagar_mensagem",
                extra={"message_id": mensagem["MessageId"], "motivo": _resumo(erro)},
            )
        self.processadas += 1
        log.info(
            "mensagem_processada",
            extra={
                "message_id": mensagem["MessageId"],
                "autor_id": resultado.autor_id,
                "acordos": resultado.acordos,
                "documentos": resultado.documentos,
                "duracao_ms": round((time.monotonic() - inicio) * 1000),
            },
        )

    def _falhou(self, mensagem: dict, tentativa: int, correlation_id, erro: Exception) -> None:
        self.falhas += 1
        tipo = "contrato" if isinstance(erro, MensagemInvalida) else "persistencia"
        ultima = tentativa >= self._max_receive_count
        log.error(
            "mensagem_falhou",
            extra={
                "message_id": mensagem["MessageId"],
                "tentativa": tentativa,
                "max_tentativas": self._max_receive_count,
                "tipo": tipo,
                "tipo_erro": type(erro).__name__,
                "motivo": _resumo(erro),
                "ultima_tentativa": ultima,
            },
        )
        # Não apaga: a mensagem reaparece depois do visibility timeout.
        # Na recepção seguinte à última tentativa, é o SQS que a move para a DLQ.
        if not ultima:
            return
        try:
            self._registrar_erro(
                correlation_id,
                tipo,
                {
                    "message_id": mensagem["MessageId"],
                    "tentativa": tentativa,
                    "tamanho_bytes": len(mensagem["Body"].encode("utf-8")),
                },
                _resumo(erro),
            )
        except Exception as erro_registro:
            log.error("falha_ao_registrar_erro", extra={"motivo": _resumo(erro_registro)})

    def _fila_vazia(self) -> bool:
        atributos = self._sqs.get_queue_attributes(
            QueueUrl=self._fila_url,
            AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
        )["Attributes"]
        return (
            int(atributos["ApproximateNumberOfMessages"]) == 0
            and int(atributos["ApproximateNumberOfMessagesNotVisible"]) == 0
        )


def registrar_erro_no_banco(session_factory):
    def registrar(correlation_id, tipo, payload, erro):
        with session_factory.begin() as sessao:
            sessao.add(
                CargaErro(correlation_id=correlation_id, tipo=tipo, payload=payload, erro=erro)
            )

    return registrar


def main(argv=None) -> int:
    # Imports aqui dentro: só o executável real precisa de configuração e fila.
    from app.config import settings
    from app.database import criar_session_factory
    from app.messaging import criar_cliente_sqs

    parser = argparse.ArgumentParser(description="Consumidor da fila de acordos")
    parser.add_argument(
        "--ate-esvaziar", action="store_true", help="encerra quando a fila estiver vazia"
    )
    args = parser.parse_args(argv)

    configurar_logging()
    sqs = criar_cliente_sqs()
    fila_url = sqs.get_queue_url(QueueName=settings.sqs_queue_name)["QueueUrl"]
    fabrica = criar_session_factory(settings.database_url)

    worker = Worker(
        sqs,
        fila_url,
        ConsumidorService(fabrica),
        registrar_erro_no_banco(fabrica),
        max_receive_count=settings.sqs_max_receive_count,
        visibility_timeout=settings.sqs_visibility_timeout,
    )
    # Ctrl+C e SIGTERM (docker stop) terminam o lote atual e saem sem cortar uma gravação.
    signal.signal(signal.SIGINT, lambda *_: worker.parar())
    signal.signal(signal.SIGTERM, lambda *_: worker.parar())

    worker.executar(ate_esvaziar=args.ate_esvaziar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
