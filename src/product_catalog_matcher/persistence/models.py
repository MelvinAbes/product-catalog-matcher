from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from product_catalog_matcher.domain import (
    ImportRole,
    ImportStatus,
    IssueSeverity,
    MatchDecision,
    RecordStatus,
    ReviewAction,
)
from product_catalog_matcher.persistence.base import Base


def enum_values(
    enum_type: type[ImportRole | ImportStatus | IssueSeverity | MatchDecision | ReviewAction],
) -> list[str]:
    return [item.value for item in enum_type]


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "total_rows >= 0 AND accepted_rows >= 0 AND rejected_rows >= 0 "
            "AND duplicate_rows >= 0 AND issue_count >= 0",
            name="non_negative_counts",
        ),
        UniqueConstraint("supplier_id", "content_sha256", name="supplier_content"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    role: Mapped[ImportRole] = mapped_column(
        Enum(
            ImportRole,
            values_callable=enum_values,
            name="import_role",
            native_enum=False,
        )
    )
    status: Mapped[ImportStatus] = mapped_column(
        Enum(
            ImportStatus,
            values_callable=enum_values,
            name="import_status",
            native_enum=False,
        ),
        default=ImportStatus.PENDING,
    )
    file_name: Mapped[str] = mapped_column(String(255))
    content_sha256: Mapped[str] = mapped_column(String(64))
    total_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    accepted_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    issue_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanonicalProduct(Base):
    __tablename__ = "canonical_products"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(200))
    normalized_brand: Mapped[str | None] = mapped_column(String(200), index=True)
    category: Mapped[str | None] = mapped_column(String(300))
    normalized_category: Mapped[str | None] = mapped_column(String(300), index=True)
    gtin: Mapped[str | None] = mapped_column(String(14), index=True)
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(120))
    normalized_mpn: Mapped[str | None] = mapped_column(String(120))
    pack_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit_code: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (
        CheckConstraint("source_row_number > 0", name="source_row"),
        UniqueConstraint("import_batch_id", "source_record_id", name="batch_source_record"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    supplier_id: Mapped[UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True
    )
    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True
    )
    source_record_id: Mapped[str] = mapped_column(String(160))
    source_row_number: Mapped[int] = mapped_column(Integer)
    record_status: Mapped[RecordStatus] = mapped_column(String(20))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    name: Mapped[str] = mapped_column(String(500))
    normalized_name: Mapped[str] = mapped_column(String(500))
    brand: Mapped[str | None] = mapped_column(String(200))
    normalized_brand: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(300))
    normalized_category: Mapped[str | None] = mapped_column(String(300))
    gtin: Mapped[str | None] = mapped_column(String(40))
    normalized_gtin: Mapped[str | None] = mapped_column(String(14), index=True)
    sku: Mapped[str | None] = mapped_column(String(160))
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(120))
    normalized_mpn: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    normalized_description: Mapped[str | None] = mapped_column(Text)
    pack_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit_code: Mapped[str | None] = mapped_column(String(20))
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportIssue(Base):
    __tablename__ = "import_issues"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(String(80))
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(
            IssueSeverity,
            values_callable=enum_values,
            name="issue_severity",
            native_enum=False,
        )
    )
    message: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchProposal(Base):
    __tablename__ = "match_proposals"
    __table_args__ = (
        CheckConstraint("rank > 0", name="positive_rank"),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        CheckConstraint(
            "runner_up_margin IS NULL OR (runner_up_margin >= 0 AND runner_up_margin <= 1)",
            name="margin_range",
        ),
        UniqueConstraint(
            "supplier_product_id",
            "canonical_product_id",
            "policy_version",
            name="product_target_policy",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    supplier_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplier_products.id", ondelete="CASCADE"), index=True
    )
    canonical_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    runner_up_margin: Mapped[Decimal | None] = mapped_column(Numeric(7, 6))
    decision: Mapped[MatchDecision] = mapped_column(
        Enum(
            MatchDecision,
            values_callable=enum_values,
            name="match_decision",
            native_enum=False,
        )
    )
    policy_version: Mapped[str] = mapped_column(String(40))
    semantic_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoreFactor(Base):
    __tablename__ = "score_factors"
    __table_args__ = (
        CheckConstraint("raw_score >= 0 AND raw_score <= 1", name="raw_score_range"),
        CheckConstraint("weight >= 0 AND weight <= 1", name="weight_range"),
        UniqueConstraint("match_proposal_id", "name", name="proposal_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    match_proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_proposals.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(60))
    raw_score: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    weight: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    contribution: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON)


class CatalogLink(Base):
    __tablename__ = "catalog_links"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    supplier_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("supplier_products.id", ondelete="CASCADE"), unique=True
    )
    canonical_product_id: Mapped[UUID] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="RESTRICT"), index=True
    )
    match_proposal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("match_proposals.id", ondelete="SET NULL")
    )
    method: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[Decimal] = mapped_column(Numeric(7, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    match_proposal_id: Mapped[UUID] = mapped_column(
        ForeignKey("match_proposals.id", ondelete="RESTRICT"), index=True
    )
    canonical_product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("canonical_products.id", ondelete="RESTRICT")
    )
    action: Mapped[ReviewAction] = mapped_column(
        Enum(
            ReviewAction,
            values_callable=enum_values,
            name="review_action",
            native_enum=False,
        )
    )
    reviewer: Mapped[str] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
