"""Create catalog matching schema.

Revision ID: 20260731_01
Revises:
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

uuid_type = sa.Uuid()
timestamp = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "suppliers",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
        sa.UniqueConstraint("code", name=op.f("uq_suppliers_code")),
    )
    op.create_table(
        "import_batches",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("supplier_id", uuid_type, nullable=False),
        sa.Column(
            "role",
            sa.Enum("reference", "candidate", name="import_role", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "completed",
                "completed_with_errors",
                "failed",
                name="import_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("accepted_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("issue_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", timestamp, nullable=True),
        sa.Column("completed_at", timestamp, nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "total_rows >= 0 AND accepted_rows >= 0 AND rejected_rows >= 0 "
            "AND duplicate_rows >= 0 AND issue_count >= 0",
            name=op.f("ck_import_batches_non_negative_counts"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_import_batches_supplier_id_suppliers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
        sa.UniqueConstraint(
            "supplier_id",
            "content_sha256",
            name=op.f("uq_import_batches_supplier_content"),
        ),
    )
    op.create_index(
        op.f("ix_import_batches_supplier_id"),
        "import_batches",
        ["supplier_id"],
        unique=False,
    )
    op.create_table(
        "canonical_products",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("brand", sa.String(length=200), nullable=True),
        sa.Column("normalized_brand", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=300), nullable=True),
        sa.Column("normalized_category", sa.String(length=300), nullable=True),
        sa.Column("gtin", sa.String(length=14), nullable=True),
        sa.Column("manufacturer_part_number", sa.String(length=120), nullable=True),
        sa.Column("normalized_mpn", sa.String(length=120), nullable=True),
        sa.Column("pack_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit_value", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit_code", sa.String(length=20), nullable=True),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canonical_products")),
    )
    op.create_index(
        op.f("ix_canonical_products_gtin"),
        "canonical_products",
        ["gtin"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canonical_products_normalized_brand"),
        "canonical_products",
        ["normalized_brand"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canonical_products_normalized_category"),
        "canonical_products",
        ["normalized_category"],
        unique=False,
    )
    op.execute(
        "CREATE INDEX ix_canonical_products_name_trgm "
        "ON canonical_products USING gin (normalized_name gin_trgm_ops)"
    )
    op.create_table(
        "supplier_products",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("supplier_id", uuid_type, nullable=False),
        sa.Column("import_batch_id", uuid_type, nullable=False),
        sa.Column("source_record_id", sa.String(length=160), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column(
            "record_status",
            sa.Enum("valid", "duplicate", name="record_status", native_enum=False),
            nullable=False,
        ),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=500), nullable=False),
        sa.Column("brand", sa.String(length=200), nullable=True),
        sa.Column("normalized_brand", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=300), nullable=True),
        sa.Column("normalized_category", sa.String(length=300), nullable=True),
        sa.Column("gtin", sa.String(length=40), nullable=True),
        sa.Column("normalized_gtin", sa.String(length=14), nullable=True),
        sa.Column("sku", sa.String(length=160), nullable=True),
        sa.Column("manufacturer_part_number", sa.String(length=120), nullable=True),
        sa.Column("normalized_mpn", sa.String(length=120), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("normalized_description", sa.Text(), nullable=True),
        sa.Column("pack_quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit_value", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit_code", sa.String(length=20), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source_row_number > 0", name=op.f("ck_supplier_products_source_row")),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_supplier_products_import_batch_id_import_batches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_supplier_products_supplier_id_suppliers"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_supplier_products")),
        sa.UniqueConstraint(
            "import_batch_id",
            "source_record_id",
            name=op.f("uq_supplier_products_batch_source_record"),
        ),
    )
    op.create_index(
        op.f("ix_supplier_products_import_batch_id"),
        "supplier_products",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_products_normalized_gtin"),
        "supplier_products",
        ["normalized_gtin"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_products_supplier_id"),
        "supplier_products",
        ["supplier_id"],
        unique=False,
    )
    op.create_table(
        "import_issues",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("import_batch_id", uuid_type, nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("warning", "error", name="issue_severity", native_enum=False),
            nullable=False,
        ),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_import_issues_import_batch_id_import_batches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_issues")),
    )
    op.create_index(
        op.f("ix_import_issues_import_batch_id"),
        "import_issues",
        ["import_batch_id"],
        unique=False,
    )
    op.create_table(
        "match_proposals",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("supplier_product_id", uuid_type, nullable=False),
        sa.Column("canonical_product_id", uuid_type, nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("runner_up_margin", sa.Numeric(precision=7, scale=6), nullable=True),
        sa.Column(
            "decision",
            sa.Enum(
                "auto_match",
                "review",
                "no_match",
                name="match_decision",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("policy_version", sa.String(length=40), nullable=False),
        sa.Column("semantic_used", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rank > 0", name=op.f("ck_match_proposals_positive_rank")),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1",
            name=op.f("ck_match_proposals_score_range"),
        ),
        sa.CheckConstraint(
            "runner_up_margin IS NULL OR (runner_up_margin >= 0 AND runner_up_margin <= 1)",
            name=op.f("ck_match_proposals_margin_range"),
        ),
        sa.ForeignKeyConstraint(
            ["canonical_product_id"],
            ["canonical_products.id"],
            name=op.f("fk_match_proposals_canonical_product_id_canonical_products"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_product_id"],
            ["supplier_products.id"],
            name=op.f("fk_match_proposals_supplier_product_id_supplier_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_proposals")),
        sa.UniqueConstraint(
            "supplier_product_id",
            "canonical_product_id",
            "policy_version",
            name=op.f("uq_match_proposals_product_target_policy"),
        ),
    )
    op.create_index(
        op.f("ix_match_proposals_canonical_product_id"),
        "match_proposals",
        ["canonical_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_proposals_supplier_product_id"),
        "match_proposals",
        ["supplier_product_id"],
        unique=False,
    )
    op.create_table(
        "score_factors",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_proposal_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("raw_score", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("weight", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("contribution", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "raw_score >= 0 AND raw_score <= 1",
            name=op.f("ck_score_factors_raw_score_range"),
        ),
        sa.CheckConstraint(
            "weight >= 0 AND weight <= 1",
            name=op.f("ck_score_factors_weight_range"),
        ),
        sa.ForeignKeyConstraint(
            ["match_proposal_id"],
            ["match_proposals.id"],
            name=op.f("fk_score_factors_match_proposal_id_match_proposals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_score_factors")),
        sa.UniqueConstraint(
            "match_proposal_id",
            "name",
            name=op.f("uq_score_factors_proposal_name"),
        ),
    )
    op.create_index(
        op.f("ix_score_factors_match_proposal_id"),
        "score_factors",
        ["match_proposal_id"],
        unique=False,
    )
    op.create_table(
        "catalog_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("supplier_product_id", uuid_type, nullable=False),
        sa.Column("canonical_product_id", uuid_type, nullable=False),
        sa.Column("match_proposal_id", uuid_type, nullable=True),
        sa.Column("method", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=7, scale=6), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_catalog_links_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["canonical_product_id"],
            ["canonical_products.id"],
            name=op.f("fk_catalog_links_canonical_product_id_canonical_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["match_proposal_id"],
            ["match_proposals.id"],
            name=op.f("fk_catalog_links_match_proposal_id_match_proposals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_product_id"],
            ["supplier_products.id"],
            name=op.f("fk_catalog_links_supplier_product_id_supplier_products"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_links")),
        sa.UniqueConstraint(
            "supplier_product_id",
            name=op.f("uq_catalog_links_supplier_product_id"),
        ),
    )
    op.create_index(
        op.f("ix_catalog_links_canonical_product_id"),
        "catalog_links",
        ["canonical_product_id"],
        unique=False,
    )
    op.create_table(
        "review_events",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("match_proposal_id", uuid_type, nullable=False),
        sa.Column("canonical_product_id", uuid_type, nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "accepted",
                "rejected",
                "reassigned",
                name="review_action",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("reviewer", sa.String(length=120), nullable=False),
        sa.Column("rationale", sa.String(length=500), nullable=False),
        sa.Column("created_at", timestamp, server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["canonical_product_id"],
            ["canonical_products.id"],
            name=op.f("fk_review_events_canonical_product_id_canonical_products"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["match_proposal_id"],
            ["match_proposals.id"],
            name=op.f("fk_review_events_match_proposal_id_match_proposals"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_events")),
    )
    op.create_index(
        op.f("ix_review_events_match_proposal_id"),
        "review_events",
        ["match_proposal_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_review_events_match_proposal_id"), table_name="review_events")
    op.drop_table("review_events")
    op.drop_index(op.f("ix_catalog_links_canonical_product_id"), table_name="catalog_links")
    op.drop_table("catalog_links")
    op.drop_index(op.f("ix_score_factors_match_proposal_id"), table_name="score_factors")
    op.drop_table("score_factors")
    op.drop_index(
        op.f("ix_match_proposals_supplier_product_id"),
        table_name="match_proposals",
    )
    op.drop_index(
        op.f("ix_match_proposals_canonical_product_id"),
        table_name="match_proposals",
    )
    op.drop_table("match_proposals")
    op.drop_index(op.f("ix_import_issues_import_batch_id"), table_name="import_issues")
    op.drop_table("import_issues")
    op.drop_index(op.f("ix_supplier_products_supplier_id"), table_name="supplier_products")
    op.drop_index(
        op.f("ix_supplier_products_normalized_gtin"),
        table_name="supplier_products",
    )
    op.drop_index(
        op.f("ix_supplier_products_import_batch_id"),
        table_name="supplier_products",
    )
    op.drop_table("supplier_products")
    op.execute("DROP INDEX IF EXISTS ix_canonical_products_name_trgm")
    op.drop_index(
        op.f("ix_canonical_products_normalized_category"),
        table_name="canonical_products",
    )
    op.drop_index(
        op.f("ix_canonical_products_normalized_brand"),
        table_name="canonical_products",
    )
    op.drop_index(op.f("ix_canonical_products_gtin"), table_name="canonical_products")
    op.drop_table("canonical_products")
    op.drop_index(op.f("ix_import_batches_supplier_id"), table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_table("suppliers")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
