from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Lê o .env e ignora variáveis que não declaramos aqui
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Banco
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    # Fila (SQS)
    aws_endpoint_url: str | None = None  # vazio em produção real
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    sqs_queue_name: str
    sqs_dlq_name: str
    sqs_max_receive_count: int = 3
    sqs_visibility_timeout: int = 30

    # API
    api_key: str
    public_api_base_url: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
