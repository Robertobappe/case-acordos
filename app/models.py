from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Autor(Base):
    __tablename__ = "autor"

    # O id vem da origem (não é gerado pelo banco): base da idempotência.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150))
    telefone: Mapped[str | None] = mapped_column(String(50))
    endereco: Mapped[str | None] = mapped_column(String(300))
    empresa_nome: Mapped[str | None] = mapped_column(String(150))
    empresa_segmento: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    acordos: Mapped[list["Acordo"]] = relationship(back_populates="autor", order_by="Acordo.id")


class Acordo(Base):
    __tablename__ = "acordo"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    autor_id: Mapped[int] = mapped_column(ForeignKey("autor.id"))
    titulo: Mapped[str] = mapped_column(String(300))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    autor: Mapped[Autor] = relationship(back_populates="acordos")
    documentos: Mapped[list["Documento"]] = relationship(back_populates="acordo", order_by="Documento.id")


class Documento(Base):
    __tablename__ = "documento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    acordo_id: Mapped[int] = mapped_column(ForeignKey("acordo.id"))
    titulo: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))
    thumbnail_url: Mapped[str] = mapped_column(String(500))
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())

    acordo: Mapped[Acordo] = relationship(back_populates="documentos")


class CargaErro(Base):
    __tablename__ = "carga_erro"

    id: Mapped[int] = mapped_column(primary_key=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    tipo: Mapped[str | None] = mapped_column(String(30))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    erro: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
