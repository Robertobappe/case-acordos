import secrets

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.acordo_service import AcordoService
from app.exceptions import NaoAutenticado
from app.query_repository import AutorRepository

# auto_error=False: quem decide o erro (e seu formato) é o nosso handler central.
# Declarar como esquema de segurança faz o Swagger exibir o botão "Authorize".
_esquema_api_key = APIKeyHeader(
    name="X-API-Key",
    scheme_name="ApiKeyAuth",
    auto_error=False,
    description="Chave de acesso da API.",
)


def verificar_api_key(request: Request, chave: str | None = Security(_esquema_api_key)) -> None:
    esperada: str = request.app.state.api_key
    # compare_digest leva o mesmo tempo quer a chave erre no 1º ou no último caractere.
    if not chave or not secrets.compare_digest(chave.encode(), esperada.encode()):
        raise NaoAutenticado("API Key ausente ou inválida")


def get_session(request: Request):
    """Uma sessão por requisição, fechada ao final. A API só lê, então nunca faz commit."""
    with request.app.state.session_factory() as sessao:
        yield sessao


def get_service(sessao: Session = Depends(get_session)) -> AcordoService:
    return AcordoService(AutorRepository(sessao))
