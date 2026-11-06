from pydantic import BaseModel

# Contrato fixado pelo enunciado: os nomes em camelCase
# (quantidadeAcordos, thumbnailUrl) são intencionais.


class EmpresaResponse(BaseModel):
    nome: str | None = None
    segmento: str | None = None


class AutorResponse(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None
    empresa: EmpresaResponse


class DocumentoResponse(BaseModel):
    id: int
    titulo: str
    url: str
    thumbnailUrl: str


class AcordoResponse(BaseModel):
    id: int
    titulo: str
    quantidadeDocumentos: int
    documentos: list[DocumentoResponse]


class ResumoResponse(BaseModel):
    quantidadeAcordos: int
    quantidadeDocumentos: int


class AutorAcordosResponse(BaseModel):
    autor: AutorResponse
    resumo: ResumoResponse
    acordos: list[AcordoResponse]


class ErroDetalhe(BaseModel):
    codigo: str
    mensagem: str
    correlationId: str | None = None


class ErroResponse(BaseModel):
    erro: ErroDetalhe
