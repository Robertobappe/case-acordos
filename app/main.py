from app.api.factory import create_app
from app.config import settings
from app.database import criar_session_factory
from app.logging_config import configurar_logging

configurar_logging()

app = create_app(
    api_key=settings.api_key,
    session_factory=criar_session_factory(settings.database_url),
)
