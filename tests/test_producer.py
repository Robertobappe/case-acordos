from app.clients.jsonplaceholder import ApiPublicaError
from app.contracts import AutorMsg
from app.producer import Produtor


def usuario(i):
    return {
        "id": i, "name": f"Autor {i}", "email": f"a{i}@exemplo.com", "phone": "1",
        "address": {"street": "Rua", "suite": "1", "city": "Cidade", "zipcode": "00000-000"},
        "company": {"name": "Empresa", "bs": "segmento"},
    }


class ApiFalsa:
    def __init__(self, falha_no_autor=None):
        self.falha_no_autor = falha_no_autor

    def listar_usuarios(self):
        return [usuario(1), usuario(2)]

    def listar_albuns_do_usuario(self, usuario_id):
        if usuario_id == self.falha_no_autor:
            raise ApiPublicaError("api fora do ar")
        return [{"id": usuario_id * 10, "title": f"acordo {usuario_id}"}]

    def listar_fotos_do_album(self, album_id):
        return [{"id": album_id * 100, "title": "foto", "url": "u", "thumbnailUrl": "t"}]


class PublicadorFalso:
    def __init__(self):
        self.mensagens = []

    def __call__(self, corpo, correlation_id):
        self.mensagens.append((corpo, correlation_id))
        return len(corpo)


def test_publica_uma_mensagem_por_autor_com_o_mesmo_correlation_id():
    publicador = PublicadorFalso()

    resultado = Produtor(ApiFalsa(), publicador).executar()

    assert (resultado.publicadas, resultado.falhas) == (2, 0)
    assert (resultado.acordos, resultado.documentos) == (2, 2)
    assert {cid for _, cid in publicador.mensagens} == {resultado.correlation_id}
    primeira = AutorMsg.model_validate_json(publicador.mensagens[0][0])
    assert primeira.id == 1 and len(primeira.acordos[0].documentos) == 1


def test_falha_em_um_autor_nao_impede_os_outros():
    publicador = PublicadorFalso()

    resultado = Produtor(ApiFalsa(falha_no_autor=1), publicador).executar()

    assert (resultado.publicadas, resultado.falhas) == (1, 1)
    assert AutorMsg.model_validate_json(publicador.mensagens[0][0]).id == 2


def test_cada_execucao_tem_seu_correlation_id():
    produtor = Produtor(ApiFalsa(), PublicadorFalso())

    assert produtor.executar().correlation_id != produtor.executar().correlation_id
