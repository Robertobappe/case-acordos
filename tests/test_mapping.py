from app.mapping import montar_endereco, montar_mensagem_autor

USUARIO = {
    "id": 1,
    "name": "Leanne Graham",
    "email": "leanne@exemplo.com",
    "phone": "1-770-736-8031",
    "address": {"street": "Kulas Light", "suite": "Apt. 556", "city": "Gwenborough", "zipcode": "92998-3874"},
    "company": {"name": "Romaguera-Crona", "bs": "harness real-time e-markets"},
}


def test_endereco_completo():
    assert montar_endereco(USUARIO["address"]) == "Kulas Light, Apt. 556 - Gwenborough - CEP 92998-3874"


def test_endereco_parcial_nao_deixa_separador_sobrando():
    assert montar_endereco({"street": "Rua X", "city": "São Paulo"}) == "Rua X - São Paulo"


def test_endereco_vazio():
    assert montar_endereco({}) is None


def test_mapeia_autor_acordos_e_documentos():
    albuns = [
        ({"id": 1, "title": "acordo um"}, [{"id": 7, "title": "termo", "url": "u", "thumbnailUrl": "t"}]),
        ({"id": 2, "title": "acordo dois"}, []),
    ]

    msg = montar_mensagem_autor(USUARIO, albuns)

    assert msg.empresa_nome == "Romaguera-Crona"
    assert msg.empresa_segmento == "harness real-time e-markets"
    assert len(msg.acordos) == 2
    assert msg.acordos[0].documentos[0].thumbnail_url == "t"
    assert msg.acordos[1].documentos == []
