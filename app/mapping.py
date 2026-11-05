from app.contracts import AcordoMsg, AutorMsg, DocumentoMsg


def montar_endereco(endereco: dict) -> str | None:
    """street, suite, city, zipcode -> 'Rua, Complemento - Cidade - CEP 00000-000'."""
    if not endereco:
        return None
    rua = ", ".join(p for p in (endereco.get("street"), endereco.get("suite")) if p)
    cidade = endereco.get("city")
    cep = endereco.get("zipcode")
    partes = [rua, cidade, f"CEP {cep}" if cep else None]
    return " - ".join(p for p in partes if p) or None


def montar_mensagem_autor(usuario: dict, albuns_com_fotos: list[tuple[dict, list[dict]]]) -> AutorMsg:
    """Converte users + albums + photos da API pública no nosso contrato."""
    empresa = usuario.get("company") or {}
    return AutorMsg(
        id=usuario["id"],
        nome=usuario["name"],
        email=usuario["email"],
        telefone=usuario.get("phone"),
        endereco=montar_endereco(usuario.get("address") or {}),
        empresa_nome=empresa.get("name"),
        empresa_segmento=empresa.get("bs"),
        acordos=[
            AcordoMsg(
                id=album["id"],
                titulo=album["title"],
                documentos=[
                    DocumentoMsg(
                        id=foto["id"],
                        titulo=foto["title"],
                        url=foto["url"],
                        thumbnail_url=foto["thumbnailUrl"],
                    )
                    for foto in fotos
                ],
            )
            for album, fotos in albuns_com_fotos
        ],
    )
