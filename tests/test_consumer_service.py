import json
from contextlib import contextmanager

import pytest

from app.consumer_service import ConsumidorService, MensagemInvalida
from app.contracts import AcordoMsg, AutorMsg, DocumentoMsg


def corpo_valido(autor_id=1):
    return AutorMsg(
        id=autor_id,
        nome="Fulano",
        email="fulano@exemplo.com",
        acordos=[
            AcordoMsg(
                id=10,
                titulo="Acordo",
                documentos=[
                    DocumentoMsg(id=100, titulo="Doc 1", url="u", thumbnail_url="t"),
                    DocumentoMsg(id=101, titulo="Doc 2", url="u", thumbnail_url="t"),
                ],
            )
        ],
    ).model_dump_json()


class FabricaFalsa:
    """Imita session_factory.begin(): conta aberturas, commits e rollbacks."""

    def __init__(self):
        self.abertas = 0
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def begin(self):
        self.abertas += 1
        try:
            yield object()
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


def repositorio_falso(salvos, falha=None):
    class RepositorioFalso:
        def __init__(self, sessao):
            pass

        def salvar_autor(self, msg):
            if falha:
                raise falha
            salvos.append(msg)

    return RepositorioFalso


def test_mensagem_valida_e_gravada_e_confirmada():
    fabrica, salvos = FabricaFalsa(), []

    resultado = ConsumidorService(fabrica, repositorio_falso(salvos)).processar(corpo_valido(7))

    assert [m.id for m in salvos] == [7]
    assert (fabrica.commits, fabrica.rollbacks) == (1, 0)
    assert (resultado.autor_id, resultado.acordos, resultado.documentos) == (7, 1, 2)


def test_json_invalido_e_recusado_sem_abrir_transacao():
    fabrica = FabricaFalsa()

    with pytest.raises(MensagemInvalida):
        ConsumidorService(fabrica, repositorio_falso([])).processar("{isto nao e json")

    assert fabrica.abertas == 0


def test_mensagem_fora_do_contrato_nao_vaza_dados_pessoais_no_erro():
    corpo = json.dumps({"id": 1, "email": "segredo@exemplo.com"})  # falta o nome

    with pytest.raises(MensagemInvalida) as info:
        ConsumidorService(FabricaFalsa(), repositorio_falso([])).processar(corpo)

    texto = str(info.value)
    assert "nome" in texto
    assert "segredo@exemplo.com" not in texto


def test_falha_ao_gravar_desfaz_a_transacao_e_propaga_o_erro():
    fabrica = FabricaFalsa()
    servico = ConsumidorService(fabrica, repositorio_falso([], falha=RuntimeError("banco caiu")))

    with pytest.raises(RuntimeError):
        servico.processar(corpo_valido())

    assert (fabrica.commits, fabrica.rollbacks) == (0, 1)
