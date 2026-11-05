from app.consumer import Worker
from app.consumer_service import MensagemInvalida, ResultadoMensagem
from app.logging_config import correlation_id_ctx


def mensagem(numero, corpo="ok", tentativa=1, correlation_id="cid-1"):
    return {
        "MessageId": f"m{numero}",
        "ReceiptHandle": f"r{numero}",
        "Body": corpo,
        "Attributes": {"ApproximateReceiveCount": str(tentativa)},
        "MessageAttributes": {
            "correlation_id": {"DataType": "String", "StringValue": correlation_id}
        },
    }


class SqsFalso:
    def __init__(self, mensagens):
        self.fila = list(mensagens)
        self.apagadas = []

    def receive_message(self, **_):
        lote, self.fila = self.fila[:10], self.fila[10:]
        return {"Messages": lote} if lote else {}

    def delete_message(self, QueueUrl, ReceiptHandle):
        self.apagadas.append(ReceiptHandle)

    def get_queue_attributes(self, **_):
        return {
            "Attributes": {
                "ApproximateNumberOfMessages": str(len(self.fila)),
                "ApproximateNumberOfMessagesNotVisible": "0",
            }
        }


class ServicoFalso:
    def __init__(self):
        self.correlation_ids = []

    def processar(self, corpo):
        self.correlation_ids.append(correlation_id_ctx.get())
        if corpo == "contrato":
            raise MensagemInvalida("campo faltando")
        if corpo == "banco":
            raise RuntimeError("banco fora do ar")
        return ResultadoMensagem(autor_id=1, acordos=1, documentos=1)


def montar(mensagens, max_receive_count=3):
    sqs, servico, erros = SqsFalso(mensagens), ServicoFalso(), []
    worker = Worker(
        sqs,
        "fila-url",
        servico,
        lambda *args: erros.append(args),
        max_receive_count=max_receive_count,
        espera_s=0,
    )
    return worker, sqs, servico, erros


def test_sucesso_apaga_a_mensagem():
    worker, sqs, _, erros = montar([mensagem(1)])

    worker.processar_lote()

    assert sqs.apagadas == ["r1"]
    assert (worker.processadas, worker.falhas) == (1, 0)
    assert erros == []


def test_falha_nao_apaga_a_mensagem_e_ainda_nao_registra_erro():
    worker, sqs, _, erros = montar([mensagem(1, corpo="banco", tentativa=1)])

    worker.processar_lote()

    assert sqs.apagadas == []
    assert worker.falhas == 1
    assert erros == []  # ainda há tentativas


def test_na_ultima_tentativa_registra_o_erro_sem_o_corpo():
    worker, sqs, _, erros = montar([mensagem(1, corpo="contrato", tentativa=3)])

    worker.processar_lote()

    assert sqs.apagadas == []  # mandar para a DLQ é trabalho do SQS
    assert len(erros) == 1
    correlation_id, tipo, payload, _ = erros[0]
    assert (correlation_id, tipo) == ("cid-1", "contrato")
    assert payload["message_id"] == "m1"
    assert "contrato" not in payload.values()  # o corpo da mensagem não é guardado


def test_erro_de_banco_e_classificado_como_persistencia():
    worker, _, _, erros = montar([mensagem(1, corpo="banco", tentativa=3)])

    worker.processar_lote()

    assert erros[0][1] == "persistencia"


def test_falha_em_uma_mensagem_nao_impede_as_outras_do_lote():
    worker, sqs, _, _ = montar([mensagem(1, corpo="banco"), mensagem(2)])

    worker.processar_lote()

    assert sqs.apagadas == ["r2"]
    assert (worker.processadas, worker.falhas) == (1, 1)


def test_correlation_id_da_mensagem_vale_no_processamento_e_e_limpo_depois():
    worker, _, servico, _ = montar([mensagem(1, correlation_id="abc")])

    worker.processar_lote()

    assert servico.correlation_ids == ["abc"]
    assert correlation_id_ctx.get() is None


def test_ate_esvaziar_termina_quando_a_fila_acaba():
    worker, sqs, _, _ = montar([mensagem(i) for i in range(1, 26)])

    worker.executar(ate_esvaziar=True)

    assert worker.processadas == 25
    assert len(sqs.apagadas) == 25
