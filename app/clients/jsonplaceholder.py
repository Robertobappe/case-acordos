import random
import time

import httpx

from app.logging_config import get_logger

log = get_logger(__name__)

# Status HTTP que indicam falha temporária: vale tentar de novo.
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}


class ApiPublicaError(Exception):
    """Falha definitiva ao consultar a API pública (esgotadas as tentativas)."""


class _FalhaTransitoria(Exception):
    """Uso interno: sinaliza um status HTTP que merece retentativa."""


class JsonPlaceholderClient:
    def __init__(
        self,
        base_url: str,
        max_tentativas: int = 4,
        backoff_base: float = 0.5,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
        sleep=time.sleep,
    ):
        self._base_url = base_url.rstrip("/")
        self._max_tentativas = max_tentativas
        self._backoff_base = backoff_base
        self._http = client or httpx.Client(timeout=timeout)
        self._sleep = sleep

    # --- operações de negócio -------------------------------------------
    def listar_usuarios(self) -> list[dict]:
        return self._get("/users")

    def listar_albuns_do_usuario(self, usuario_id: int) -> list[dict]:
        return self._get(f"/users/{usuario_id}/albums")

    def listar_fotos_do_album(self, album_id: int) -> list[dict]:
        return self._get(f"/albums/{album_id}/photos")

    # --- infraestrutura de resiliência ----------------------------------
    def _get(self, caminho: str):
        url = f"{self._base_url}{caminho}"

        for tentativa in range(1, self._max_tentativas + 1):
            try:
                resposta = self._http.get(url)
                if resposta.status_code in STATUS_TRANSITORIOS:
                    raise _FalhaTransitoria(f"status {resposta.status_code}")
                resposta.raise_for_status()  # 4xx vira HTTPStatusError
                return resposta.json()

            except (httpx.TransportError, _FalhaTransitoria) as erro:
                # Timeout, queda de conexão ou status transitório.
                if tentativa == self._max_tentativas:
                    log.error(
                        "api_publica_falhou",
                        extra={"url": url, "tentativas": tentativa, "motivo": str(erro)},
                    )
                    raise ApiPublicaError(
                        f"Falha ao consultar {url} após {tentativa} tentativas: {erro}"
                    ) from erro

                espera = self._backoff_base * (2 ** (tentativa - 1)) + random.uniform(0, 0.3)
                log.warning(
                    "retentativa",
                    extra={
                        "url": url,
                        "tentativa": tentativa,
                        "max_tentativas": self._max_tentativas,
                        "espera_s": round(espera, 2),
                        "motivo": str(erro),
                    },
                )
                self._sleep(espera)

            except httpx.HTTPStatusError as erro:
                # 4xx: o erro é da requisição, repetir não adianta.
                log.error(
                    "api_publica_erro_nao_transitorio",
                    extra={"url": url, "status": erro.response.status_code},
                )
                raise ApiPublicaError(
                    f"Erro {erro.response.status_code} ao consultar {url}"
                ) from erro
