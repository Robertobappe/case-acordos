import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Identificador da execução atual (carga ou requisição). Definido uma vez,
# lido automaticamente em todo log.
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)

# Atributos que todo LogRecord já possui; o que sobrar em record.__dict__
# veio de `extra=` e vira campo do JSON.
_CAMPOS_PADRAO = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "evento": record.getMessage(),
        }
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id

        for chave, valor in record.__dict__.items():
            if chave not in _CAMPOS_PADRAO:
                payload[chave] = valor

        if record.exc_info:
            payload["excecao"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configurar_logging(nivel: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel)


def get_logger(nome: str) -> logging.Logger:
    return logging.getLogger(nome)
