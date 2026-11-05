from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.contracts import AutorMsg
from app.models import Acordo, Autor, Documento

# Linhas por comando INSERT. O Postgres aceita até 65.535 parâmetros por comando.
TAMANHO_LOTE = 1000

COLUNAS_AUTOR = ["nome", "email", "telefone", "endereco", "empresa_nome", "empresa_segmento"]


class CargaRepository:
    """Grava a mensagem de um autor (e seus acordos e documentos) de forma idempotente.

    Não faz commit: quem chama controla a transação, e assim tudo ou nada é confirmado.
    """

    def __init__(self, session: Session):
        self._session = session

    def salvar_autor(self, msg: AutorMsg) -> None:
        # A ordem respeita as chaves estrangeiras: autor -> acordos -> documentos.
        self._upsert_autor(msg)

        acordos = [{"id": a.id, "autor_id": msg.id, "titulo": a.titulo} for a in msg.acordos]
        self._upsert_em_lotes(Acordo, acordos, atualizar=["autor_id", "titulo"])

        documentos = [
            {
                "id": d.id,
                "acordo_id": a.id,
                "titulo": d.titulo,
                "url": d.url,
                "thumbnail_url": d.thumbnail_url,
            }
            for a in msg.acordos
            for d in a.documentos
        ]
        self._upsert_em_lotes(
            Documento, documentos, atualizar=["acordo_id", "titulo", "url", "thumbnail_url"]
        )

    def _upsert_autor(self, msg: AutorMsg) -> None:
        valores = {"id": msg.id, **{coluna: getattr(msg, coluna) for coluna in COLUNAS_AUTOR}}
        stmt = insert(Autor.__table__).values(**valores)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                **{coluna: stmt.excluded[coluna] for coluna in COLUNAS_AUTOR},
                "atualizado_em": func.now(),
            },
        )
        self._session.execute(stmt)

    def _upsert_em_lotes(self, modelo, linhas: list[dict], atualizar: list[str]) -> None:
        # Usa a tabela (Core) em vez da classe ORM: é um upsert em lote,
        # sem criar um objeto Python por linha.
        for inicio in range(0, len(linhas), TAMANHO_LOTE):
            lote = linhas[inicio : inicio + TAMANHO_LOTE]
            stmt = insert(modelo.__table__).values(lote)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={coluna: stmt.excluded[coluna] for coluna in atualizar},
            )
            self._session.execute(stmt)
