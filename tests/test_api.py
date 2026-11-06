import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_service, get_session
from app.api.factory import create_app
from app.exceptions import AutorNaoEncontrado
from app.schemas import (
    AcordoResponse,
    AutorAcordosResponse,
    AutorResponse,
    DocumentoResponse,
    EmpresaResponse,
    ResumoResponse,
)

CHAVE = "chave-de-teste"
HEADERS = {"X-API-Key": CHAVE}
URL = "/api/v1/usuarios/{}/acordos"


def resposta_exemplo():
    return AutorAcordosResponse(
        autor=AutorResponse(
            id=1,
            nome="Ana Silva",
            email="ana@exemplo.com",
            telefone="11 99999-0001",
            endereco="Rua A - São Paulo",
            empresa=EmpresaResponse(nome="Empresa A", segmento="varejo"),
        ),
        resumo=ResumoResponse(quantidadeAcordos=1, quantidadeDocumentos=1),
        acordos=[
            AcordoResponse(
                id=1,
                titulo="Acordo 1",
                quantidadeDocumentos=1,
                documentos=[
                    DocumentoResponse(
                        id=1,
                        titulo="Termo",
                        url="https://exemplo.com/1.png",
                        thumbnailUrl="https://exemplo.com/t1.png",
                    )
                ],
            )
        ],
    )


class ServicoFalso:
    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.ids = resposta, erro, []

    def consultar(self, autor_id):
        self.ids.append(autor_id)
        if self.erro:
            raise self.erro
        return self.resposta


def montar(servico=None, sessao=None):
    app = create_app(api_key=CHAVE, session_factory=None)
    if servico is not None:
        app.dependency_overrides[get_service] = lambda: servico
    if sessao is not None:

        def sessao_falsa():
            yield sessao

        app.dependency_overrides[get_session] = sessao_falsa
    return TestClient(app)


# --- autenticação e validação -----------------------------------------------
def test_consulta_valida_devolve_200_e_o_contrato():
    servico = ServicoFalso(resposta=resposta_exemplo())

    r = montar(servico).get(URL.format(1), headers=HEADERS)

    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"autor", "resumo", "acordos"}
    assert corpo["resumo"] == {"quantidadeAcordos": 1, "quantidadeDocumentos": 1}
    assert corpo["acordos"][0]["documentos"][0]["thumbnailUrl"] == "https://exemplo.com/t1.png"
    assert servico.ids == [1]


def test_sem_chave_devolve_401_e_nao_consulta_o_servico():
    servico = ServicoFalso(resposta=resposta_exemplo())

    r = montar(servico).get(URL.format(1))

    assert r.status_code == 401
    assert r.json()["erro"]["codigo"] == "nao_autenticado"
    assert servico.ids == []


def test_chave_errada_devolve_401():
    r = montar(ServicoFalso(resposta=resposta_exemplo())).get(
        URL.format(1), headers={"X-API-Key": "errada"}
    )

    assert r.status_code == 401


def test_autenticacao_vem_antes_da_validacao():
    # Sem chave e com id inválido: 401, para não revelar nada a quem não se identificou.
    r = montar(ServicoFalso()).get(URL.format("abc"))

    assert r.status_code == 401


@pytest.mark.parametrize("valor", ["xyz123", "0", "-5", "99999999999"])
def test_id_invalido_devolve_400(valor):
    servico = ServicoFalso(resposta=resposta_exemplo())

    r = montar(servico).get(URL.format(valor), headers=HEADERS)

    assert r.status_code == 400
    assert r.json()["erro"]["codigo"] == "requisicao_invalida"
    assert servico.ids == []


def test_400_nao_ecoa_o_valor_recebido():
    r = montar(ServicoFalso()).get(URL.format("xyz123"), headers=HEADERS)

    assert "xyz123" not in r.text
    assert "usuario_id" in r.json()["erro"]["mensagem"]


# --- erros de negócio e erros inesperados --------------------------------------
def test_autor_inexistente_devolve_404():
    servico = ServicoFalso(erro=AutorNaoEncontrado(999))

    r = montar(servico).get(URL.format(999), headers=HEADERS)

    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "autor_nao_encontrado"


def test_erro_inesperado_devolve_500_sem_vazar_detalhes():
    servico = ServicoFalso(erro=RuntimeError("segredo-interno"))

    r = montar(servico).get(URL.format(1), headers=HEADERS)

    assert r.status_code == 500
    assert r.json()["erro"]["codigo"] == "erro_interno"
    assert "segredo-interno" not in r.text
    assert r.json()["erro"]["correlationId"] == r.headers["x-correlation-id"]


# --- correlation id -----------------------------------------------------------
def test_correlation_id_recebido_e_devolvido():
    servico = ServicoFalso(erro=AutorNaoEncontrado(5))

    r = montar(servico).get(URL.format(5), headers={**HEADERS, "X-Correlation-ID": "meu-id-123"})

    assert r.headers["x-correlation-id"] == "meu-id-123"
    assert r.json()["erro"]["correlationId"] == "meu-id-123"


def test_correlation_id_invalido_e_substituido():
    servico = ServicoFalso(erro=AutorNaoEncontrado(5))

    r = montar(servico).get(URL.format(5), headers={**HEADERS, "X-Correlation-ID": "id invalido!"})

    assert r.headers["x-correlation-id"] != "id invalido!"
    assert len(r.headers["x-correlation-id"]) == 36  # um UUID gerado


def test_correlation_id_e_gerado_quando_ausente():
    r = montar(ServicoFalso(erro=AutorNaoEncontrado(5))).get(URL.format(5), headers=HEADERS)

    assert len(r.headers["x-correlation-id"]) == 36


# --- health check -----------------------------------------------------------
def test_health_nao_exige_autenticacao():
    r = montar().get("/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_com_banco_ok():
    class SessaoOk:
        def execute(self, *_):
            return None

    r = montar(sessao=SessaoOk()).get("/health/ready")

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "banco": "ok"}


def test_ready_devolve_503_com_banco_fora():
    class SessaoQuebrada:
        def execute(self, *_):
            raise RuntimeError("banco fora")

    r = montar(sessao=SessaoQuebrada()).get("/health/ready")

    assert r.status_code == 503
    assert r.json()["banco"] == "indisponivel"
    assert "banco fora" not in r.text


# --- rotas desconhecidas e configuração -----------------------------------------
def test_rota_inexistente_usa_o_formato_padrao():
    r = montar().get("/nada")

    assert r.status_code == 404
    assert r.json()["erro"]["codigo"] == "rota_nao_encontrada"


def test_metodo_nao_permitido_usa_o_formato_padrao():
    r = montar(ServicoFalso()).post(URL.format(1), headers=HEADERS)

    assert r.status_code == 405
    assert r.json()["erro"]["codigo"] == "metodo_nao_permitido"


def test_api_key_vazia_e_recusada_na_criacao():
    with pytest.raises(ValueError):
        create_app(api_key="", session_factory=None)


def test_openapi_documenta_a_chave_e_nao_anuncia_422():
    schema = montar().get("/openapi.json").json()

    assert "ApiKeyAuth" in schema["components"]["securitySchemes"]
    for caminho in schema["paths"].values():
        for operacao in caminho.values():
            assert "422" not in operacao["responses"]
