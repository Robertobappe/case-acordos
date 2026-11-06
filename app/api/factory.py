import logging
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi

from app.api.errors import registrar_handlers, resposta_erro
from app.api.routes import router_acordos, router_saude
from app.logging_config import correlation_id_ctx, get_logger

log = get_logger(__name__)

# Só aceitamos ids curtos e "limpos": o valor vai parar em logs.
_CORRELATION_VALIDO = re.compile(r"[A-Za-z0-9._-]{1,64}")

DESCRICAO = (
    "Consulta consolidada de autores, acordos e documentos.\n\n"
    "Envie a chave no cabeçalho `X-API-Key`. "
    "Toda resposta traz o cabeçalho `X-Correlation-ID`."
)


def create_app(api_key: str, session_factory) -> FastAPI:
    """Monta a aplicação. Recebe a configuração por parâmetro (não lê o .env),
    e por isso os testes criam apps isolados sem depender de ambiente."""
    if not api_key:
        raise ValueError("API_KEY não configurada")

    app = FastAPI(title="API de Acordos", version="1.0.0", description=DESCRICAO)
    app.state.api_key = api_key
    app.state.session_factory = session_factory

    registrar_handlers(app)
    app.include_router(router_saude)
    app.include_router(router_acordos)

    @app.middleware("http")
    async def correlation_id_e_log(request: Request, call_next):
        recebido = request.headers.get("x-correlation-id", "")
        correlation_id = recebido if _CORRELATION_VALIDO.fullmatch(recebido) else str(uuid4())
        token = correlation_id_ctx.set(correlation_id)
        inicio = time.monotonic()
        try:
            try:
                resposta = await call_next(request)
            except Exception:
                # Rede de segurança: o cliente recebe uma frase genérica e o id;
                # o traceback vai só para o log. Os parâmetros das consultas desta
                # API são apenas ids, então não há dado pessoal nele.
                log.exception("erro_nao_tratado", extra={"caminho": request.url.path})
                resposta = resposta_erro(
                    500, "erro_interno", "Erro interno. Informe o correlationId ao suporte."
                )

            resposta.headers["X-Correlation-ID"] = correlation_id
            # Os health checks são frequentes: só aparecem com o nível DEBUG.
            nivel = logging.DEBUG if request.url.path.startswith("/health") else logging.INFO
            log.log(
                nivel,
                "requisicao",
                extra={
                    "metodo": request.method,
                    "caminho": request.url.path,
                    "status": resposta.status_code,
                    "duracao_ms": round((time.monotonic() - inicio) * 1000),
                },
            )
            return resposta
        finally:
            correlation_id_ctx.reset(token)

    _openapi_sem_422(app)
    return app


def _openapi_sem_422(app: FastAPI) -> None:
    """Valores inválidos viram 400 nesta API. O FastAPI anunciaria 422 no Swagger,
    e a documentação não pode contradizer o comportamento."""

    def personalizado():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes
        )
        for caminho in schema["paths"].values():
            for operacao in caminho.values():
                if isinstance(operacao, dict):
                    operacao.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
        return schema

    app.openapi = personalizado
