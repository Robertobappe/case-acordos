import sys
import time
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from pydantic import ValidationError

from app.clients.jsonplaceholder import ApiPublicaError
from app.contracts import MensagemGrandeDemais
from app.logging_config import configurar_logging, correlation_id_ctx, get_logger
from app.mapping import montar_mensagem_autor

log = get_logger(__name__)

# Falhas por autor que não devem derrubar a carga inteira.
ERROS_POR_AUTOR = (ApiPublicaError, MensagemGrandeDemais, KeyError, ValidationError)


@dataclass
class ResultadoCarga:
    correlation_id: str = ""
    publicadas: int = 0
    falhas: int = 0
    acordos: int = 0
    documentos: int = 0


class Produtor:
    def __init__(self, api, publicar: Callable[[str, str], int]):
        """api: cliente da API pública. publicar(corpo, correlation_id) -> bytes."""
        self._api = api
        self._publicar = publicar

    def executar(self) -> ResultadoCarga:
        correlation_id = str(uuid4())
        token = correlation_id_ctx.set(correlation_id)
        inicio = time.monotonic()
        resultado = ResultadoCarga(correlation_id=correlation_id)
        try:
            log.info("carga_iniciada")
            usuarios = self._api.listar_usuarios()
            log.info("autores_encontrados", extra={"total": len(usuarios)})

            for usuario in usuarios:
                self._processar_autor(usuario, correlation_id, resultado)

            log.info(
                "carga_finalizada",
                extra={
                    "publicadas": resultado.publicadas,
                    "falhas": resultado.falhas,
                    "acordos": resultado.acordos,
                    "documentos": resultado.documentos,
                    "duracao_s": round(time.monotonic() - inicio, 2),
                },
            )
            return resultado
        finally:
            correlation_id_ctx.reset(token)

    def _processar_autor(self, usuario: dict, correlation_id: str, resultado: ResultadoCarga) -> None:
        try:
            albuns = self._api.listar_albuns_do_usuario(usuario["id"])
            pares = [(album, self._api.listar_fotos_do_album(album["id"])) for album in albuns]
            mensagem = montar_mensagem_autor(usuario, pares)
            tamanho = self._publicar(mensagem.model_dump_json(), correlation_id)
        except ERROS_POR_AUTOR as erro:
            resultado.falhas += 1
            log.error(
                "autor_falhou",
                extra={"autor_id": usuario.get("id"), "tipo_erro": type(erro).__name__, "motivo": str(erro)},
            )
            return

        total_documentos = sum(len(a.documentos) for a in mensagem.acordos)
        resultado.publicadas += 1
        resultado.acordos += len(mensagem.acordos)
        resultado.documentos += total_documentos
        log.info(
            "mensagem_publicada",
            extra={
                "autor_id": mensagem.id,
                "acordos": len(mensagem.acordos),
                "documentos": total_documentos,
                "tamanho_bytes": tamanho,
            },
        )


def main() -> int:
    # Imports aqui dentro: só o executável real precisa de configuração e fila.
    from app.clients.jsonplaceholder import JsonPlaceholderClient
    from app.config import settings
    from app.messaging import criar_cliente_sqs, garantir_filas, publicar

    configurar_logging()
    api = JsonPlaceholderClient(settings.public_api_base_url)
    sqs = criar_cliente_sqs()
    fila_url, _ = garantir_filas(sqs)

    produtor = Produtor(api, lambda corpo, cid: publicar(sqs, fila_url, corpo, cid))
    try:
        resultado = produtor.executar()
    except Exception:
        log.exception("carga_abortada")
        return 1
    return 1 if resultado.falhas else 0


if __name__ == "__main__":
    sys.exit(main())
