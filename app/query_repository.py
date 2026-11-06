from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Acordo, Autor


class AutorRepository:
    """Consultas de leitura. A API nunca escreve no banco."""

    def __init__(self, session: Session):
        self._session = session

    def buscar_com_acordos(self, autor_id: int) -> Autor | None:
        """Devolve o autor com acordos e documentos, ou None se não existir.

        selectinload carrega cada nível com uma única consulta (IN), e evita
        o problema N+1: são 3 consultas, qualquer que seja o volume.
        """
        stmt = (
            select(Autor)
            .where(Autor.id == autor_id)
            .options(selectinload(Autor.acordos).selectinload(Acordo.documentos))
        )
        return self._session.execute(stmt).scalar_one_or_none()
