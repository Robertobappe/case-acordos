from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.acordo_service import AcordoService
from app.api.deps import get_service, get_session, verificar_api_key
from app.logging_config import get_logger
from app.schemas import AutorAcordosResponse, ErroResponse

log = get_logger(__name__)

# Maior valor de INTEGER no Postgres. Acima disso o banco levanta erro (viraria 500).
ID_MAXIMO = 2_147_483_647

# A autenticação vale para o roteador inteiro: nenhuma rota nova nasce desprotegida.
router_acordos = APIRouter(
    prefix="/api/v1", tags=["Acordos"], dependencies=[Depends(verificar_api_key)]
)
router_saude = APIRouter(tags=["Saúde"])


@router_acordos.get(
    "/usuarios/{usuario_id}/acordos",
    response_model=AutorAcordosResponse,
    summary="Consulta o autor com seus acordos e documentos",
    responses={
        400: {"model": ErroResponse, "description": "Id inválido"},
        401: {"model": ErroResponse, "description": "API Key ausente ou inválida"},
        404: {"model": ErroResponse, "description": "Autor não encontrado"},
        500: {"model": ErroResponse, "description": "Erro interno"},
    },
)
def consultar_acordos(
    usuario_id: int = Path(..., gt=0, le=ID_MAXIMO, description="Id do autor (inteiro positivo)"),
    servico: AcordoService = Depends(get_service),
):
    return servico.consultar(usuario_id)


@router_saude.get("/health", summary="Liveness: o processo está vivo")
def health():
    return {"status": "ok"}


@router_saude.get("/health/ready", summary="Readiness: pronto para atender (consulta o banco)")
def readiness(sessao: Session = Depends(get_session)):
    try:
        sessao.execute(text("SELECT 1"))
    except Exception:
        log.warning("banco_indisponivel")
        return JSONResponse(status_code=503, content={"status": "degradado", "banco": "indisponivel"})
    return {"status": "ok", "banco": "ok"}
