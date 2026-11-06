from sqlalchemy import event

from app.acordo_service import AcordoService
from app.config import settings
from app.database import criar_session_factory
from app.exceptions import AutorNaoEncontrado
from app.query_repository import AutorRepository


def main():
    fabrica = criar_session_factory(settings.database_url)

    with fabrica() as sessao:
        consultas = []
        event.listen(
            sessao.get_bind(), "before_cursor_execute", lambda *args: consultas.append(1)
        )

        servico = AcordoService(AutorRepository(sessao))
        resposta = servico.consultar(1)

        primeiro_acordo = resposta.acordos[0]
        print("autor            :", resposta.autor.model_dump())
        print("resumo           :", resposta.resumo.model_dump())
        print("acordos          :", len(resposta.acordos))
        print("docs 1º acordo   :", primeiro_acordo.quantidadeDocumentos)
        print("1º documento     :", primeiro_acordo.documentos[0].model_dump())
        print("consultas SQL    :", len(consultas))

        try:
            servico.consultar(999)
        except AutorNaoEncontrado as erro:
            print("autor 999        : AutorNaoEncontrado ->", erro)


if __name__ == "__main__":
    main()
