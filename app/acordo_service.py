from app.exceptions import AutorNaoEncontrado
from app.schemas import (
    AcordoResponse,
    AutorAcordosResponse,
    AutorResponse,
    DocumentoResponse,
    EmpresaResponse,
    ResumoResponse,
)


class AcordoService:
    def __init__(self, repositorio):
        self._repositorio = repositorio

    def consultar(self, autor_id: int) -> AutorAcordosResponse:
        autor = self._repositorio.buscar_com_acordos(autor_id)
        if autor is None:
            raise AutorNaoEncontrado(autor_id)

        acordos = [
            AcordoResponse(
                id=acordo.id,
                titulo=acordo.titulo,
                quantidadeDocumentos=len(acordo.documentos),
                documentos=[
                    DocumentoResponse(
                        id=doc.id,
                        titulo=doc.titulo,
                        url=doc.url,
                        thumbnailUrl=doc.thumbnail_url,
                    )
                    for doc in acordo.documentos
                ],
            )
            for acordo in autor.acordos
        ]

        return AutorAcordosResponse(
            autor=AutorResponse(
                id=autor.id,
                nome=autor.nome,
                email=autor.email,
                telefone=autor.telefone,
                endereco=autor.endereco,
                empresa=EmpresaResponse(nome=autor.empresa_nome, segmento=autor.empresa_segmento),
            ),
            resumo=ResumoResponse(
                quantidadeAcordos=len(acordos),
                quantidadeDocumentos=sum(a.quantidadeDocumentos for a in acordos),
            ),
            acordos=acordos,
        )
