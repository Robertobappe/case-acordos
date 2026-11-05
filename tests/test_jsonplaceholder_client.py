import httpx
import pytest

from app.clients.jsonplaceholder import ApiPublicaError, JsonPlaceholderClient


def montar_cliente(roteiro, max_tentativas=4):
    """Cria um cliente cujo 'servidor' segue um roteiro.

    Cada item do roteiro é (status, corpo_json) ou uma exceção a ser levantada.
    Quando o roteiro acaba, o último item se repete.
    Devolve o cliente, as URLs chamadas e as esperas pedidas (sem esperar de verdade).
    """
    chamadas = []
    esperas = []

    def handler(request):
        indice = min(len(chamadas), len(roteiro) - 1)
        chamadas.append(str(request.url))
        item = roteiro[indice]
        if isinstance(item, Exception):
            raise item
        status, corpo = item
        return httpx.Response(status, json=corpo)

    cliente = JsonPlaceholderClient(
        "https://api.fake",
        max_tentativas=max_tentativas,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=esperas.append,
    )
    return cliente, chamadas, esperas


def test_sucesso_na_primeira_tentativa():
    cliente, chamadas, esperas = montar_cliente([(200, [{"id": 1}])])

    assert cliente.listar_usuarios() == [{"id": 1}]
    assert len(chamadas) == 1
    assert esperas == []


def test_recupera_depois_de_falhas_transitorias():
    cliente, chamadas, esperas = montar_cliente([(503, {}), (503, {}), (200, [{"id": 1}])])

    assert cliente.listar_usuarios() == [{"id": 1}]
    assert len(chamadas) == 3
    assert len(esperas) == 2
    assert esperas[1] > esperas[0]  # backoff exponencial


def test_timeout_tambem_e_retentado():
    cliente, chamadas, _ = montar_cliente([httpx.ConnectTimeout("lento"), (200, [])])

    assert cliente.listar_usuarios() == []
    assert len(chamadas) == 2


def test_desiste_depois_do_limite_de_tentativas():
    cliente, chamadas, esperas = montar_cliente([(503, {})], max_tentativas=3)

    with pytest.raises(ApiPublicaError):
        cliente.listar_usuarios()

    assert len(chamadas) == 3
    assert len(esperas) == 2  # não espera depois da última tentativa


def test_erro_4xx_nao_e_retentado():
    cliente, chamadas, esperas = montar_cliente([(404, {})])

    with pytest.raises(ApiPublicaError):
        cliente.listar_usuarios()

    assert len(chamadas) == 1
    assert esperas == []
