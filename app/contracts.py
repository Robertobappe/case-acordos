from pydantic import BaseModel, Field

# Limite de tamanho de uma mensagem no SQS.
TAMANHO_MAX_BYTES = 256 * 1024


class MensagemGrandeDemais(Exception):
    """A mensagem excede o limite do SQS."""


class DocumentoMsg(BaseModel):
    id: int
    titulo: str
    url: str
    thumbnail_url: str


class AcordoMsg(BaseModel):
    id: int
    titulo: str
    documentos: list[DocumentoMsg] = Field(default_factory=list)


class AutorMsg(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str | None = None
    endereco: str | None = None
    empresa_nome: str | None = None
    empresa_segmento: str | None = None
    acordos: list[AcordoMsg] = Field(default_factory=list)
