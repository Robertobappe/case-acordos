from sqlalchemy import text

from app.config import settings
from app.contracts import AcordoMsg, AutorMsg, DocumentoMsg
from app.database import criar_session_factory
from app.models import Autor
from app.repository import CargaRepository


def mensagem(autor_id: int, nome: str) -> AutorMsg:
    return AutorMsg(
        id=autor_id,
        nome=nome,
        email="demo@exemplo.com",
        acordos=[
            AcordoMsg(
                id=autor_id,
                titulo="Acordo demo",
                documentos=[
                    DocumentoMsg(id=autor_id + i, titulo=f"Doc {i}", url="u", thumbnail_url="t")
                    for i in range(3)
                ],
            )
        ],
    )


def contagens(sessao) -> str:
    a, c, d = sessao.execute(
        text(
            "SELECT (SELECT count(*) FROM autor WHERE id >= 9000),"
            "       (SELECT count(*) FROM acordo WHERE id >= 9000),"
            "       (SELECT count(*) FROM documento WHERE id >= 9000)"
        )
    ).one()
    return f"autores={a} acordos={c} documentos={d}"


def main():
    fabrica = criar_session_factory(settings.database_url)

    with fabrica.begin() as s:
        CargaRepository(s).salvar_autor(mensagem(9001, "Autor Demo"))
    with fabrica() as s:
        print("1ª gravação            :", contagens(s))

    with fabrica.begin() as s:
        CargaRepository(s).salvar_autor(mensagem(9001, "Autor Demo"))
    with fabrica() as s:
        print("2ª gravação (idêntica) :", contagens(s))

    with fabrica.begin() as s:
        CargaRepository(s).salvar_autor(mensagem(9001, "Autor Atualizado"))
    with fabrica() as s:
        nome = s.get(Autor, 9001).nome
        print(f"3ª gravação (nome novo): nome={nome!r} | {contagens(s)}")

    try:
        with fabrica.begin() as s:
            CargaRepository(s).salvar_autor(mensagem(9002, "Autor que nao deve ficar"))
            raise RuntimeError("falha simulada no meio da transação")
    except RuntimeError as erro:
        print("Erro provocado         :", erro)
    with fabrica() as s:
        print("Autor 9002 existe?     :", s.get(Autor, 9002) is not None, "|", contagens(s))

    with fabrica.begin() as s:
        s.execute(text("DELETE FROM documento WHERE id >= 9000"))
        s.execute(text("DELETE FROM acordo WHERE id >= 9000"))
        s.execute(text("DELETE FROM autor WHERE id >= 9000"))
    with fabrica() as s:
        print("Depois da limpeza      :", contagens(s))


if __name__ == "__main__":
    main()
