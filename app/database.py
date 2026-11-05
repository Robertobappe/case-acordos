from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def criar_session_factory(database_url: str) -> sessionmaker:
    """Devolve uma fábrica de sessões.

    pool_pre_ping testa a conexão antes de usá-la, e evita erro com conexões
    que o banco já derrubou (por exemplo, depois de ficar ocioso).
    """
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)
