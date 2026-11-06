from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AutorNaoEncontrado, NaoAutenticado
from app.logging_config import correlation_id_ctx
from app.schemas import ErroDetalhe, ErroResponse

_MENSAGENS_HTTP = {
    404: ("rota_nao_encontrada", "Rota não encontrada"),
    405: ("metodo_nao_permitido", "Método não permitido para esta rota"),
}


def resposta_erro(status: int, codigo: str, mensagem: str, headers: dict | None = None) -> JSONResponse:
    corpo = ErroResponse(
        erro=ErroDetalhe(codigo=codigo, mensagem=mensagem, correlationId=correlation_id_ctx.get())
    )
    return JSONResponse(status_code=status, content=corpo.model_dump(), headers=headers)


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(AutorNaoEncontrado)
    async def autor_nao_encontrado(request: Request, erro: AutorNaoEncontrado):
        return resposta_erro(404, "autor_nao_encontrado", str(erro))

    @app.exception_handler(NaoAutenticado)
    async def nao_autenticado(request: Request, erro: NaoAutenticado):
        return resposta_erro(
            401, "nao_autenticado", "API Key ausente ou inválida", headers={"WWW-Authenticate": "ApiKey"}
        )

    @app.exception_handler(RequestValidationError)
    async def requisicao_invalida(request: Request, erro: RequestValidationError):
        # Só o nome do parâmetro. Nunca o valor recebido.
        campos = sorted({str(e["loc"][-1]) for e in erro.errors()})
        return resposta_erro(400, "requisicao_invalida", f"Parâmetro inválido: {', '.join(campos)}")

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(request: Request, erro: StarletteHTTPException):
        codigo, mensagem = _MENSAGENS_HTTP.get(
            erro.status_code, (f"http_{erro.status_code}", "Requisição não atendida")
        )
        return resposta_erro(erro.status_code, codigo, mensagem, headers=getattr(erro, "headers", None))
