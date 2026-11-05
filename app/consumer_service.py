from dataclasses import dataclass

from pydantic import ValidationError

from app.contracts import AutorMsg
from app.repository import CargaRepository


class MensagemInvalida(Exception):
    """O corpo da mensagem não respeita o contrato. Reprocessar não resolve."""


@dataclass
class ResultadoMensagem:
    autor_id: int
    acordos: int
    documentos: int


def _resumir_erros(erro: ValidationError) -> str:
    # Só o local e o tipo do problema. O texto padrão do Pydantic inclui o valor
    # recebido, e isso seria dado pessoal indo parar em log.
    itens = [
        f"{'.'.join(str(parte) for parte in e['loc']) or 'corpo'}: {e['type']}"
        for e in erro.errors()[:5]
    ]
    return "; ".join(itens)


class ConsumidorService:
    def __init__(self, session_factory, repositorio=CargaRepository):
        self._session_factory = session_factory
        self._repositorio = repositorio

    def processar(self, corpo: str) -> ResultadoMensagem:
        try:
            msg = AutorMsg.model_validate_json(corpo)
        except ValidationError as erro:
            raise MensagemInvalida(f"Mensagem fora do contrato ({_resumir_erros(erro)})") from erro

        # begin(): confirma ao sair do bloco e desfaz se uma exceção escapar.
        with self._session_factory.begin() as sessao:
            self._repositorio(sessao).salvar_autor(msg)

        return ResultadoMensagem(
            autor_id=msg.id,
            acordos=len(msg.acordos),
            documentos=sum(len(a.documentos) for a in msg.acordos),
        )
