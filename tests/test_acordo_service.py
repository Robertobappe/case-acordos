from types import SimpleNamespace as NS

import pytest

from app.acordo_service import AcordoService
from app.exceptions import AutorNaoEncontrado


def doc(numero):
    return NS(
        id=numero,
        titulo=f"Documento {numero}",
        url=f"https://exemplo.com/{numero}.png",
        thumbnail_url=f"https://exemplo.com/t{numero}.png",
    )


def autor_falso(acordos):
    return NS(
        id=1,
        nome="Ana Silva",
        email="ana@exemplo.com",
        telefone="11 99999-0001",
        endereco="Rua A, Apto 1 - São Paulo - CEP 01000-000",
        empresa_nome="Empresa A",
        empresa_segmento="varejo",
        acordos=acordos,
    )


class RepositorioFalso:
    def __init__(self, autor):
        self.autor = autor
        self.ids_consultados = []

    def buscar_com_acordos(self, autor_id):
        self.ids_consultados.append(autor_id)
        return self.autor


def test_consolida_resumo_e_acordos():
    acordos = [
        NS(id=1, titulo="Acordo 1", documentos=[doc(1), doc(2), doc(3)]),
        NS(id=2, titulo="Acordo 2", documentos=[doc(4), doc(5)]),
        NS(id=3, titulo="Acordo 3", documentos=[]),
    ]

    resposta = AcordoService(RepositorioFalso(autor_falso(acordos))).consultar(1)

    assert resposta.resumo.quantidadeAcordos == 3
    assert resposta.resumo.quantidadeDocumentos == 5
    assert [a.quantidadeDocumentos for a in resposta.acordos] == [3, 2, 0]
    assert [a.id for a in resposta.acordos] == [1, 2, 3]


def test_mapeia_dados_do_autor_e_da_empresa():
    resposta = AcordoService(RepositorioFalso(autor_falso([]))).consultar(1)

    assert resposta.autor.id == 1
    assert resposta.autor.email == "ana@exemplo.com"
    assert resposta.autor.endereco == "Rua A, Apto 1 - São Paulo - CEP 01000-000"
    assert resposta.autor.empresa.nome == "Empresa A"
    assert resposta.autor.empresa.segmento == "varejo"


def test_documento_expoe_thumbnail_com_o_nome_do_contrato():
    acordos = [NS(id=1, titulo="Acordo 1", documentos=[doc(7)])]

    resposta = AcordoService(RepositorioFalso(autor_falso(acordos))).consultar(1)

    documento = resposta.acordos[0].documentos[0]
    assert documento.thumbnailUrl == "https://exemplo.com/t7.png"
    assert documento.url == "https://exemplo.com/7.png"
    assert "thumbnailUrl" in documento.model_dump()


def test_autor_sem_acordos_devolve_resumo_zerado_e_lista_vazia():
    resposta = AcordoService(RepositorioFalso(autor_falso([]))).consultar(1)

    assert resposta.resumo.quantidadeAcordos == 0
    assert resposta.resumo.quantidadeDocumentos == 0
    assert resposta.acordos == []


def test_autor_inexistente_levanta_excecao_de_dominio():
    repositorio = RepositorioFalso(None)

    with pytest.raises(AutorNaoEncontrado) as erro:
        AcordoService(repositorio).consultar(999)

    assert repositorio.ids_consultados == [999]
    assert erro.value.autor_id == 999
