import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """Модель документа"""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(10), nullable=False, index=True)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 хеш
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Связь с содержимым
    content = relationship(
        "DocumentContent",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Document(id={self.id}, file_type={self.file_type}, user_id={self.user_id})>"


class DocumentContent(Base):
    """Модель содержимого документа"""

    __tablename__ = "document_contents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)
    tsvector_col = Column(TSVECTOR)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Связь с документом
    document = relationship("Document", back_populates="content")

    def __repr__(self):
        return f"<DocumentContent(id={self.id}, document_id={self.document_id})>"

    __table_args__ = (
        # GIN индекс для полнотекстового поиска
        Index(
            "idx_document_contents_tsvector",
            "tsvector_col",
            postgresql_using="gin",
        ),
    )
