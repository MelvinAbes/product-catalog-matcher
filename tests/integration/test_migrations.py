import pytest
from sqlalchemy import Engine, inspect, text

pytestmark = pytest.mark.integration


def test_migration_creates_domain_tables_and_trigram_index(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)

    assert {
        "alembic_version",
        "canonical_products",
        "catalog_links",
        "import_batches",
        "import_issues",
        "match_proposals",
        "review_events",
        "score_factors",
        "supplier_products",
        "suppliers",
    } <= set(inspector.get_table_names())

    with migrated_engine.connect() as connection:
        extension = connection.scalar(
            text("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'")
        )
        index = connection.scalar(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE indexname = 'ix_canonical_products_name_trgm'"
            )
        )

    assert extension == "pg_trgm"
    assert index == "ix_canonical_products_name_trgm"
