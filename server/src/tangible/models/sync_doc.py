"""Automerge CRDT documents and append-only change log."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from tangible.db import Base
from tangible.models.base import TimestampMixin, ULIDPrimaryKey


class AutomergeDoc(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "automerge_docs"

    collection_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "item"
    snapshot: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    head_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AutomergeChange(ULIDPrimaryKey, TimestampMixin, Base):
    __tablename__ = "automerge_changes"
    __table_args__ = (
        UniqueConstraint("doc_id", "change_hash", name="uq_change_doc_hash"),
    )

    doc_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("automerge_docs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    server_seq: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    change_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
